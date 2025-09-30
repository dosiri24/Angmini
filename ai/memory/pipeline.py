"""Pipeline helpers that orchestrate snapshot extraction, retention, and curation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from ai.react_engine.models import ExecutionContext

from .deduplicator import MemoryDeduplicator
from .memory_curator import MemoryCurator
from .memory_records import MemoryRecord, MemorySourceData
from .retention_policy import MemoryRetentionDecision, MemoryRetentionPolicy
from .snapshot_extractor import SnapshotExtractor


@dataclass(slots=True)
class MemoryPipelineResult:
    record: Optional[MemoryRecord]
    retention: MemoryRetentionDecision
    duplicate_of: Optional[MemoryRecord]


class MemoryPipeline:
    """High-level utility that produces memory records when conditions are met."""

    def __init__(
        self,
        snapshot_extractor: SnapshotExtractor,
        retention_policy: MemoryRetentionPolicy,
        curator: MemoryCurator,
        *,
        deduplicator: MemoryDeduplicator | None = None,
    ) -> None:
        self._snapshot_extractor = snapshot_extractor
        self._retention_policy = retention_policy
        self._curator = curator
        self._deduplicator = deduplicator

    def run(
        self,
        context: ExecutionContext,
        *,
        user_request: str,
        existing_records: Iterable[MemoryRecord] | None = None,
    ) -> MemoryPipelineResult:
        source = self._snapshot_extractor.collect(context, user_request=user_request)
        decision = self._retention_policy.evaluate(context, source)
        if not decision.should_store:
            return MemoryPipelineResult(record=None, retention=decision, duplicate_of=None)

        record = self._curator.curate(source)

        duplicate: Optional[MemoryRecord] = None
        if self._deduplicator and existing_records:
            duplicate = self._deduplicator.find_duplicate(record, existing_records)
            if duplicate:
                record = self._deduplicator.merge(duplicate, record)

        return MemoryPipelineResult(record=record, retention=decision, duplicate_of=duplicate)
