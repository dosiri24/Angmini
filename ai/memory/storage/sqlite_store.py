"""SQLite-backed metadata store for memory records."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Iterable

from ai.core.logger import get_logger

from ..memory_records import MemoryCategory, MemoryRecord
from .base import BaseMemoryStore


_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE NOT NULL,
    summary TEXT NOT NULL,
    goal TEXT NOT NULL,
    user_intent TEXT NOT NULL,
    outcome TEXT NOT NULL,
    category TEXT NOT NULL,
    tools_used TEXT NOT NULL,
    tags TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_metadata TEXT NOT NULL,
    embedding TEXT
);
"""


class SqliteMemoryStore(BaseMemoryStore):
    """Persist memory records in a lightweight SQLite database."""

    def __init__(self, database_path: str | Path) -> None:
        self._path = Path(database_path)
        self._logger = get_logger(self.__class__.__name__)
        self._initialise()

    def save(self, record: MemoryRecord) -> None:
        payload = record.to_document()
        record_id = record.source_metadata.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("MemoryRecord.source_metadata['id']가 필요합니다.")

        embedding_json = json.dumps(payload.pop("embedding", None))
        tools_json = json.dumps(payload.pop("tools_used", []), ensure_ascii=False)
        tags_json = json.dumps(payload.pop("tags", []), ensure_ascii=False)
        metadata_json = json.dumps(payload.pop("source_metadata", {}), ensure_ascii=False)

        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """
                INSERT INTO memories
                (external_id, summary, goal, user_intent, outcome, category, tools_used, tags, created_at, source_metadata, embedding)
                VALUES (:external_id, :summary, :goal, :user_intent, :outcome, :category, :tools_used, :tags, :created_at, :source_metadata, :embedding)
                ON CONFLICT(external_id) DO UPDATE SET
                    summary=excluded.summary,
                    goal=excluded.goal,
                    user_intent=excluded.user_intent,
                    outcome=excluded.outcome,
                    category=excluded.category,
                    tools_used=excluded.tools_used,
                    tags=excluded.tags,
                    created_at=excluded.created_at,
                    source_metadata=excluded.source_metadata,
                    embedding=excluded.embedding
                """,
                {
                    "external_id": record_id,
                    "summary": payload["summary"],
                    "goal": payload["goal"],
                    "user_intent": payload["user_intent"],
                    "outcome": payload["outcome"],
                    "category": payload["category"],
                    "tools_used": tools_json,
                    "tags": tags_json,
                    "created_at": payload["created_at"],
                    "source_metadata": metadata_json,
                    "embedding": embedding_json,
                },
            )
            conn.commit()

    def list_all(self) -> Iterable[MemoryRecord]:
        with sqlite3.connect(self._path) as conn:
            cursor = conn.execute(
                "SELECT external_id, summary, goal, user_intent, outcome, category, tools_used, tags, created_at, source_metadata, embedding FROM memories"
            )
            for row in cursor:
                external_id = row[0]
                tools_used = json.loads(row[6])
                tags = json.loads(row[7])
                metadata = json.loads(row[9])
                metadata.setdefault("id", external_id)
                embedding_raw = row[10]
                embedding = json.loads(embedding_raw) if embedding_raw else None
                created_at = datetime.fromisoformat(row[8]) if row[8] else datetime.utcnow()
                record = MemoryRecord(
                    summary=row[1],
                    goal=row[2],
                    user_intent=row[3],
                    outcome=row[4],
                    category=MemoryCategory(row[5]),
                    tools_used=tools_used,
                    tags=tags,
                    created_at=created_at,
                    source_metadata=metadata,
                    embedding=embedding,
                )
                yield record

    def _initialise(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._path) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()
        self._logger.debug("SQLite memory store initialised at %s", self._path)
