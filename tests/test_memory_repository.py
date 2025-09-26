"""Tests for the memory repository abstraction."""

from __future__ import annotations

from datetime import datetime

from ai.memory.memory_records import MemoryCategory, MemoryRecord
from ai.memory.storage import BaseMemoryStore, MemoryRepository, VectorIndex, VectorIndexResult
from ai.memory.storage.sqlite_store import SqliteMemoryStore


class DummyEmbedder:
    def embed_single(self, text: str) -> list[float]:
        return [float(len(text))]


class InMemoryVectorIndex(VectorIndex):
    def __init__(self) -> None:
        self.entries: dict[str, list[float]] = {}

    def add(self, record_id: str, embedding):  # noqa: ANN002
        self.entries[record_id] = list(embedding)

    def search(self, embedding, *, top_k: int = 5):  # noqa: ANN002
        record_id = next(iter(self.entries), None)
        if record_id is None:
            return []
        return [VectorIndexResult(record_id, 1.0)]


def test_repository_adds_record(tmp_path):
    db_path = tmp_path / "memory.db"
    store = SqliteMemoryStore(db_path)
    index = InMemoryVectorIndex()
    embedder = DummyEmbedder()
    repo = MemoryRepository(store, vector_index=index, embedder=embedder)

    record = MemoryRecord(
        summary="사용자의 일정 정리",
        goal="일정 관리",
        user_intent="일정을 정리하고 공유",
        outcome="성공",
        category=MemoryCategory.FULL_EXPERIENCE,
        tools_used=["notion"],
        tags=["schedule"],
        created_at=datetime.utcnow(),
        source_metadata={},
    )

    repo.add(record)

    stored = list(store.list_all())
    assert len(stored) == 1
    assert stored[0].summary == "사용자의 일정 정리"
    assert stored[0].source_metadata.get("id")
    assert index.entries


def test_repository_search_returns_matches(tmp_path):
    db_path = tmp_path / "memory.db"
    store = SqliteMemoryStore(db_path)
    index = InMemoryVectorIndex()
    embedder = DummyEmbedder()
    repo = MemoryRepository(store, vector_index=index, embedder=embedder)

    record = MemoryRecord(
        summary="사과 5개 구매 경험",
        goal="장보기",
        user_intent="사과를 사서 냉장고에 보관",
        outcome="성공",
        category=MemoryCategory.FULL_EXPERIENCE,
        tools_used=["notion"],
        tags=["shopping"],
        created_at=datetime.utcnow(),
        source_metadata={},
    )

    repo.add(record)

    results = repo.search("사과 구매")
    assert results
    retrieved, score = results[0]
    assert retrieved.summary.startswith("사과")
    assert score == 1.0
