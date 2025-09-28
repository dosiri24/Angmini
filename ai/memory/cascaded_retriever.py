"""LLM-assisted cascaded retrieval over the memory repository."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from ai.ai_brain import AIBrain
from ai.core.exceptions import EngineError
from ai.core.logger import get_logger

from .memory_records import MemoryRecord
from .storage import MemoryRepository


DEFAULT_MAX_DEPTH = 3
DEFAULT_TOP_K = 5
DEFAULT_MIN_SCORE = 0.35
DEFAULT_MAX_NO_NEW_RESULTS = 2
FILTER_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "cascaded_filter_prompt.md"


@dataclass(slots=True)
class CascadedMemoryMatch:
    """Outcome entry returned after cascaded retrieval."""

    record: MemoryRecord
    score: float
    reason: Optional[str] = None


@dataclass(slots=True)
class RetrievalIterationMetrics:
    """Telemetry produced per retrieval iteration."""

    query: str
    depth: int
    total_candidates: int
    kept: int
    follow_up_queries: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass(slots=True)
class CascadedRetrievalResult:
    """Aggregated cascaded retrieval outcome."""

    matches: List[CascadedMemoryMatch]
    iterations: List[RetrievalIterationMetrics]


class CascadedRetriever:
    """Coordinate multi-hop memory retrieval with an LLM filter."""

    def __init__(
        self,
        *,
        brain: AIBrain,
        repository: MemoryRepository,
        top_k: int = DEFAULT_TOP_K,
        max_depth: int = DEFAULT_MAX_DEPTH,
        min_score: float = DEFAULT_MIN_SCORE,
        max_no_new_results: int = DEFAULT_MAX_NO_NEW_RESULTS,
        filter_prompt_path: Path | None = None,
    ) -> None:
        self._brain = brain
        self._repository = repository
        self._top_k = max(top_k, 1)
        self._max_depth = max_depth
        self._min_score = min_score
        self._max_no_new_results = max_no_new_results
        self._logger = get_logger(self.__class__.__name__)
        self._prompt_template = self._load_prompt(filter_prompt_path)

    def retrieve(self, user_request: str) -> CascadedRetrievalResult:
        pending: List[Tuple[str, int]] = [(user_request, 0)]
        visited_queries: Set[str] = set()
        seen_ids: Set[str] = set()
        matches: List[CascadedMemoryMatch] = []
        iterations: List[RetrievalIterationMetrics] = []
        no_new_results_counter = 0

        while pending:
            query, depth = pending.pop(0)
            normalized_query = query.strip()
            if not normalized_query:
                continue
            if normalized_query.lower() in visited_queries:
                continue
            visited_queries.add(normalized_query.lower())

            if depth >= self._max_depth:
                self._logger.debug("Max depth reached (query=%s, depth=%d)", normalized_query, depth)
                continue

            start_time = time.perf_counter()
            results = self._repository.search(normalized_query, top_k=self._top_k)
            duration_ms = (time.perf_counter() - start_time) * 1000

            metrics = RetrievalIterationMetrics(
                query=normalized_query,
                depth=depth,
                total_candidates=len(results),
                kept=0,
                duration_ms=duration_ms,
            )

            if not results:
                iterations.append(metrics)
                no_new_results_counter += 1
                if no_new_results_counter >= self._max_no_new_results:
                    break
                continue

            try:
                filtered = self._filter_with_llm(
                    user_request=user_request,
                    current_query=normalized_query,
                    depth=depth,
                    candidates=results,
                )
            except EngineError as exc:
                self._logger.warning("LLM filter failed, falling back to score threshold: %s", exc)
                filtered = self._fallback_filter(results)

            new_matches = 0
            follow_up: List[str] = []
            for entry in filtered["keep"]:
                record = entry["record"]
                score = entry["score"]
                reason = entry.get("reason")
                record_id = self._record_id(record)
                if record_id is None or record_id in seen_ids:
                    continue
                if score < self._min_score:
                    continue
                matches.append(CascadedMemoryMatch(record=record, score=score, reason=reason))
                seen_ids.add(record_id)
                new_matches += 1

            metrics.kept = new_matches
            follow_up = filtered.get("follow_up_queries") or []
            metrics.follow_up_queries = follow_up
            iterations.append(metrics)

            if new_matches == 0:
                no_new_results_counter += 1
            else:
                no_new_results_counter = 0

            if no_new_results_counter >= self._max_no_new_results:
                break

            for follow_up_query in follow_up:
                candidate_query = follow_up_query.strip()
                if not candidate_query:
                    continue
                if candidate_query.lower() in visited_queries:
                    continue
                pending.append((candidate_query, depth + 1))

        return CascadedRetrievalResult(matches=matches, iterations=iterations)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _filter_with_llm(
        self,
        *,
        user_request: str,
        current_query: str,
        depth: int,
        candidates: Sequence[Tuple[MemoryRecord, float]],
    ) -> Dict[str, List[Dict[str, object]]]:
        prompt = self._render_prompt(user_request, current_query, depth, candidates)
        llm_response = self._brain.generate_text(
            prompt,
            temperature=0.1,
            max_output_tokens=800,
        )
        try:
            data = json.loads(llm_response.text)
        except json.JSONDecodeError as exc:
            raise EngineError("LLM filter가 JSON 형식을 반환하지 않았습니다.") from exc

        keep_entries: List[Dict[str, object]] = []
        follow_up_queries: List[str] = []

        raw_keep = data.get("keep") if isinstance(data, dict) else None
        if isinstance(raw_keep, list):
            for item in raw_keep:
                if not isinstance(item, dict):
                    continue
                keep_entries.append(item)

        raw_follow_up = data.get("follow_up_queries") if isinstance(data, dict) else None
        if isinstance(raw_follow_up, list):
            follow_up_queries = [
                str(query).strip()
                for query in raw_follow_up
                if isinstance(query, (str, bytes)) and str(query).strip()
            ][:3]

        prepared_keep: List[Dict[str, object]] = []
        candidate_map = {
            self._record_id(record): (record, score) for record, score in candidates
        }

        for entry in keep_entries:
            record_id = entry.get("id")
            if not isinstance(record_id, str):
                continue
            record_id = record_id.strip()
            record_tuple = candidate_map.get(record_id)
            if not record_tuple:
                continue
            record, score = record_tuple
            prepared_keep.append(
                {
                    "record": record,
                    "score": float(score),
                    "reason": self._coerce_reason(entry.get("reason")),
                }
            )

        if not prepared_keep:
            prepared_keep = self._fallback_filter(candidates)["keep"]

        return {
            "keep": prepared_keep,
            "follow_up_queries": follow_up_queries,
        }

    def _fallback_filter(
        self,
        candidates: Sequence[Tuple[MemoryRecord, float]],
    ) -> Dict[str, List[Dict[str, object]]]:
        keep: List[Dict[str, object]] = []
        for record, score in candidates:
            if score >= self._min_score:
                keep.append({
                    "record": record,
                    "score": float(score),
                    "reason": "score_above_threshold",
                })
        return {"keep": keep, "follow_up_queries": []}

    def _render_prompt(
        self,
        user_request: str,
        current_query: str,
        depth: int,
        candidates: Sequence[Tuple[MemoryRecord, float]],
    ) -> str:
        payload: List[Dict[str, object]] = []
        for record, score in candidates:
            payload.append(
                {
                    "id": self._record_id(record) or "",
                    "summary": record.summary,
                    "user_intent": record.user_intent,
                    "outcome": record.outcome,
                    "tags": list(record.tags),
                    "score": float(score),
                }
            )

        candidates_json = json.dumps(payload, ensure_ascii=False, indent=2)
        prompt = (
            self._prompt_template
            .replace("{{user_request}}", user_request)
            .replace("{{current_query}}", current_query)
            .replace("{{depth}}", str(depth))
            .replace("{{candidates_json}}", candidates_json)
        )
        return prompt

    def _load_prompt(self, prompt_path: Path | None) -> str:
        path = prompt_path or FILTER_PROMPT_PATH
        if not path.exists():
            raise EngineError(f"Cascaded retrieval 프롬프트를 찾을 수 없습니다: {path}")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _record_id(record: MemoryRecord) -> Optional[str]:
        record_id = record.source_metadata.get("id")
        if isinstance(record_id, str) and record_id.strip():
            return record_id.strip()
        return None

    @staticmethod
    def _coerce_reason(value: object) -> Optional[str]:
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                return trimmed
        return None
