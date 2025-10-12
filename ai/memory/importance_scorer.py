"""Importance scoring system for memory records.

Calculates multi-factor importance scores based on:
- Access frequency (how often retrieved)
- Temporal recency (when last accessed)
- Success indicators (positive outcomes)
- User feedback (explicit ratings)
- Entity richness (number of tracked entities)
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ai.core.logger import get_logger
from .memory_records import MemoryRecord


@dataclass
class ImportanceScore:
    """Importance score breakdown for a memory record.

    Attributes:
        total_score: Final importance score (0.0-1.0)
        frequency_score: Access frequency component (0.0-1.0)
        recency_score: Temporal recency component (0.0-1.0)
        success_score: Outcome quality component (0.0-1.0)
        feedback_score: User feedback component (0.0-1.0)
        entity_score: Entity richness component (0.0-1.0)
    """

    total_score: float
    frequency_score: float = 0.0
    recency_score: float = 0.0
    success_score: float = 0.0
    feedback_score: float = 0.0
    entity_score: float = 0.0


class ImportanceScorer:
    """Calculate and track importance scores for memory records.

    Uses weighted combination of multiple factors:
    - Frequency: How often memory is retrieved/used
    - Recency: How recently memory was accessed
    - Success: Outcome quality (from tags, category)
    - Feedback: Explicit user ratings
    - Entity richness: Number of connected entities

    Scores decay over time using exponential decay formula.
    """

    def __init__(
        self,
        database_path: str | Path,
        frequency_weight: float = 0.25,
        recency_weight: float = 0.25,
        success_weight: float = 0.20,
        feedback_weight: float = 0.15,
        entity_weight: float = 0.15,
        decay_halflife_days: float = 30.0,
    ) -> None:
        """Initialize importance scorer.

        Args:
            database_path: Path to SQLite database
            frequency_weight: Weight for access frequency (0.0-1.0)
            recency_weight: Weight for temporal recency (0.0-1.0)
            success_weight: Weight for outcome success (0.0-1.0)
            feedback_weight: Weight for user feedback (0.0-1.0)
            entity_weight: Weight for entity connections (0.0-1.0)
            decay_halflife_days: Half-life for exponential decay (days)
        """
        self._db_path = Path(database_path)
        self._frequency_weight = frequency_weight
        self._recency_weight = recency_weight
        self._success_weight = success_weight
        self._feedback_weight = feedback_weight
        self._entity_weight = entity_weight
        self._decay_halflife = decay_halflife_days
        self._logger = get_logger(self.__class__.__name__)

        # Validate weights sum to 1.0
        total_weight = sum([
            frequency_weight,
            recency_weight,
            success_weight,
            feedback_weight,
            entity_weight,
        ])
        if abs(total_weight - 1.0) > 0.01:
            self._logger.warning(f"Weights don't sum to 1.0: {total_weight}")

        self._initialize_schema()

    def calculate_importance(
        self,
        memory_id: str,
        current_time: Optional[datetime] = None,
    ) -> ImportanceScore:
        """Calculate importance score for a memory record.

        Args:
            memory_id: Memory record ID
            current_time: Reference time for decay calculation (defaults to now)

        Returns:
            ImportanceScore with breakdown
        """
        current_time = current_time or datetime.utcnow()

        with sqlite3.connect(self._db_path) as conn:
            # Get memory metadata
            cursor = conn.execute(
                """
                SELECT created_at, tags, category, tools_used
                FROM memories
                WHERE external_id = ?
                """,
                (memory_id,),
            )
            row = cursor.fetchone()

            if not row:
                self._logger.warning(f"Memory {memory_id} not found")
                return ImportanceScore(total_score=0.0)

            created_at = datetime.fromisoformat(row[0])
            tags = row[1]  # JSON string
            category = row[2]
            tools_used = row[3]  # JSON string

            # Get access stats
            access_stats = self._get_access_stats(conn, memory_id)

            # Get entity count
            entity_count = self._get_entity_count(conn, memory_id)

            # Get user feedback
            feedback_rating = self._get_feedback_rating(conn, memory_id)

        # Calculate component scores
        frequency_score = self._calculate_frequency_score(
            access_count=access_stats["access_count"],
        )

        recency_score = self._calculate_recency_score(
            last_access=access_stats["last_access"],
            created_at=created_at,
            current_time=current_time,
        )

        success_score = self._calculate_success_score(
            category=category,
            tags=tags,
        )

        feedback_score = self._calculate_feedback_score(
            rating=feedback_rating,
        )

        entity_score = self._calculate_entity_score(
            entity_count=entity_count,
        )

        # Combine with weights
        total_score = (
            self._frequency_weight * frequency_score +
            self._recency_weight * recency_score +
            self._success_weight * success_score +
            self._feedback_weight * feedback_score +
            self._entity_weight * entity_score
        )

        return ImportanceScore(
            total_score=total_score,
            frequency_score=frequency_score,
            recency_score=recency_score,
            success_score=success_score,
            feedback_score=feedback_score,
            entity_score=entity_score,
        )

    def record_access(
        self,
        memory_id: str,
        access_type: str = "retrieval",
    ) -> None:
        """Record that a memory was accessed.

        Args:
            memory_id: Memory record ID
            access_type: Type of access (retrieval, update, etc.)
        """
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO memory_access_log (memory_id, access_time, access_type)
                VALUES (?, ?, ?)
                """,
                (memory_id, now, access_type),
            )
            conn.commit()

    def record_feedback(
        self,
        memory_id: str,
        rating: float,
        comment: str = "",
    ) -> None:
        """Record explicit user feedback for a memory.

        Args:
            memory_id: Memory record ID
            rating: User rating (0.0-1.0)
            comment: Optional feedback comment
        """
        if not (0.0 <= rating <= 1.0):
            raise ValueError(f"Rating must be 0.0-1.0, got {rating}")

        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO memory_feedback (memory_id, rating, comment, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(memory_id) DO UPDATE SET
                    rating=excluded.rating,
                    comment=excluded.comment,
                    created_at=excluded.created_at
                """,
                (memory_id, rating, comment, now),
            )
            conn.commit()

    def get_top_memories(
        self,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Tuple[str, ImportanceScore]]:
        """Get most important memories by score.

        Args:
            limit: Number of memories to return
            category: Optional category filter

        Returns:
            List of (memory_id, ImportanceScore) tuples
        """
        with sqlite3.connect(self._db_path) as conn:
            if category:
                cursor = conn.execute(
                    """
                    SELECT external_id FROM memories
                    WHERE category = ?
                    LIMIT ?
                    """,
                    (category, limit * 2),  # Fetch extra for scoring
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT external_id FROM memories
                    LIMIT ?
                    """,
                    (limit * 2,),
                )

            memory_ids = [row[0] for row in cursor]

        # Score all candidates
        scored = [
            (memory_id, self.calculate_importance(memory_id))
            for memory_id in memory_ids
        ]

        # Sort by total score descending
        scored.sort(key=lambda x: x[1].total_score, reverse=True)

        return scored[:limit]

    def _calculate_frequency_score(self, access_count: int) -> float:
        """Calculate score based on access frequency.

        Uses logarithmic scaling to prevent over-weighting very frequent accesses.

        Args:
            access_count: Number of times accessed

        Returns:
            Frequency score (0.0-1.0)
        """
        if access_count == 0:
            return 0.0

        # Logarithmic scaling: log(1 + count) / log(1 + max_reasonable_count)
        # Assumes 100 accesses is very high frequency
        max_count = 100
        score = math.log(1 + access_count) / math.log(1 + max_count)

        return min(1.0, score)

    def _calculate_recency_score(
        self,
        last_access: Optional[datetime],
        created_at: datetime,
        current_time: datetime,
    ) -> float:
        """Calculate score based on temporal recency.

        Uses exponential decay from last access or creation time.

        Args:
            last_access: Last access timestamp (None if never accessed)
            created_at: Creation timestamp
            current_time: Reference time for decay

        Returns:
            Recency score (0.0-1.0)
        """
        reference_time = last_access or created_at
        age_days = (current_time - reference_time).total_seconds() / (24 * 3600)

        # Exponential decay: score = 2^(-age / halflife)
        decay_factor = 2.0 ** (-age_days / self._decay_halflife)

        return max(0.0, min(1.0, decay_factor))

    def _calculate_success_score(
        self,
        category: str,
        tags: str,
    ) -> float:
        """Calculate score based on outcome success indicators.

        Args:
            category: Memory category
            tags: JSON string of tags

        Returns:
            Success score (0.0-1.0)
        """
        score = 0.5  # Neutral baseline

        # Category-based scoring
        if category == "workflow_optimisation":
            score += 0.3  # High value category
        elif category == "error_solution":
            score += 0.2  # Problem-solving

        # Tag-based scoring
        import json
        try:
            tag_list = json.loads(tags) if tags else []
        except:
            tag_list = []

        positive_tags = {"success", "solved", "completed", "optimized", "improved"}
        negative_tags = {"failed", "error", "incomplete", "blocked"}

        positive_count = sum(1 for tag in tag_list if tag.lower() in positive_tags)
        negative_count = sum(1 for tag in tag_list if tag.lower() in negative_tags)

        score += (positive_count * 0.1) - (negative_count * 0.15)

        return max(0.0, min(1.0, score))

    def _calculate_feedback_score(self, rating: Optional[float]) -> float:
        """Calculate score from explicit user feedback.

        Args:
            rating: User rating (0.0-1.0) or None

        Returns:
            Feedback score (0.0-1.0)
        """
        if rating is None:
            return 0.5  # Neutral if no feedback

        return rating

    def _calculate_entity_score(self, entity_count: int) -> float:
        """Calculate score based on entity richness.

        More entities = more contextual connections = higher importance.

        Args:
            entity_count: Number of linked entities

        Returns:
            Entity score (0.0-1.0)
        """
        if entity_count == 0:
            return 0.0

        # Logarithmic scaling: 10 entities is very rich
        max_count = 10
        score = math.log(1 + entity_count) / math.log(1 + max_count)

        return min(1.0, score)

    def _get_access_stats(
        self,
        conn: sqlite3.Connection,
        memory_id: str,
    ) -> Dict[str, any]:
        """Get access statistics for a memory.

        Returns:
            Dictionary with access_count and last_access
        """
        cursor = conn.execute(
            """
            SELECT COUNT(*), MAX(access_time)
            FROM memory_access_log
            WHERE memory_id = ?
            """,
            (memory_id,),
        )
        row = cursor.fetchone()

        access_count = row[0] if row and row[0] else 0
        last_access_str = row[1] if row and row[1] else None
        last_access = datetime.fromisoformat(last_access_str) if last_access_str else None

        return {
            "access_count": access_count,
            "last_access": last_access,
        }

    def _get_entity_count(
        self,
        conn: sqlite3.Connection,
        memory_id: str,
    ) -> int:
        """Get number of entities linked to memory."""
        cursor = conn.execute(
            """
            SELECT COUNT(*)
            FROM memory_entities
            WHERE memory_id = ?
            """,
            (memory_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else 0

    def _get_feedback_rating(
        self,
        conn: sqlite3.Connection,
        memory_id: str,
    ) -> Optional[float]:
        """Get user feedback rating for memory."""
        cursor = conn.execute(
            """
            SELECT rating
            FROM memory_feedback
            WHERE memory_id = ?
            """,
            (memory_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def _initialize_schema(self) -> None:
        """Initialize tracking tables if they don't exist."""
        schema = """
        -- Track memory access patterns
        CREATE TABLE IF NOT EXISTS memory_access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id TEXT NOT NULL,
            access_time TEXT NOT NULL,
            access_type TEXT DEFAULT 'retrieval'
        );

        CREATE INDEX IF NOT EXISTS idx_access_log_memory ON memory_access_log(memory_id);
        CREATE INDEX IF NOT EXISTS idx_access_log_time ON memory_access_log(access_time DESC);

        -- Track user feedback ratings
        CREATE TABLE IF NOT EXISTS memory_feedback (
            memory_id TEXT PRIMARY KEY,
            rating REAL NOT NULL,
            comment TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_feedback_rating ON memory_feedback(rating DESC);
        """

        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(schema)
            conn.commit()

        self._logger.debug("Importance scorer schema initialized")
