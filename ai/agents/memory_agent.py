"""
agents/memory_agent.py
장기 기억 관리 전문 에이전트
"""
from typing import Optional
from .base_agent import BaseAngminiAgent
from mcp.crewai_adapters.memory_crewai_tool import MemoryCrewAITool
from ai.memory.service import MemoryService
from ai.ai_brain import AIBrain
from ai.core.config import Config


class MemoryAgent(BaseAngminiAgent):
    """장기 기억 관리 전문가"""

    def __init__(
        self,
        ai_brain: Optional[AIBrain] = None,
        memory_service: Optional[MemoryService] = None,
        config: Optional[Config] = None,
        verbose: bool = True
    ):
        super().__init__(ai_brain, memory_service, config, verbose)
        # MemoryCrewAITool에 memory_service 전달
        self._memory_tool = MemoryCrewAITool(memory_service=memory_service)

    def role(self) -> str:
        return "장기 기억 및 경험 관리 전문가"

    def goal(self) -> str:
        return "과거 경험을 검색하고 관련성 있는 정보를 제공하여 더 나은 의사결정 지원"

    def backstory(self) -> str:
        return """
        당신은 Angmini의 장기 기억 시스템을 관리하는 전문가입니다.
        벡터 임베딩 기반 의미적 검색으로 관련 경험을 찾아냅니다.

        주요 책임:
        - 과거 실행 경험 검색
        - 유사한 문제의 해결 방법 찾기
        - 사용자 선호도 및 패턴 분석
        - 학습된 지식 활용
        - 경험 기반 추천 제공

        **검색 전략**:
        - 의미적 유사도 기반 검색
        - 컨텍스트 기반 필터링
        - 관련성 순위 정렬
        - 시간적 관련성 고려
        - 패턴 인식 및 추론

        **결과 보고 규칙**:
        - 검색된 경험을 **명확하고 구조화된 형태**로 반환
        - 각 경험의 요약, 관련도, 사용된 도구 등 포함
        - 검색 결과가 없을 경우에도 명확히 표시

        작업 원칙:
        - 정확한 경험 매칭
        - 컨텍스트를 고려한 검색
        - 프라이버시 보호
        - 효율적인 메모리 활용
        - 지속적인 학습 개선
        """

    def tools(self) -> list:
        return [self._memory_tool]