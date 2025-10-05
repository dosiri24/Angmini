"""Entity Memory subsystem for tracking objects across conversations.

This module provides:
- Entity extraction from natural language (LLM-based NER)
- Entity storage and retrieval with SQLite
- Relationship graph tracking
- Memory-entity linking for context-aware retrieval
"""

from .extractor import EntityExtractor, RuleBasedEntityExtractor
from .models import (
    Entity,
    EntityRelation,
    EntityType,
    ExtractedEntityInfo,
    MemoryEntityLink,
    RelationType,
)
from .storage import EntityRepository
from .tracker import EntityTracker

__all__ = [
    # Models
    "Entity",
    "EntityRelation",
    "EntityType",
    "ExtractedEntityInfo",
    "MemoryEntityLink",
    "RelationType",
    # Extraction
    "EntityExtractor",
    "RuleBasedEntityExtractor",
    # Storage
    "EntityRepository",
    # High-level API
    "EntityTracker",
]
