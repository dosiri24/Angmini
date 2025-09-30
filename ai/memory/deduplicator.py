"""Simple heuristics for detecting and merging duplicate memory records."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from difflib import SequenceMatcher
from typing import Iterable, Optional

from .memory_records import MemoryRecord


class MemoryDeduplicator:
    """Detects near-duplicate memory records and merges their details."""

    def __init__(self, *, similarity_threshold: float = 0.85) -> None:
        self._similarity_threshold = similarity_threshold

    def find_duplicate(
        self,
        candidate: MemoryRecord,
        existing: Iterable[MemoryRecord],
    ) -> Optional[MemoryRecord]:
        for record in existing:
            if self._is_duplicate(record, candidate):
                return record
        return None

    def merge(self, base: MemoryRecord, other: MemoryRecord) -> MemoryRecord:
        summary = base.summary if len(base.summary) >= len(other.summary) else other.summary
        outcome = other.outcome or base.outcome
        tools = sorted({*base.tools_used, *other.tools_used})
        tags = sorted({*base.tags, *other.tags})

        metadata = dict(base.source_metadata)
        merge_log = metadata.setdefault("merge_history", [])
        if isinstance(merge_log, list):
            merge_log.append(
                {
                    "merged_at": datetime.utcnow().isoformat(),
                    "summary": other.summary,
                    "outcome": other.outcome,
                    "tags": other.tags,
                }
            )
        metadata["last_merged_at"] = datetime.utcnow().isoformat()

        embedding = base.embedding or other.embedding

        merged = replace(
            base,
            summary=summary,
            outcome=outcome,
            tools_used=tools,
            tags=tags,
            source_metadata=metadata,
            embedding=embedding,
        )
        return merged

    def _is_duplicate(self, record: MemoryRecord, candidate: MemoryRecord) -> bool:
        if record.goal.strip().lower() != candidate.goal.strip().lower():
            return False
        if record.user_intent.strip().lower() != candidate.user_intent.strip().lower():
            return False

        similarity = self._text_similarity(record.summary, candidate.summary)
        if similarity >= self._similarity_threshold:
            return True

        shared_tags = set(record.tags) & set(candidate.tags)
        if shared_tags and similarity >= (self._similarity_threshold - 0.1):
            return True
        return False

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        return SequenceMatcher(a=a.lower(), b=b.lower()).ratio()
