"""High-level memory repository combining metadata store and vector index."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple
from uuid import uuid4

from ai.core.logger import get_logger

from ..embedding import QwenEmbeddingModel
from ..memory_records import MemoryRecord
from .base import BaseMemoryStore, VectorIndex


class MemoryRepository:
    """Coordinates storage, embedding, and retrieval of memory records."""

    def __init__(
        self,
        store: BaseMemoryStore,
        *,
        vector_index: VectorIndex | None = None,
        embedder: QwenEmbeddingModel | None = None,
    ) -> None:
        self._store = store
        self._vector_index = vector_index
        self._embedder = embedder
        self._logger = get_logger(self.__class__.__name__)

    def add(self, record: MemoryRecord) -> MemoryRecord:
        record_id = self._ensure_record_id(record)

        if self._vector_index and self._embedder:
            embedding = self._embedder.embed_single(self._embedding_payload(record))
            record.embedding = embedding
            self._vector_index.add(record_id, embedding)

        self._store.save(record)
        return record

    def bulk_add(self, records: Iterable[MemoryRecord]) -> None:
        for record in records:
            self.add(record)

    def list_all(self) -> List[MemoryRecord]:
        return list(self._store.list_all())

    def search(self, query: str, *, top_k: int = 5) -> List[Tuple[MemoryRecord, float]]:
        if not self._vector_index or not self._embedder:
            self._logger.warning("Vector index 또는 임베더가 설정되지 않아 검색을 수행할 수 없습니다.")
            return []

        embedding = self._embedder.embed_single(query)
        results = self._vector_index.search(embedding, top_k=top_k)
        if not results:
            return []

        records_by_id = {record.source_metadata.get("id"): record for record in self._store.list_all()}
        matches: List[Tuple[MemoryRecord, float]] = []
        for entry in results:
            record = records_by_id.get(entry.record_id)
            if record:
                matches.append((record, entry.score))
        return matches

    def _ensure_record_id(self, record: MemoryRecord) -> str:
        metadata = record.source_metadata
        record_id = metadata.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            record_id = str(uuid4())
            metadata["id"] = record_id
        return record_id

    @staticmethod
    def _embedding_payload(record: MemoryRecord) -> str:
        return "\n".join(filter(None, [record.summary, record.goal, record.user_intent]))
