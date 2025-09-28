"""Memory subsystem primitives for the Personal AI Assistant."""

from .cascaded_retriever import (
    CascadedMemoryMatch,
    CascadedRetrievalResult,
    CascadedRetriever,
    RetrievalIterationMetrics,
)
from .deduplicator import MemoryDeduplicator
from .embedding import QwenEmbeddingModel
from .memory_curator import MemoryCurator
from .memory_records import MemoryCategory, MemoryRecord, MemorySourceData
from .pipeline import MemoryPipeline, MemoryPipelineResult
from .metrics import MemoryMetrics
from .retention_policy import MemoryRetentionDecision, MemoryRetentionPolicy
from .service import MemoryCaptureResult, MemoryService
from .snapshot_extractor import SnapshotExtractor
from .storage import (
    BaseMemoryStore,
    FaissVectorIndex,
    MemoryRepository,
    SqliteMemoryStore,
    VectorIndex,
    VectorIndexResult,
)

__all__ = [
    "MemoryCurator",
    "MemoryDeduplicator",
    "MemoryPipeline",
    "MemoryPipelineResult",
    "MemoryService",
    "MemoryCaptureResult",
    "QwenEmbeddingModel",
    "MemoryRepository",
    "SqliteMemoryStore",
    "FaissVectorIndex",
    "BaseMemoryStore",
    "VectorIndex",
    "VectorIndexResult",
    "MemoryCategory",
    "MemoryRecord",
    "MemorySourceData",
    "MemoryRetentionDecision",
    "MemoryRetentionPolicy",
    "SnapshotExtractor",
    "CascadedRetriever",
    "CascadedRetrievalResult",
    "CascadedMemoryMatch",
    "RetrievalIterationMetrics",
    "MemoryMetrics",
]
