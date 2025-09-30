"""Utilities for tracking memory capture and retrieval metrics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict


@dataclass(slots=True)
class CaptureMetrics:
    attempts: int = 0
    stored: int = 0
    skipped: int = 0
    duplicates: int = 0

    def as_dict(self) -> Dict[str, float | int]:
        success_rate = (self.stored / self.attempts) if self.attempts else 0.0
        return {
            "attempts": self.attempts,
            "stored": self.stored,
            "skipped": self.skipped,
            "duplicates": self.duplicates,
            "success_rate": round(success_rate, 3),
        }


@dataclass(slots=True)
class RetrievalMetrics:
    requests: int = 0
    hits: int = 0
    misses: int = 0
    total_latency_ms: float = 0.0
    operation_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def record_operation(self, operation: str) -> None:
        key = operation.lower().strip() or "unknown"
        self.operation_counts[key] += 1

    def as_dict(self) -> Dict[str, float | int | Dict[str, int]]:
        hit_rate = (self.hits / self.requests) if self.requests else 0.0
        avg_latency = (self.total_latency_ms / self.requests) if self.requests else 0.0
        return {
            "requests": self.requests,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 3),
            "avg_latency_ms": round(avg_latency, 2),
            "operation_counts": dict(self.operation_counts),
        }


@dataclass(slots=True)
class MemoryMetrics:
    capture: CaptureMetrics = field(default_factory=CaptureMetrics)
    retrieval: RetrievalMetrics = field(default_factory=RetrievalMetrics)

    def record_capture(
        self,
        *,
        should_store: bool,
        stored: bool,
        duplicate_detected: bool,
    ) -> None:
        self.capture.attempts += 1
        if stored:
            self.capture.stored += 1
        else:
            self.capture.skipped += 1
        if duplicate_detected:
            self.capture.duplicates += 1

    def record_retrieval(
        self,
        *,
        operation: str,
        match_count: int,
        latency_ms: float,
        success: bool,
    ) -> None:
        self.retrieval.requests += 1
        self.retrieval.record_operation(operation)
        if success and match_count > 0:
            self.retrieval.hits += 1
        else:
            self.retrieval.misses += 1
        self.retrieval.total_latency_ms += max(latency_ms, 0.0)

    def as_dict(self) -> Dict[str, Dict[str, float | int | Dict[str, int]]]:
        return {
            "capture": self.capture.as_dict(),
            "retrieval": self.retrieval.as_dict(),
        }


__all__ = ["MemoryMetrics", "CaptureMetrics", "RetrievalMetrics"]
