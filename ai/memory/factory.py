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
