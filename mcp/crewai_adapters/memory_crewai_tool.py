"""
mcp/crewai_adapters/memory_crewai_tool.py
기존 MemoryTool을 CrewAI BaseTool로 래핑
"""
from crewai.tools import BaseTool
from typing import Type, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from mcp.tools.memory_tool import MemoryTool, ToolResult
from ai.core.logger import get_logger


class MemoryToolInput(BaseModel):
    """MemoryTool 입력 스키마"""
    operation: str = Field(..., description="Operation: search_experiences, find_solutions, analyze_patterns")
    query: str = Field(..., description="Search query or topic to analyze")
    top_k: int = Field(default=3, description="Number of results to return")


class MemoryCrewAITool(BaseTool):
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
        """도구 실행"""
        self._logger.info(f"🔧 [MemoryTool] 실행 - operation={operation}, query={query}, top_k={top_k}")

        if not self._enabled:
            self._logger.warning("❌ [MemoryTool] 비활성화")
            return "❌ 메모리 도구가 비활성화됨"

        # MemoryTool 파라미터 구성
        params = {
            "operation": operation,
            "query": query,
            "top_k": top_k
        }

        try:
            result: ToolResult = self._memory_tool(**params)
            if result.success:
                self._logger.info(f"✅ [MemoryTool] 성공")
            else:
                self._logger.warning(f"❌ [MemoryTool] 실패: {result.error}")

            # 결과를 문자열로 변환
            if result.success:
                data = result.data
                if isinstance(data, dict):
                    if "memories" in data:
                        memories = data["memories"]
                        if not memories:
                            return "✅ 관련 경험을 찾을 수 없습니다."
                        output = f"✅ 관련 경험 {len(memories)}개 검색:\n"
                        for i, mem in enumerate(memories, 1):
                            output += f"\n{i}. {mem.get('summary', '요약 없음')}\n"
                            if mem.get('goal'):
                                output += f"   목표: {mem['goal']}\n"
                            if mem.get('outcome'):
                                output += f"   결과: {mem['outcome']}\n"
                            if mem.get('tools_used'):
                                output += f"   사용 도구: {', '.join(mem['tools_used'])}\n"
                        return output
                    elif "patterns" in data:
                        patterns = data["patterns"]
                        output = "✅ 발견된 패턴:\n"
                        for pattern in patterns:
                            output += f"  - {pattern}\n"
                        return output
                    else:
                        import json
                        return f"✅ 성공:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
                else:
                    return f"✅ 성공: {data}"
            else:
                return f"❌ 실패: {result.error}"
        except Exception as e:
            return f"❌ 도구 실행 오류: {str(e)}"