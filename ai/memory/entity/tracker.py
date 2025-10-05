"""High-level entity tracking coordinator.

Coordinates entity extraction, deduplication, storage, and memory linking.
Provides a unified interface for the entity memory subsystem.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from ai.core.logger import get_logger
from .extractor import EntityExtractor, RuleBasedEntityExtractor
from .models import Entity, EntityRelation, EntityType, ExtractedEntityInfo, MemoryEntityLink, RelationType
from .storage import EntityRepository


class EntityTracker:
    """Coordinates entity extraction, storage, and retrieval.

    Provides high-level API for:
    - Extracting entities from memory records
    - Deduplicating and merging entities
    - Tracking entity relationships
    - Linking entities to memories
    """

    def __init__(
        self,
        repository: EntityRepository,
        extractor: EntityExtractor,
        fallback_extractor: Optional[RuleBasedEntityExtractor] = None,
    ) -> None:
        """Initialize entity tracker.

        Args:
            repository: EntityRepository for storage
            extractor: Primary LLM-based entity extractor
            fallback_extractor: Optional rule-based fallback extractor
        """
        self._repository = repository
        self._extractor = extractor
        self._fallback_extractor = fallback_extractor or RuleBasedEntityExtractor()
        self._logger = get_logger(self.__class__.__name__)

    def track_memory(
        self,
        memory_id: str,
        memory_dict: Dict[str, Any],
    ) -> Tuple[List[Entity], List[EntityRelation]]:
        """Extract and track entities from a memory record.

        Args:
            memory_id: Unique memory record identifier
            memory_dict: Memory record data (summary, goal, outcome, etc.)

        Returns:
            Tuple of (tracked entities, tracked relations)
        """
        # Extract entities using LLM
        extracted_entities, extracted_relations = self._extractor.extract_from_memory_context(
            memory_dict
        )

        # Supplement with rule-based extraction
        text = self._build_text_from_memory(memory_dict)
        fallback_files = self._fallback_extractor.extract_files(text)
        fallback_tools = self._fallback_extractor.extract_tools(text)

        # Merge extracted entities
        all_extracted = extracted_entities + fallback_files + fallback_tools

        if not all_extracted:
            self._logger.debug(f"No entities extracted for memory {memory_id}")
            return [], []

        # Deduplicate and create/update entities
        entities = self._process_extracted_entities(all_extracted)

        # Create entity relations
        relations = self._process_extracted_relations(
            extracted_relations,
            entities,
        )

        # Link entities to memory
        self._link_entities_to_memory(memory_id, entities)

        self._logger.info(
            f"Tracked {len(entities)} entities and {len(relations)} relations for memory {memory_id}"
        )

        return entities, relations

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity if found, None otherwise
        """
        return self._repository.get_entity(entity_id)

    def search_entities(
        self,
        name: str,
        entity_type: Optional[EntityType] = None,
        fuzzy: bool = True,
    ) -> List[Entity]:
        """Search for entities by name.

        Args:
            name: Entity name to search for
            entity_type: Optional type filter
            fuzzy: Use fuzzy matching

        Returns:
            List of matching entities
        """
        entities = self._repository.get_entities_by_name(name, fuzzy=fuzzy)

        if entity_type:
            entities = [e for e in entities if e.type == entity_type]

        return entities

    def get_entity_context(self, entity_id: str, depth: int = 1) -> Dict[str, Any]:
        """Get full context for an entity (relations, mentions, etc.).

        Args:
            entity_id: Entity to get context for
            depth: Relationship traversal depth

        Returns:
            Dictionary with entity details, relations, and memory links
        """
        entity = self._repository.get_entity(entity_id)
        if not entity:
            return {}

        # Get related entities
        related_ids = self._repository.get_related_entities(entity_id, depth=depth)
        related_entities = [
            self._repository.get_entity(rid)
            for rid in related_ids
            if rid != entity_id
        ]

        # Get memory mentions
        memory_links = self._repository.get_memories_for_entity(entity_id)

        return {
            "entity": entity,
            "related_entities": [e for e in related_entities if e],
            "memory_count": len(memory_links),
            "recent_memories": memory_links[:10],  # Top 10 most relevant
            "mention_count": entity.mention_count,
            "last_seen": entity.last_seen,
        }

    def get_entities_by_type(
        self,
        entity_type: EntityType,
        limit: int = 100,
    ) -> List[Entity]:
        """Get entities of a specific type.

        Args:
            entity_type: Type to filter by
            limit: Maximum number to return

        Returns:
            List of entities
        """
        return self._repository.get_entities_by_type(entity_type, limit=limit)

    def get_statistics(self) -> Dict[str, Any]:
        """Get entity tracking statistics.

        Returns:
            Dictionary with counts and metrics
        """
        stats = self._repository.get_entity_statistics()
        return {
            "total_entities": stats.get("total", 0),
            "by_type": {
                k: v for k, v in stats.items() if k != "total"
            },
        }

    def _process_extracted_entities(
        self,
        extracted: List[ExtractedEntityInfo],
    ) -> List[Entity]:
        """Process extracted entities: deduplicate, merge, store.

        Args:
            extracted: List of extracted entity info

        Returns:
            List of processed Entity objects
        """
        processed = []

        for info in extracted:
            # Generate stable ID
            entity_id = info.to_entity_id()

            # Check if entity already exists
            existing = self._repository.get_entity(entity_id)

            if existing:
                # Update existing entity
                existing.update_mention()
                existing.merge_attributes(info.attributes)
                self._repository.save_entity(existing)
                processed.append(existing)
            else:
                # Create new entity
                entity = Entity(
                    id=entity_id,
                    type=info.type,
                    name=info.name,
                    attributes=info.attributes,
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    mention_count=1,
                    relations=[],
                    embedding=None,  # Embedding added separately
                )
                self._repository.save_entity(entity)
                processed.append(entity)

        return processed

    def _process_extracted_relations(
        self,
        extracted_relations: List[Tuple[str, str, RelationType, str]],
        entities: List[Entity],
    ) -> List[EntityRelation]:
        """Process extracted relations: resolve entities, store.

        Args:
            extracted_relations: List of (source_name, target_name, relation_type, context)
            entities: List of entities in current context

        Returns:
            List of processed EntityRelation objects
        """
        # Build name -> entity_id mapping
        name_to_id = {e.name.lower(): e.id for e in entities}

        processed = []

        for source_name, target_name, relation_type, context in extracted_relations:
            source_id = name_to_id.get(source_name.lower())
            target_id = name_to_id.get(target_name.lower())

            if not source_id or not target_id:
                self._logger.debug(
                    f"Skipping relation {source_name} -> {target_name}: entities not found"
                )
                continue

            # Create and save relation
            relation = EntityRelation(
                source_entity_id=source_id,
                target_entity_id=target_id,
                relation_type=relation_type,
                context=context,
                created_at=datetime.utcnow(),
            )
            self._repository.save_relation(relation)
            processed.append(relation)

        return processed

    def _link_entities_to_memory(
        self,
        memory_id: str,
        entities: List[Entity],
    ) -> None:
        """Create memory-entity links.

        Args:
            memory_id: Memory record ID
            entities: Entities to link
        """
        for entity in entities:
            # Simple relevance scoring based on mention count
            # More sophisticated scoring could be added later
            relevance_score = min(1.0, 0.5 + (entity.mention_count * 0.05))

            link = MemoryEntityLink(
                memory_id=memory_id,
                entity_id=entity.id,
                relevance_score=relevance_score,
                created_at=datetime.utcnow(),
            )
            self._repository.save_memory_entity_link(link)

    def _build_text_from_memory(self, memory_dict: Dict[str, Any]) -> str:
        """Build concatenated text from memory fields."""
        parts = []
        for key in ["summary", "goal", "user_intent", "outcome"]:
            if key in memory_dict and memory_dict[key]:
                parts.append(str(memory_dict[key]))

        return " ".join(parts)
