"""MCP tool exposing the memory repository search capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable, Dict, Iterable, List, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger
from ai.memory.factory import create_memory_repository
from ai.memory.metrics import MemoryMetrics
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
        metrics: MemoryMetrics | None = None,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._repository_factory = repository_factory or create_memory_repository
        self._config = config or MemoryToolConfig()
        self._logger = get_logger(self.__class__.__name__)
        self._metrics = metrics

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
        start = perf_counter()
        result: ToolResult | None = None
        success = False
        match_count = 0
        try:
            result = handler({"repository": repository, **kwargs})
            success = result.success
            match_count = self._extract_match_count(result.data)
            return result
        finally:
            elapsed_ms = (perf_counter() - start) * 1000.0
            self._record_metrics(
                operation=operation,
                success=success,
                match_count=match_count,
                latency_ms=elapsed_ms,
            )

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

    def _extract_match_count(self, data: Any) -> int:
        if isinstance(data, dict):
            matches = data.get("matches")
            if isinstance(matches, list):
                return len(matches)
        return 0

    def _record_metrics(
        self,
        *,
        operation: str,
        success: bool,
        match_count: int,
        latency_ms: float,
    ) -> None:
        if self._metrics is None:
            return
        self._metrics.record_retrieval(
            operation=operation,
            match_count=match_count,
            latency_ms=latency_ms,
            success=success,
        )
        self._logger.debug(
            "Memory retrieval metrics: %s",
            self._metrics.as_dict()["retrieval"],
        )

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


# ====================================================================
# CrewAI Adapter
# ====================================================================


class MemoryToolInput(BaseModel):
    """MemoryTool 입력 스키마"""
    operation: str = Field(..., description="Operation: search_experiences, find_solutions, analyze_patterns")
    query: str = Field(..., description="Search query or topic to analyze")
    top_k: int = Field(default=3, description="Number of results to return")


class MemoryCrewAITool(BaseTool):
    """CrewAI adapter for MemoryTool"""
    name: str = "메모리 도구"
    description: str = "과거 경험 검색, 해결책 찾기, 패턴 분석을 수행합니다."
    args_schema: Type[BaseModel] = MemoryToolInput

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, memory_service=None, **kwargs):
        super().__init__(**kwargs)
        self._logger = get_logger(__name__)
        try:
            self._memory_tool = MemoryTool()
            # 메모리 서비스 주입 (있는 경우)
            if memory_service:
                self._memory_tool.memory_service = memory_service
            self._enabled = True
        except Exception as e:
            self._memory_tool = None
            self._enabled = False
            self._logger.warning(f"MemoryTool 초기화 실패: {e}")

    def _run(
        self,
        operation: str,
        query: str,
        top_k: int = 3,
        **kwargs: Any
    ) -> str:
        """도구 실행 - MemoryTool의 run() 메서드를 호출하여 실제 작업 수행"""
        # 전체 파라미터 상세 로깅
        import json
        all_params = {
            "operation": operation,
            "query": query,
            "top_k": top_k,
            **kwargs
        }
        # None 값 제거
        logged_params = {k: v for k, v in all_params.items() if v is not None}
        self._logger.info(f"🔧 [MemoryCrewAITool] 실행 시작 - 파라미터: {json.dumps(logged_params, ensure_ascii=False, default=str)}")

        if not self._enabled:
            error_msg = "❌ 메모리 도구가 비활성화됨"
            self._logger.error(f"[MemoryCrewAITool] {error_msg}")
            return error_msg

        # MemoryTool 파라미터 구성
        params = {
            "operation": operation,
            "query": query,
            "top_k": top_k
        }

        self._logger.debug(f"[MemoryCrewAITool] MemoryTool로 전달할 파라미터: {json.dumps(params, ensure_ascii=False, default=str)}")

        try:
            # MemoryTool의 run() 메서드 호출
            self._logger.debug(f"[MemoryCrewAITool] MemoryTool.run() 호출 중...")
            result: ToolResult = self._memory_tool(**params)

            # 결과 검증 및 상세 로깅
            if result.success:
                # 성공 시 데이터 검증
                if not result.data:
                    warning_msg = "⚠️ 성공했으나 결과 데이터가 비어있음"
                    self._logger.warning(f"[MemoryCrewAITool] {warning_msg}")
                    return f"✅ 작업 완료 (데이터 없음)"

                # 결과 데이터 상세 로깅 (200자 제한)
                data_str = json.dumps(result.data, ensure_ascii=False, default=str)
                data_preview = data_str[:200] + ("..." if len(data_str) > 200 else "")
                self._logger.info(f"✅ [MemoryCrewAITool] 성공 - 결과: {data_preview}")

                # 성공 메시지 포맷팅
                return self._format_success_response(result.data, operation)
            else:
                # 실패 시 에러 상세 로깅 (200자 제한)
                error_str = str(result.error) if result.error else "알 수 없는 에러"
                error_preview = error_str[:200] + ("..." if len(error_str) > 200 else "")
                self._logger.error(f"❌ [MemoryCrewAITool] 실패 - 에러: {error_preview}")
                return f"❌ 메모리 작업 실패: {error_preview}"

        except ToolError as e:
            # ToolError는 MemoryTool에서 발생한 예상된 에러
            error_str = str(e)[:200]
            self._logger.error(f"❌ [MemoryCrewAITool] ToolError - {error_str}")
            return f"❌ 메모리 도구 에러: {error_str}"
        except Exception as e:
            # 예상치 못한 에러
            error_str = str(e)[:200]
            self._logger.exception(f"❌ [MemoryCrewAITool] 예상치 못한 에러 - {error_str}")
            return f"❌ 도구 실행 중 예외 발생: {error_str}"

    def _format_success_response(self, data: Any, operation: str) -> str:
        """성공 응답을 사용자 친화적인 형식으로 변환"""
        import json

        if isinstance(data, dict):
            if "matches" in data:
                # search_experiences 결과
                matches = data["matches"]
                if not matches:
                    return "✅ 관련 경험을 찾을 수 없습니다."
                output = f"✅ 관련 경험 {len(matches)}개 검색:\n"
                for i, mem in enumerate(matches, 1):
                    output += f"\n{i}. {mem.get('summary', '요약 없음')}\n"
                    if mem.get('goal'):
                        output += f"   목표: {mem['goal']}\n"
                    if mem.get('outcome'):
                        output += f"   결과: {mem['outcome']}\n"
                    if mem.get('tools_used'):
                        output += f"   사용 도구: {', '.join(mem['tools_used'])}\n"
                    if mem.get('score'):
                        output += f"   관련도: {mem['score']:.2f}\n"
                self._logger.info(f"[MemoryCrewAITool] 경험 검색 성공 - {len(matches)}개 결과")
                return output

            elif "tool_usage" in data or "tags" in data:
                # analyze_patterns 결과
                output = "✅ 발견된 패턴:\n"
                if "tool_usage" in data:
                    output += "\n도구 사용 패턴:\n"
                    for tool, count in data["tool_usage"]:
                        output += f"  - {tool}: {count}회\n"
                if "tags" in data:
                    output += "\n태그 패턴:\n"
                    for tag, count in data["tags"]:
                        output += f"  - {tag}: {count}회\n"
                if "total_records" in data:
                    output += f"\n총 기록 수: {data['total_records']}개\n"
                self._logger.info(f"[MemoryCrewAITool] 패턴 분석 성공 - 총 {data.get('total_records', 0)}개 기록")
                return output

            else:
                return f"✅ 성공:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
        else:
            return f"✅ 성공: {data}"
