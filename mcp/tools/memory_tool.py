"""MCP tool exposing the memory repository search capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger
from ai.memory.factory import create_memory_repository
from ai.memory.storage import MemoryRepository

from ..tool_blueprint import ToolBlueprint, ToolResult


OperationHandler = Callable[[Dict[str, Any]], ToolResult]


@dataclass(slots=True)
class MemoryToolConfig:
    default_top_k: int = 5


class MemoryTool(ToolBlueprint):
    """Search previously stored experiences using embeddings and metadata."""

    tool_name = "memory"
    description = "장기 기억 저장소를 조회하여 유사 경험과 해결 방법을 제공합니다"
    parameters: Dict[str, Any] = {
        "operation": {
            "type": "string",
            "enum": [
                "search_experience",
                "find_solution",
                "get_tool_guidance",
                "analyze_patterns",
            ],
            "description": "수행할 메모리 조회 작업",
        },
        "query": {
            "type": "string",
            "description": "검색에 사용할 자연어 질의",
        },
        "tool": {
            "type": "string",
            "description": "특정 도구 사용 기록만 확인하고 싶을 때 지정",
        },
        "top_k": {
            "type": "integer",
            "description": "검색 결과로 반환할 최대 개수",
        },
        "include_metadata": {
            "type": "boolean",
            "description": "true일 때 저장된 원본 메타데이터를 함께 반환",
        },
    }

    def __init__(
        self,
        repository: MemoryRepository | None = None,
        *,
        repository_factory: Callable[[], MemoryRepository] | None = None,
        config: MemoryToolConfig | None = None,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._repository_factory = repository_factory or create_memory_repository
        self._config = config or MemoryToolConfig()
        self._logger = get_logger(self.__class__.__name__)

        self._operation_map: Dict[str, OperationHandler] = {
            "search_experience": self._search_experience,
            "find_solution": self._find_solution,
            "get_tool_guidance": self._get_tool_guidance,
            "analyze_patterns": self._analyze_patterns,
        }

    def run(self, **kwargs: Any) -> ToolResult:
        operation_raw = kwargs.get("operation")
        if not isinstance(operation_raw, str):
            raise ToolError("operation 파라미터가 필요합니다.")
        operation = operation_raw.strip().lower()
        handler = self._operation_map.get(operation)
        if handler is None:
            raise ToolError(f"지원하지 않는 MemoryTool operation: {operation}")

        repository = self._get_repository()
        return handler({"repository": repository, **kwargs})

    def _get_repository(self) -> MemoryRepository:
        if self._repository is None:
            try:
                self._repository = self._repository_factory()
            except Exception as exc:  # pragma: no cover - runtime dependencies
                self._logger.error("Memory repository 초기화 실패", exc_info=True)
                raise ToolError(f"Memory repository를 초기화할 수 없습니다: {exc}") from exc
        return self._repository

    # ------------------------------------------------------------------
    # Operation handlers
    # ------------------------------------------------------------------

    def _search_experience(self, context: Dict[str, Any]) -> ToolResult:
        repository: MemoryRepository = context["repository"]
        query = self._require_query(context)
        top_k = self._resolve_top_k(context)

        matches = repository.search(query, top_k=top_k)
        if not matches:
            data = {"matches": []}
            return ToolResult(success=True, data=data)

        include_metadata = bool(context.get("include_metadata"))
        data = {"matches": [self._serialise_match(record, score, include_metadata) for record, score in matches]}
        return ToolResult(success=True, data=data)

    def _find_solution(self, context: Dict[str, Any]) -> ToolResult:
        repository: MemoryRepository = context["repository"]
        query = context.get("query")
        key = (query or "").strip()
        augmented_query = f"{key} 문제 해결".strip()
        results = repository.search(augmented_query or "문제 해결", top_k=self._resolve_top_k(context))
        include_metadata = bool(context.get("include_metadata"))
        filtered = [
            (record, score)
            for record, score in results
            if self._is_failure_record(record) or "failure" in record.tags
        ]
        if not filtered:
            # fallback: filter all records for failure tag
            fallback = [
                (record, 0.0)
                for record in repository.list_all()
                if self._is_failure_record(record) or "failure" in record.tags
            ]
            filtered = fallback[: self._resolve_top_k(context)]

        data = {"matches": [self._serialise_match(r, s, include_metadata) for r, s in filtered]}
        return ToolResult(success=True, data=data)

    def _get_tool_guidance(self, context: Dict[str, Any]) -> ToolResult:
        repository: MemoryRepository = context["repository"]
        tool_name = context.get("tool")
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise ToolError("tool 파라미터가 필요합니다.")
        tool_name = tool_name.strip().lower()

        records = [
            record
            for record in repository.list_all()
            if any(t.lower() == tool_name for t in record.tools_used)
        ]
        if not records:
            return ToolResult(success=True, data={"matches": []})

        matches = [
            self._serialise_match(record, score=1.0, include_metadata=bool(context.get("include_metadata")))
            for record in records[: self._resolve_top_k(context)]
        ]
        return ToolResult(success=True, data={"matches": matches})

    def _analyze_patterns(self, context: Dict[str, Any]) -> ToolResult:
        repository: MemoryRepository = context["repository"]
        records = repository.list_all()
        if not records:
            return ToolResult(success=True, data={"summary": "(no memories stored yet)"})

        tool_counts: Dict[str, int] = {}
        tag_counts: Dict[str, int] = {}
        for record in records:
            for tool in record.tools_used:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
            for tag in record.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        top_tools = sorted(tool_counts.items(), key=lambda item: item[1], reverse=True)[:5]
        top_tags = sorted(tag_counts.items(), key=lambda item: item[1], reverse=True)[:5]
        data = {
            "tool_usage": top_tools,
            "tags": top_tags,
            "total_records": len(records),
        }
        return ToolResult(success=True, data=data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _serialise_match(
        self,
        record,
        score: float,
        include_metadata: bool,
    ) -> Dict[str, Any]:
        payload = {
            "summary": record.summary,
            "goal": record.goal,
            "user_intent": record.user_intent,
            "outcome": record.outcome,
            "category": record.category.value,
            "tools_used": record.tools_used,
            "tags": record.tags,
            "score": score,
            "created_at": record.created_at.isoformat() if hasattr(record.created_at, "isoformat") else record.created_at,
        }
        if include_metadata:
            payload["source_metadata"] = record.source_metadata
        return payload

    def _resolve_top_k(self, kwargs: Dict[str, Any]) -> int:
        value = kwargs.get("top_k")
        if isinstance(value, int) and value > 0:
            return min(value, 20)
        return self._config.default_top_k

    def _require_query(self, kwargs: Dict[str, Any]) -> str:
        query = kwargs.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ToolError("query 파라미터가 필요합니다.")
        return query.strip()

    @staticmethod
    def _is_failure_record(record) -> bool:
        outcome = record.outcome.lower()
        return any(token in outcome for token in ("실패", "오류", "error", "fail"))
