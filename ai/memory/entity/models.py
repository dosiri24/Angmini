"""Data models for the Entity Memory system.

Entities represent discrete objects mentioned across conversation history:
- PERSON: Users, collaborators, team members
- PROJECT: Code projects, initiatives, repositories
- TOOL: Software tools, libraries, frameworks
- CONCEPT: Abstract ideas, algorithms, patterns
- FILE: Specific files, modules, components
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EntityType(str, Enum):
    """Categories of trackable entities."""

    PERSON = "person"
    PROJECT = "project"
    TOOL = "tool"
    CONCEPT = "concept"
    FILE = "file"


class RelationType(str, Enum):
    """Types of relationships between entities."""

    # Collaboration relationships
    COLLABORATES_WITH = "collaborates_with"  # person <-> person
    WORKS_ON = "works_on"  # person -> project
    MAINTAINS = "maintains"  # person -> tool/project

    # Dependency relationships
    DEPENDS_ON = "depends_on"  # project -> tool, file -> file
    USES = "uses"  # project -> tool, file -> tool
    IMPORTS = "imports"  # file -> file

    # Hierarchical relationships
    BELONGS_TO = "belongs_to"  # file -> project, concept -> project
    CONTAINS = "contains"  # project -> file
    PART_OF = "part_of"  # concept -> concept

    # Semantic relationships
    RELATED_TO = "related_to"  # concept <-> concept
    IMPLEMENTS = "implements"  # file -> concept
    DISCUSSES = "discusses"  # any -> concept


@dataclass(slots=True)
class Entity:
    """A discrete entity extracted from conversation/execution context.

    Attributes:
        id: Unique identifier (format: {type}_{normalized_name}_{hash})
        type: Entity category (person, project, tool, concept, file)
        name: Display name of the entity
        attributes: Type-specific metadata (e.g., file_path for FILE, url for PROJECT)
        first_seen: When entity was first mentioned
        last_seen: Most recent mention timestamp
        mention_count: Number of times entity appeared across memories
        relations: List of (relation_type, target_entity_id, context) tuples
        embedding: Optional vector embedding for semantic similarity
    """

    id: str
    type: EntityType
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    mention_count: int = 1
    relations: List[Tuple[str, str, str]] = field(default_factory=list)
    embedding: Optional[List[float]] = None

    def to_document(self) -> Dict[str, Any]:
        """Convert entity to dictionary for storage."""
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "attributes": dict(self.attributes),
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "mention_count": self.mention_count,
            "embedding": list(self.embedding) if self.embedding else None,
        }

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> Entity:
        """Reconstruct entity from stored document."""
        return cls(
            id=doc["id"],
            type=EntityType(doc["type"]),
            name=doc["name"],
            attributes=doc.get("attributes", {}),
            first_seen=datetime.fromisoformat(doc["first_seen"]),
            last_seen=datetime.fromisoformat(doc["last_seen"]),
            mention_count=doc.get("mention_count", 1),
            relations=[],  # Relations loaded separately
            embedding=doc.get("embedding"),
        )

    def update_mention(self, timestamp: Optional[datetime] = None) -> None:
        """Update entity statistics when it's mentioned again."""
        self.last_seen = timestamp or datetime.utcnow()
        self.mention_count += 1

    def add_relation(
        self,
        relation_type: RelationType,
        target_entity_id: str,
        context: str = "",
    ) -> None:
        """Add a relationship to another entity."""
        relation_tuple = (relation_type.value, target_entity_id, context)
        if relation_tuple not in self.relations:
            self.relations.append(relation_tuple)

    def merge_attributes(self, new_attributes: Dict[str, Any]) -> None:
        """Merge new attributes into existing ones."""
        for key, value in new_attributes.items():
            if key not in self.attributes or self.attributes[key] != value:
                self.attributes[key] = value


@dataclass(slots=True)
class EntityRelation:
    """A directed relationship between two entities.

    Attributes:
        id: Auto-incremented database ID
        source_entity_id: ID of the source entity
        target_entity_id: ID of the target entity
        relation_type: Type of relationship (from RelationType enum)
        context: Optional contextual information about this relationship
        created_at: When this relationship was first observed
    """

    source_entity_id: str
    target_entity_id: str
    relation_type: RelationType
    context: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[int] = None  # Database-assigned

    def to_document(self) -> Dict[str, Any]:
        """Convert relation to dictionary for storage."""
        return {
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relation_type": self.relation_type.value,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> EntityRelation:
        """Reconstruct relation from stored document."""
        return cls(
            id=doc.get("id"),
            source_entity_id=doc["source_entity_id"],
            target_entity_id=doc["target_entity_id"],
            relation_type=RelationType(doc["relation_type"]),
            context=doc.get("context", ""),
            created_at=datetime.fromisoformat(doc["created_at"]),
        )


@dataclass(slots=True)
class MemoryEntityLink:
    """Links a memory record to an entity with relevance score.

    Attributes:
        memory_id: ID of the memory record
        entity_id: ID of the linked entity
        relevance_score: How central this entity is to the memory (0.0-1.0)
        created_at: When this link was established
    """

    memory_id: str
    entity_id: str
    relevance_score: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_document(self) -> Dict[str, Any]:
        """Convert link to dictionary for storage."""
        return {
            "memory_id": self.memory_id,
            "entity_id": self.entity_id,
            "relevance_score": self.relevance_score,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> MemoryEntityLink:
        """Reconstruct link from stored document."""
        return cls(
            memory_id=doc["memory_id"],
            entity_id=doc["entity_id"],
            relevance_score=doc.get("relevance_score", 1.0),
            created_at=datetime.fromisoformat(doc["created_at"]),
        )


@dataclass(slots=True)
class ExtractedEntityInfo:
    """Result of entity extraction from text.

    Used as intermediate representation before creating Entity objects.

    Attributes:
        type: Entity category
        name: Display name
        attributes: Extracted metadata
        confidence: Extraction confidence (0.0-1.0)
        text_span: Optional original text span that mentioned this entity
    """

    type: EntityType
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    text_span: Optional[str] = None

    def to_entity_id(self) -> str:
        """Generate a stable ID for this entity."""
        import hashlib

        # Normalize name for ID generation
        normalized = self.name.lower().strip().replace(" ", "_")

        # Include type-specific attributes in hash for disambiguation
        hash_input = f"{self.type.value}:{normalized}"

        # Add key attributes to hash
        if self.type == EntityType.FILE and "file_path" in self.attributes:
            hash_input += f":{self.attributes['file_path']}"
        elif self.type == EntityType.PROJECT and "repository" in self.attributes:
            hash_input += f":{self.attributes['repository']}"

        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"{self.type.value}_{normalized}_{hash_suffix}"
