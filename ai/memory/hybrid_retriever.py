"""Hybrid search combining semantic (vector) and keyword (FTS5) retrieval.

Uses Reciprocal Rank Fusion (RRF) to merge results from:
- FAISS vector similarity search
- SQLite FTS5 full-text search
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ai.core.logger import get_logger
from .memory_records import MemoryRecord
from .storage.vector_index import VectorIndex


@dataclass
class SearchResult:
    """Result from hybrid search.

    Attributes:
        record: Memory record that matched
        vector_score: Semantic similarity score (0.0-1.0)
        keyword_score: Keyword match score (0.0-1.0)
        rrf_score: Reciprocal Rank Fusion combined score
        rank: Final rank in merged results
    """

    record: MemoryRecord
    vector_score: float = 0.0
    keyword_score: float = 0.0
    rrf_score: float = 0.0
    rank: int = 0


class HybridRetriever:
    """Combines semantic and keyword search using RRF.

    Performs two parallel searches:
    1. Vector similarity search (FAISS)
    2. Full-text keyword search (SQLite FTS5)

    Then merges results using Reciprocal Rank Fusion algorithm.
    """

    def __init__(
        self,
        vector_index: VectorIndex,
        database_path: str | Path,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
        rrf_k: int = 60,
    ) -> None:
        """Initialize hybrid retriever.

        Args:
            vector_index: FAISS vector index for semantic search
            database_path: Path to SQLite database with FTS5 index
            vector_weight: Weight for semantic search (0.0-1.0)
            keyword_weight: Weight for keyword search (0.0-1.0)
            rrf_k: RRF constant (typically 60, higher = more aggressive fusion)
        """
        self._vector_index = vector_index
        self._db_path = Path(database_path)
        self._vector_weight = vector_weight
        self._keyword_weight = keyword_weight
        self._rrf_k = rrf_k
        self._logger = get_logger(self.__class__.__name__)

        # Validate weights
        if abs(vector_weight + keyword_weight - 1.0) > 0.01:
            self._logger.warning(
                f"Weights don't sum to 1.0: {vector_weight} + {keyword_weight}"
            )

    def search(
        self,
        query: str,
        top_k: int = 10,
        vector_k: Optional[int] = None,
        keyword_k: Optional[int] = None,
        min_rrf_score: float = 0.0,
    ) -> List[SearchResult]:
        """Perform hybrid search combining vector and keyword methods.

        Args:
            query: Search query string
            top_k: Number of final results to return
            vector_k: Number of results from vector search (default: top_k * 2)
            keyword_k: Number of results from keyword search (default: top_k * 2)
            min_rrf_score: Minimum RRF score to include in results

        Returns:
            List of SearchResult objects ranked by RRF score
        """
        # Default to fetching 2x results from each source for better fusion
        vector_k = vector_k or (top_k * 2)
        keyword_k = keyword_k or (top_k * 2)

        # Perform parallel searches
        vector_results = self._vector_search(query, k=vector_k)
        keyword_results = self._keyword_search(query, k=keyword_k)

        # Merge using RRF
        merged = self._reciprocal_rank_fusion(
            vector_results,
            keyword_results,
        )

        # Filter by minimum score
        filtered = [r for r in merged if r.rrf_score >= min_rrf_score]

        # Take top-k
        final_results = filtered[:top_k]

        # Assign final ranks
        for i, result in enumerate(final_results, start=1):
            result.rank = i

        self._logger.info(
            f"Hybrid search: {len(vector_results)} vector + {len(keyword_results)} keyword "
            f"→ {len(merged)} merged → {len(final_results)} final"
        )

        return final_results

    def _vector_search(self, query: str, k: int) -> List[Tuple[str, float]]:
        """Perform semantic similarity search using FAISS.

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of (memory_id, similarity_score) tuples
        """
        try:
            results = self._vector_index.search(query, k=k)
            # Vector index returns (memory_id, distance) - convert distance to similarity
            # Assuming cosine distance: similarity = 1 - distance
            return [(memory_id, max(0.0, 1.0 - distance)) for memory_id, distance in results]
        except Exception as e:
            self._logger.error(f"Vector search failed: {e}", exc_info=True)
            return []

    def _keyword_search(self, query: str, k: int) -> List[Tuple[str, float]]:
        """Perform full-text keyword search using SQLite FTS5.

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of (memory_id, relevance_score) tuples
        """
        try:
            with sqlite3.connect(self._db_path) as conn:
                # FTS5 MATCH query with BM25 ranking
                cursor = conn.execute(
                    """
                    SELECT m.external_id, rank
                    FROM memories_fts
                    JOIN memories m ON memories_fts.rowid = m.id
                    WHERE memories_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (self._prepare_fts_query(query), k),
                )

                results = []
                for row in cursor:
                    memory_id = row[0]
                    # FTS5 rank is negative (lower = better match)
                    # Convert to positive similarity score (0-1 range)
                    fts_rank = row[1]
                    score = self._normalize_fts_rank(fts_rank)
                    results.append((memory_id, score))

                return results

        except Exception as e:
            self._logger.error(f"Keyword search failed: {e}", exc_info=True)
            return []

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Tuple[str, float]],
        keyword_results: List[Tuple[str, float]],
    ) -> List[SearchResult]:
        """Merge results using Reciprocal Rank Fusion.

        RRF formula: score = sum(1 / (k + rank_i))
        where rank_i is the rank in each result list.

        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search

        Returns:
            Merged and ranked SearchResult list
        """
        # Build rank maps: memory_id -> (rank, score)
        vector_ranks = {
            memory_id: (rank + 1, score)  # rank is 1-indexed
            for rank, (memory_id, score) in enumerate(vector_results)
        }

        keyword_ranks = {
            memory_id: (rank + 1, score)
            for rank, (memory_id, score) in enumerate(keyword_results)
        }

        # Get all unique memory IDs
        all_memory_ids = set(vector_ranks.keys()) | set(keyword_ranks.keys())

        # Calculate RRF scores
        rrf_scores: Dict[str, Tuple[float, float, float]] = {}  # memory_id -> (rrf, vector_score, keyword_score)

        for memory_id in all_memory_ids:
            vector_rank, vector_score = vector_ranks.get(memory_id, (float('inf'), 0.0))
            keyword_rank, keyword_score = keyword_ranks.get(memory_id, (float('inf'), 0.0))

            # RRF score with weights
            vector_rrf = self._vector_weight / (self._rrf_k + vector_rank) if vector_rank != float('inf') else 0.0
            keyword_rrf = self._keyword_weight / (self._rrf_k + keyword_rank) if keyword_rank != float('inf') else 0.0

            rrf_score = vector_rrf + keyword_rrf

            rrf_scores[memory_id] = (rrf_score, vector_score, keyword_score)

        # Sort by RRF score descending
        sorted_ids = sorted(
            rrf_scores.keys(),
            key=lambda mid: rrf_scores[mid][0],
            reverse=True,
        )

        # Convert to SearchResult objects
        # Note: We need to load actual MemoryRecord objects here
        # For now, create placeholder results (integration point for actual repository)
        results = []
        for memory_id in sorted_ids:
            rrf_score, vector_score, keyword_score = rrf_scores[memory_id]

            # This is a placeholder - actual implementation should fetch from repository
            result = SearchResult(
                record=self._load_memory_stub(memory_id),
                vector_score=vector_score,
                keyword_score=keyword_score,
                rrf_score=rrf_score,
                rank=0,  # Will be set by caller
            )
            results.append(result)

        return results

    def _prepare_fts_query(self, query: str) -> str:
        """Prepare query string for FTS5 MATCH.

        Args:
            query: Original query string

        Returns:
            FTS5-formatted query string
        """
        # Simple preparation - can be enhanced with:
        # - Tokenization
        # - Stop word removal
        # - Stemming
        # - Boolean operators (AND, OR, NOT)

        # For now, just escape special characters and quote phrases
        # FTS5 supports: word, "phrase", word*, column:word, etc.

        # Remove special FTS5 characters that might cause syntax errors
        special_chars = ['"', '(', ')', '*', '^']
        cleaned = query
        for char in special_chars:
            cleaned = cleaned.replace(char, ' ')

        # Split into words and rejoin
        words = cleaned.split()

        # Simple OR query: match any word
        fts_query = ' OR '.join(words)

        return fts_query

    def _normalize_fts_rank(self, fts_rank: float) -> float:
        """Normalize FTS5 BM25 rank to 0-1 similarity score.

        FTS5 rank is negative (typically -10 to 0 range).
        Convert to positive similarity score.

        Args:
            fts_rank: FTS5 rank value (negative)

        Returns:
            Normalized score (0.0-1.0)
        """
        # FTS5 rank is negative, more negative = less relevant
        # Typical range: -20 to -1 for good matches
        # Convert to 0-1 scale with sigmoid-like function

        # Simple normalization: map [-20, 0] to [0, 1]
        min_rank = -20.0
        max_rank = 0.0

        if fts_rank >= max_rank:
            return 1.0
        elif fts_rank <= min_rank:
            return 0.0
        else:
            # Linear normalization
            normalized = (fts_rank - min_rank) / (max_rank - min_rank)
            return max(0.0, min(1.0, normalized))

    def _load_memory_stub(self, memory_id: str) -> MemoryRecord:
        """Load memory record stub for search result.

        This is a placeholder - actual implementation should use repository.

        Args:
            memory_id: Memory record ID

        Returns:
            MemoryRecord (stub for now)
        """
        from datetime import datetime
        from .memory_records import MemoryCategory

        # Placeholder - in real implementation, load from SQLite via repository
        return MemoryRecord(
            summary=f"Memory {memory_id}",
            goal="",
            user_intent="",
            outcome="",
            category=MemoryCategory.FULL_EXPERIENCE,
            tools_used=[],
            tags=[],
            created_at=datetime.utcnow(),
            source_metadata={"id": memory_id},
            embedding=None,
        )

    def get_statistics(self) -> Dict[str, any]:
        """Get retriever statistics and configuration.

        Returns:
            Dictionary with configuration and metrics
        """
        with sqlite3.connect(self._db_path) as conn:
            # Count FTS-indexed memories
            cursor = conn.execute("SELECT COUNT(*) FROM memories_fts")
            fts_count = cursor.fetchone()[0]

        return {
            "vector_weight": self._vector_weight,
            "keyword_weight": self._keyword_weight,
            "rrf_k": self._rrf_k,
            "fts_indexed_memories": fts_count,
            "vector_index_size": self._vector_index.size(),
        }
