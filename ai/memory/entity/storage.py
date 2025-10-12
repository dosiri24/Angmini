"""Entity storage and retrieval using SQLite with graph relationship tracking.

Manages entities, relationships, and memory-entity links with efficient querying
and update capabilities.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from ai.core.logger import get_logger
from .models import Entity, EntityRelation, EntityType, MemoryEntityLink, RelationType


class EntityRepository:
    """Repository for entity CRUD operations and relationship management.

    Handles:
    - Entity storage and retrieval
    - Relationship tracking (graph structure)
    - Memory-entity linking
    - Entity merging and deduplication
    """

    def __init__(self, database_path: str | Path) -> None:
        """Initialize repository with database path.

        Args:
            database_path: Path to SQLite database file
        """
        self._path = Path(database_path)
        self._logger = get_logger(self.__class__.__name__)

    def save_entity(self, entity: Entity) -> None:
        """Save or update an entity.

        Args:
            entity: Entity to save
        """
        doc = entity.to_document()
        embedding_json = json.dumps(doc.pop("embedding", None))
        attributes_json = json.dumps(doc["attributes"], ensure_ascii=False)

        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """
                INSERT INTO entities
                (id, type, name, attributes, first_seen, last_seen, mention_count, embedding, created_at, updated_at)
                VALUES (:id, :type, :name, :attributes, :first_seen, :last_seen, :mention_count, :embedding, :created_at, :updated_at)
                ON CONFLICT(id) DO UPDATE SET
                    type=excluded.type,
                    name=excluded.name,
                    attributes=excluded.attributes,
                    last_seen=excluded.last_seen,
                    mention_count=excluded.mention_count,
                    embedding=excluded.embedding,
                    updated_at=excluded.updated_at
                """,
                {
                    "id": entity.id,
                    "type": entity.type.value,
                    "name": entity.name,
                    "attributes": attributes_json,
                    "first_seen": doc["first_seen"],
                    "last_seen": doc["last_seen"],
                    "mention_count": entity.mention_count,
                    "embedding": embedding_json,
                    "created_at": doc.get("created_at", now),
                    "updated_at": now,
                },
            )
            conn.commit()

    def save_relation(self, relation: EntityRelation) -> None:
        """Save or update a relationship between entities.

        Args:
            relation: EntityRelation to save
        """
        doc = relation.to_document()

        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """
                INSERT INTO entity_relations
                (source_entity_id, target_entity_id, relation_type, context, created_at)
                VALUES (:source, :target, :relation_type, :context, :created_at)
                ON CONFLICT(source_entity_id, target_entity_id, relation_type) DO UPDATE SET
                    context=excluded.context
                """,
                {
                    "source": doc["source_entity_id"],
                    "target": doc["target_entity_id"],
                    "relation_type": doc["relation_type"],
                    "context": doc["context"],
                    "created_at": doc["created_at"],
                },
            )
            conn.commit()

    def save_memory_entity_link(self, link: MemoryEntityLink) -> None:
        """Link a memory record to an entity.

        Args:
            link: MemoryEntityLink to save
        """
        doc = link.to_document()

        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """
                INSERT INTO memory_entities
                (memory_id, entity_id, relevance_score, created_at)
                VALUES (:memory_id, :entity_id, :relevance_score, :created_at)
                ON CONFLICT(memory_id, entity_id) DO UPDATE SET
                    relevance_score=excluded.relevance_score
                """,
                {
                    "memory_id": doc["memory_id"],
                    "entity_id": doc["entity_id"],
                    "relevance_score": doc["relevance_score"],
                    "created_at": doc["created_at"],
                },
            )
            conn.commit()

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity by ID.

        Args:
            entity_id: Unique entity identifier

        Returns:
            Entity if found, None otherwise
        """
        with sqlite3.connect(self._path) as conn:
            cursor = conn.execute(
                """
                SELECT id, type, name, attributes, first_seen, last_seen, mention_count, embedding
                FROM entities
                WHERE id = ?
                """,
                (entity_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            entity = self._row_to_entity(row)

            # Load relations
            entity.relations = self.get_entity_relations(entity_id)

            return entity

    def get_entities_by_type(self, entity_type: EntityType, limit: int = 100) -> List[Entity]:
        """Retrieve entities by type.

        Args:
            entity_type: Type of entities to retrieve
            limit: Maximum number of entities to return

        Returns:
            List of entities matching the type
        """
        with sqlite3.connect(self._path) as conn:
            cursor = conn.execute(
                """
                SELECT id, type, name, attributes, first_seen, last_seen, mention_count, embedding
                FROM entities
                WHERE type = ?
                ORDER BY mention_count DESC, last_seen DESC
                LIMIT ?
                """,
                (entity_type.value, limit),
            )

            entities = [self._row_to_entity(row) for row in cursor]
            return entities

    def get_entities_by_name(self, name: str, fuzzy: bool = False) -> List[Entity]:
        """Find entities by name.

        Args:
            name: Entity name to search for
            fuzzy: If True, use LIKE matching

        Returns:
            List of matching entities
        """
        with sqlite3.connect(self._path) as conn:
            if fuzzy:
                cursor = conn.execute(
                    """
                    SELECT id, type, name, attributes, first_seen, last_seen, mention_count, embedding
                    FROM entities
                    WHERE name LIKE ?
                    ORDER BY mention_count DESC
                    """,
                    (f"%{name}%",),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT id, type, name, attributes, first_seen, last_seen, mention_count, embedding
                    FROM entities
                    WHERE name = ?
                    ORDER BY mention_count DESC
                    """,
                    (name,),
                )

            entities = [self._row_to_entity(row) for row in cursor]
            return entities

    def get_entity_relations(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None,
    ) -> List[Tuple[str, str, str]]:
        """Get all relations for an entity.

        Args:
            entity_id: Entity to get relations for
            relation_type: Optional filter for specific relation type

        Returns:
            List of (relation_type, target_entity_id, context) tuples
        """
        with sqlite3.connect(self._path) as conn:
            if relation_type:
                cursor = conn.execute(
                    """
                    SELECT relation_type, target_entity_id, context
                    FROM entity_relations
                    WHERE source_entity_id = ? AND relation_type = ?
                    """,
                    (entity_id, relation_type.value),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT relation_type, target_entity_id, context
                    FROM entity_relations
                    WHERE source_entity_id = ?
                    """,
                    (entity_id,),
                )

            return [(row[0], row[1], row[2]) for row in cursor]

    def get_related_entities(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None,
        depth: int = 1,
    ) -> Set[str]:
        """Get entities related to the given entity (graph traversal).

        Args:
            entity_id: Starting entity
            relation_type: Optional filter for specific relation type
            depth: How many hops to traverse (1 = direct relations)

        Returns:
            Set of related entity IDs
        """
        related = set()
        to_visit = {entity_id}
        visited = set()

        for _ in range(depth):
            current_level = to_visit - visited
            if not current_level:
                break

            for ent_id in current_level:
                visited.add(ent_id)
                relations = self.get_entity_relations(ent_id, relation_type)
                related.update(target for _, target, _ in relations)

            to_visit = related - visited

        return related

    def get_entities_for_memory(self, memory_id: str) -> List[Tuple[Entity, float]]:
        """Get all entities linked to a memory record.

        Args:
            memory_id: Memory record ID

        Returns:
            List of (Entity, relevance_score) tuples
        """
        with sqlite3.connect(self._path) as conn:
            cursor = conn.execute(
                """
                SELECT e.id, e.type, e.name, e.attributes, e.first_seen, e.last_seen, e.mention_count, e.embedding,
                       me.relevance_score
                FROM entities e
                JOIN memory_entities me ON e.id = me.entity_id
                WHERE me.memory_id = ?
                ORDER BY me.relevance_score DESC
                """,
                (memory_id,),
            )

            results = []
            for row in cursor:
                entity = self._row_to_entity(row[:8])
                relevance_score = row[8]
                results.append((entity, relevance_score))

            return results

    def get_memories_for_entity(self, entity_id: str) -> List[Tuple[str, float]]:
        """Get all memory records that mention this entity.

        Args:
            entity_id: Entity to search for

        Returns:
            List of (memory_id, relevance_score) tuples
        """
        with sqlite3.connect(self._path) as conn:
            cursor = conn.execute(
                """
                SELECT memory_id, relevance_score
                FROM memory_entities
                WHERE entity_id = ?
                ORDER BY relevance_score DESC
                """,
                (entity_id,),
            )

            return [(row[0], row[1]) for row in cursor]

    def update_entity_mention(
        self,
        entity_id: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Increment mention count and update last_seen timestamp.

        Args:
            entity_id: Entity to update
            timestamp: Optional custom timestamp (defaults to now)
        """
        last_seen = (timestamp or datetime.utcnow()).isoformat()
        updated_at = datetime.utcnow().isoformat()

        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """
                UPDATE entities
                SET mention_count = mention_count + 1,
                    last_seen = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (last_seen, updated_at, entity_id),
            )
            conn.commit()

    def merge_entities(self, source_id: str, target_id: str) -> None:
        """Merge two entities (e.g., duplicates detected).

        All relations and memory links from source are transferred to target,
        then source is deleted.

        Args:
            source_id: Entity to merge from (will be deleted)
            target_id: Entity to merge into (will be kept)
        """
        with sqlite3.connect(self._path) as conn:
            # Transfer relations
            conn.execute(
                """
                UPDATE entity_relations
                SET source_entity_id = ?
                WHERE source_entity_id = ?
                """,
                (target_id, source_id),
            )
            conn.execute(
                """
                UPDATE entity_relations
                SET target_entity_id = ?
                WHERE target_entity_id = ?
                """,
                (target_id, source_id),
            )

            # Transfer memory links
            conn.execute(
                """
                UPDATE OR REPLACE memory_entities
                SET entity_id = ?
                WHERE entity_id = ?
                """,
                (target_id, source_id),
            )

            # Delete source entity
            conn.execute("DELETE FROM entities WHERE id = ?", (source_id,))

            conn.commit()

        self._logger.info(f"Merged entity {source_id} into {target_id}")

    def list_all_entities(self, limit: Optional[int] = None) -> Iterable[Entity]:
        """List all entities in the database.

        Args:
            limit: Optional limit on number of entities

        Yields:
            Entity objects
        """
        with sqlite3.connect(self._path) as conn:
            query = """
                SELECT id, type, name, attributes, first_seen, last_seen, mention_count, embedding
                FROM entities
                ORDER BY mention_count DESC, last_seen DESC
            """
            if limit:
                query += f" LIMIT {limit}"

            cursor = conn.execute(query)

            for row in cursor:
                yield self._row_to_entity(row)

    def get_entity_statistics(self) -> Dict[str, int]:
        """Get statistics about stored entities.

        Returns:
            Dictionary with counts per entity type
        """
        with sqlite3.connect(self._path) as conn:
            cursor = conn.execute(
                """
                SELECT type, COUNT(*) as count
                FROM entities
                GROUP BY type
                """
            )

            stats = {row[0]: row[1] for row in cursor}
            stats["total"] = sum(stats.values())

            return stats

    def _row_to_entity(self, row: tuple) -> Entity:
        """Convert database row to Entity object."""
        attributes = json.loads(row[3]) if row[3] else {}
        embedding_raw = row[7] if len(row) > 7 else None
        embedding = json.loads(embedding_raw) if embedding_raw else None

        return Entity(
            id=row[0],
            type=EntityType(row[1]),
            name=row[2],
            attributes=attributes,
            first_seen=datetime.fromisoformat(row[4]),
            last_seen=datetime.fromisoformat(row[5]),
            mention_count=row[6],
            relations=[],  # Load separately if needed
            embedding=embedding,
        )
