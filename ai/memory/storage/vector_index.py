"""FAISS-based vector index for memory embeddings."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import faiss
import numpy as np

from ai.core.logger import get_logger

from ..memory_records import MemoryRecord
from .base import VectorIndex, VectorIndexResult


class FaissVectorIndex(VectorIndex):
    """Maintain a simple FAISS index for cosine similarity searches."""

    def __init__(self, dimension: int, *, index_path: str | Path | None = None) -> None:
        self._dimension = dimension
        self._index_path = Path(index_path) if index_path else None
        self._logger = get_logger(self.__class__.__name__)
        self._index = faiss.IndexFlatIP(dimension)
        self._ids: list[str] = []
        if self._index_path and self._index_path.exists():
            self._load()

    def add(self, record_id: str, embedding: Sequence[float]) -> None:
        vector = np.asarray(embedding, dtype="float32")[np.newaxis, :]
        faiss.normalize_L2(vector)
        self._index.add(vector)
        self._ids.append(record_id)
        if self._index_path:
            self._save()

    def search(self, embedding: Sequence[float], *, top_k: int = 5) -> Sequence[VectorIndexResult]:
        if not self._ids:
            return []
        vector = np.asarray(embedding, dtype="float32")[np.newaxis, :]
        faiss.normalize_L2(vector)
        similarities, indices = self._index.search(vector, top_k)
        results: list[VectorIndexResult] = []
        for score, idx in zip(similarities[0], indices[0]):
            if idx == -1:
                continue
            results.append(VectorIndexResult(self._ids[idx], float(score)))
        return results

    def populate(self, records: Iterable[MemoryRecord]) -> None:
        if self._ids:
            return
        vectors: list[list[float]] = []
        ids: list[str] = []
        for record in records:
            if record.embedding:
                vectors.append(record.embedding)
                ids.append(record.source_metadata.get("id", record.summary) or record.summary)
        if not vectors:
            return
        matrix = np.asarray(vectors, dtype="float32")
        faiss.normalize_L2(matrix)
        self._index.add(matrix)
        self._ids.extend(ids)

    def _save(self) -> None:
        if not self._index_path:
            return
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._index_path))
        id_path = self._index_path.with_suffix(".ids")
        id_path.write_text("\n".join(self._ids), encoding="utf-8")
        self._logger.debug("FAISS index saved to %s", self._index_path)

    def _load(self) -> None:
        if not self._index_path:
            return
        self._index = faiss.read_index(str(self._index_path))
        id_path = self._index_path.with_suffix(".ids")
        if id_path.exists():
            self._ids = id_path.read_text(encoding="utf-8").splitlines()
        else:
            self._ids = []
        self._logger.debug("FAISS index loaded from %s", self._index_path)
