"""High-level coordinator for memory capture and retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from ai.core.logger import get_logger

from .deduplicator import MemoryDeduplicator
from .factory import create_memory_repository
from .memory_curator import MemoryCurator
from .memory_records import MemoryRecord
from .metrics import MemoryMetrics
from .pipeline import MemoryPipeline
from .retention_policy import MemoryRetentionDecision, MemoryRetentionPolicy
from .snapshot_extractor import SnapshotExtractor
from .storage import MemoryRepository


@dataclass(slots=True)
class MemoryCaptureResult:
    should_store: bool
    reason: str
    stored: bool
    record_id: Optional[str]
    category: Optional[str]
    duplicate_id: Optional[str]
    record: Optional[MemoryRecord]


class MemoryService:
    """Bundles repository/pipeline logic for easy reuse across the agent."""

    def __init__(self, repository: MemoryRepository, pipeline: MemoryPipeline) -> None:
        self._repository = repository
        self._pipeline = pipeline
        self._logger = get_logger(self.__class__.__name__)
        self._metrics = MemoryMetrics()

    @property
    def repository(self) -> MemoryRepository:
        return self._repository

    @property
    def metrics(self) -> MemoryMetrics:
        return self._metrics

    @classmethod
    def build(cls, brain) -> "MemoryService":  # noqa: ANN001 - brain type is AIBrain
        repository = create_memory_repository()
        pipeline = MemoryPipeline(
            snapshot_extractor=SnapshotExtractor(),
            retention_policy=MemoryRetentionPolicy(brain=brain),
            curator=MemoryCurator(brain),
            deduplicator=MemoryDeduplicator(),
        )
        service = cls(repository=repository, pipeline=pipeline)
        return service

    def capture(self, context, user_request: str) -> MemoryCaptureResult:
        existing_records: Iterable[MemoryRecord] = self._repository.list_all()
        pipeline_result = self._pipeline.run(
            context,
            user_request=user_request,
            existing_records=existing_records,
        )

        duplicate_id: Optional[str] = None
        if pipeline_result.duplicate_of is not None:
            duplicate_id = pipeline_result.duplicate_of.source_metadata.get("id")

        stored_record: Optional[MemoryRecord] = None
        record_id: Optional[str] = None
        category: Optional[str] = None
        stored = False

        if pipeline_result.record is not None and pipeline_result.retention.should_store:
            record_to_store = pipeline_result.record
            metadata = record_to_store.source_metadata
            metadata["retention_reason"] = pipeline_result.retention.reason
            metadata["retention_timestamp"] = datetime.utcnow().isoformat()
            metadata["resolved"] = True

            stored_record = self._repository.add(record_to_store)
            stored = True
            record_id = stored_record.source_metadata.get("id")
            category = stored_record.category.value

        result = MemoryCaptureResult(
            should_store=pipeline_result.retention.should_store,
            reason=pipeline_result.retention.reason,
            stored=stored,
            record_id=record_id,
            category=category,
            duplicate_id=duplicate_id,
            record=stored_record,
        )
        self._metrics.record_capture(
            should_store=pipeline_result.retention.should_store,
            stored=stored,
            duplicate_detected=duplicate_id is not None,
        )
        self._logger.debug("Memory capture metrics: %s", self._metrics.as_dict()["capture"])
        return result

    def create_memory_tool(self):  # pragma: no cover - thin wrapper
        from mcp.tools.memory_tool import MemoryTool

        return MemoryTool(repository=self._repository)
