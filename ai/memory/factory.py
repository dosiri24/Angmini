"""Factory helpers for wiring up the memory repository and tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ai.core.exceptions import EngineError
from ai.core.logger import get_logger

# Allow duplicated OpenMP runtimes (PyTorch/FAISS on macOS can each bundle libomp).
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from .embedding import QwenEmbeddingModel
from .storage import FaissVectorIndex, MemoryRepository, SqliteMemoryStore


MEMORY_DB_ENV = "MEMORY_STORE_PATH"
MEMORY_INDEX_ENV = "MEMORY_INDEX_PATH"
MEMORY_INSTRUCTION_ENV = "MEMORY_EMBED_INSTRUCTION"


def create_memory_repository(
    *,
    database_path: Optional[str | Path] = None,
    index_path: Optional[str | Path] = None,
    instruction: Optional[str] = None,
) -> MemoryRepository:
    """Instantiate the repository with SQLite + FAISS backed by Qwen embeddings."""

    db_path = Path(database_path or os.getenv(MEMORY_DB_ENV, "data/memory/memories.db"))
    index_path = Path(index_path or os.getenv(MEMORY_INDEX_ENV, "data/memory/memory.index"))
    instruction = instruction or os.getenv(MEMORY_INSTRUCTION_ENV) or (
        "Given a user query, retrieve relevant stored experiences"
    )

    logger = get_logger("MemoryRepositoryFactory")
    logger.debug("Initialising memory repository", extra={"db_path": str(db_path), "index_path": str(index_path)})

    embedder = QwenEmbeddingModel(instruction=instruction)
    dimension = embedder.embedding_size
    if not dimension:
        probe = embedder.embed_single("dimension probe")
        if not probe:
            raise EngineError("Qwen 임베딩 모델이 벡터를 반환하지 않았습니다.")
        dimension = len(probe)

    vector_index = FaissVectorIndex(dimension, index_path=index_path)
    store = SqliteMemoryStore(db_path)
    vector_index.populate(store.list_all())

    repository = MemoryRepository(store, vector_index=vector_index, embedder=embedder)
    return repository


def create_memory_service(
    *,
    database_path: Optional[str | Path] = None,
    index_path: Optional[str | Path] = None,
    instruction: Optional[str] = None,
):
    """Create a full MemoryService with repository and pipeline configured."""
    # Late imports to avoid circular dependency
    from .service import MemoryService
    from .memory_curator import MemoryCurator
    from .deduplicator import MemoryDeduplicator
    from .retention_policy import MemoryRetentionPolicy
    from .snapshot_extractor import SnapshotExtractor
    from .pipeline import MemoryPipeline
    from ai.core.config import Config

    # Create repository
    repository = create_memory_repository(
        database_path=database_path,
        index_path=index_path,
        instruction=instruction
    )

    # Create pipeline components
    config = Config.load()
    from ai.ai_brain import AIBrain

    # Create AIBrain for curator
    brain = AIBrain(config)

    snapshot_extractor = SnapshotExtractor()
    retention_policy = MemoryRetentionPolicy()
    curator = MemoryCurator(brain)
    deduplicator = MemoryDeduplicator()  # No argument needed

    # Create pipeline
    pipeline = MemoryPipeline(
        snapshot_extractor=snapshot_extractor,
        retention_policy=retention_policy,
        curator=curator,
        deduplicator=deduplicator
    )

    # Create service
    service = MemoryService(repository=repository, pipeline=pipeline)

    return service


def create_entity_tracker(
    *,
    database_path: Optional[str | Path] = None,
    instruction: Optional[str] = None,
):
    """Create EntityTracker with LLM-based entity extraction.

    Args:
        database_path: Path to SQLite database
        instruction: Optional instruction for embedding model

    Returns:
        Configured EntityTracker instance
    """
    from .entity import EntityRepository, EntityExtractor, EntityTracker, RuleBasedEntityExtractor
    from ai.core.config import Config
    from ai.memory.llm.gemini_client import GeminiClient

    db_path = Path(database_path or os.getenv(MEMORY_DB_ENV, "data/memory/memories.db"))
    logger = get_logger("EntityTrackerFactory")
    logger.debug("Initialising entity tracker", extra={"db_path": str(db_path)})

    # Create components
    repository = EntityRepository(db_path)

    config = Config.load()
    llm_client = GeminiClient(
        api_key=config.gemini_api_key,
        model=config.gemini_model,
    )

    extractor = EntityExtractor(llm_client)
    fallback_extractor = RuleBasedEntityExtractor()

    tracker = EntityTracker(
        repository=repository,
        extractor=extractor,
        fallback_extractor=fallback_extractor,
    )

    return tracker


def create_hybrid_retriever(
    *,
    database_path: Optional[str | Path] = None,
    index_path: Optional[str | Path] = None,
    instruction: Optional[str] = None,
    vector_weight: float = 0.6,
    keyword_weight: float = 0.4,
):
    """Create HybridRetriever combining vector and keyword search.

    Args:
        database_path: Path to SQLite database (with FTS5 index)
        index_path: Path to FAISS index
        instruction: Optional instruction for embedding model
        vector_weight: Weight for semantic search (0.0-1.0)
        keyword_weight: Weight for keyword search (0.0-1.0)

    Returns:
        Configured HybridRetriever instance
    """
    from .hybrid_retriever import HybridRetriever

    db_path = Path(database_path or os.getenv(MEMORY_DB_ENV, "data/memory/memories.db"))
    index_path = Path(index_path or os.getenv(MEMORY_INDEX_ENV, "data/memory/memory.index"))
    instruction = instruction or os.getenv(MEMORY_INSTRUCTION_ENV) or (
        "Given a user query, retrieve relevant stored experiences"
    )

    logger = get_logger("HybridRetrieverFactory")
    logger.debug("Initialising hybrid retriever", extra={"db_path": str(db_path)})

    # Create embedding model and vector index
    embedder = QwenEmbeddingModel(instruction=instruction)
    dimension = embedder.embedding_size
    if not dimension:
        probe = embedder.embed_single("dimension probe")
        if not probe:
            raise EngineError("Qwen 임베딩 모델이 벡터를 반환하지 않았습니다.")
        dimension = len(probe)

    vector_index = FaissVectorIndex(dimension, index_path=index_path)

    # Populate vector index from database
    store = SqliteMemoryStore(db_path)
    vector_index.populate(store.list_all())

    # Create hybrid retriever
    retriever = HybridRetriever(
        vector_index=vector_index,
        database_path=db_path,
        vector_weight=vector_weight,
        keyword_weight=keyword_weight,
    )

    return retriever


def create_importance_scorer(
    *,
    database_path: Optional[str | Path] = None,
    frequency_weight: float = 0.25,
    recency_weight: float = 0.25,
    success_weight: float = 0.20,
    feedback_weight: float = 0.15,
    entity_weight: float = 0.15,
):
    """Create ImportanceScorer for memory importance tracking.

    Args:
        database_path: Path to SQLite database
        frequency_weight: Weight for access frequency
        recency_weight: Weight for temporal recency
        success_weight: Weight for outcome success
        feedback_weight: Weight for user feedback
        entity_weight: Weight for entity connections

    Returns:
        Configured ImportanceScorer instance
    """
    from .importance_scorer import ImportanceScorer

    db_path = Path(database_path or os.getenv(MEMORY_DB_ENV, "data/memory/memories.db"))
    logger = get_logger("ImportanceScorerFactory")
    logger.debug("Initialising importance scorer", extra={"db_path": str(db_path)})

    scorer = ImportanceScorer(
        database_path=db_path,
        frequency_weight=frequency_weight,
        recency_weight=recency_weight,
        success_weight=success_weight,
        feedback_weight=feedback_weight,
        entity_weight=entity_weight,
    )

    return scorer


def create_enhanced_memory_service(
    *,
    database_path: Optional[str | Path] = None,
    index_path: Optional[str | Path] = None,
    instruction: Optional[str] = None,
    enable_entity_tracking: bool = True,
    enable_hybrid_search: bool = True,
    enable_importance_scoring: bool = True,
):
    """Create enhanced MemoryService with all new features.

    Args:
        database_path: Path to SQLite database
        index_path: Path to FAISS index
        instruction: Optional instruction for embedding
        enable_entity_tracking: Enable Entity Memory system
        enable_hybrid_search: Enable Hybrid Search (FTS5 + Vector)
        enable_importance_scoring: Enable Importance Scoring

    Returns:
        Enhanced MemoryService with optional components
    """
    logger = get_logger("EnhancedMemoryServiceFactory")
    logger.info("Creating enhanced memory service with features: "
                f"entity={enable_entity_tracking}, "
                f"hybrid={enable_hybrid_search}, "
                f"importance={enable_importance_scoring}")

    # Create base service
    base_service = create_memory_service(
        database_path=database_path,
        index_path=index_path,
        instruction=instruction,
    )

    # Add entity tracking
    entity_tracker = None
    if enable_entity_tracking:
        entity_tracker = create_entity_tracker(
            database_path=database_path,
            instruction=instruction,
        )
        logger.info("Entity tracking enabled")

    # Add hybrid retriever
    hybrid_retriever = None
    if enable_hybrid_search:
        hybrid_retriever = create_hybrid_retriever(
            database_path=database_path,
            index_path=index_path,
            instruction=instruction,
        )
        logger.info("Hybrid search enabled")

    # Add importance scorer
    importance_scorer = None
    if enable_importance_scoring:
        importance_scorer = create_importance_scorer(
            database_path=database_path,
        )
        logger.info("Importance scoring enabled")

    # Attach enhanced components to service
    # These will be accessible as service.entity_tracker, service.hybrid_retriever, etc.
    base_service.entity_tracker = entity_tracker
    base_service.hybrid_retriever = hybrid_retriever
    base_service.importance_scorer = importance_scorer

    return base_service
