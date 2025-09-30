"""Interfaces for memory storage and vector index operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Sequence

from ..memory_records import MemoryRecord


class BaseMemoryStore(ABC):
    """Persistent storage for memory records and associated metadata."""

    @abstractmethod
    def save(self, record: MemoryRecord) -> None:
        """Persist or upsert the given record."""

    @abstractmethod
    def list_all(self) -> Iterable[MemoryRecord]:
        """Return all stored records."""


class VectorIndex(ABC):
    """Vector similarity index for memory search."""

    @abstractmethod
    def add(self, record_id: str, embedding: Sequence[float]) -> None:
        """Insert or update the embedding for a record."""

    @abstractmethod
    def search(self, embedding: Sequence[float], *, top_k: int = 5) -> Sequence["VectorIndexResult"]:
        """Return the most similar stored embeddings."""


class VectorIndexResult:
    """Result entry returned by vector similarity searches."""

    __slots__ = ("record_id", "score")

    def __init__(self, record_id: str, score: float) -> None:
        self.record_id = record_id
        self.score = score

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"VectorIndexResult(record_id={self.record_id!r}, score={self.score!r})"
