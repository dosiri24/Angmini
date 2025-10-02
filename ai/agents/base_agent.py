"""
agents/base_agent.py
모든 에이전트의 공통 인터페이스 및 유틸리티
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from crewai import Agent
from ai.ai_brain import AIBrain
from ai.memory.service import MemoryService
from ai.core.logger import get_logger
from ai.core.config import Config
import os


class BaseAngminiAgent(ABC):
    """Angmini 전용 에이전트 베이스 클래스"""

    def __init__(
        self,
        ai_brain: Optional[AIBrain] = None,
        memory_service: Optional[MemoryService] = None,
        config: Optional[Config] = None,
        verbose: bool = True
    ):
        self.ai_brain = ai_brain
        self.memory_service = memory_service
        self.config = config or Config.load()
        self.verbose = verbose
        self._agent: Optional[Agent] = None
        self.logger = get_logger(self.__class__.__name__)

        # Gemini API 키 설정 (LiteLLM용)
        if self.config.gemini_api_key:
            os.environ["GEMINI_API_KEY"] = self.config.gemini_api_key

    @abstractmethod
    def role(self) -> str:
        """에이전트 역할"""
        pass

    @abstractmethod
    def goal(self) -> str:
        """에이전트 목표"""
        pass

    @abstractmethod
    def backstory(self) -> str:
        """에이전트 배경 스토리"""
        pass

    @abstractmethod
    def tools(self) -> list:
        """에이전트가 사용할 도구 리스트"""
        pass

    def build_agent(self) -> Agent:
        """CrewAI Agent 인스턴스 생성"""
        if self._agent is None:
            # Gemini 모델명 정리
            model_name = self.config.gemini_model
            if model_name.startswith("models/"):
                model_name = model_name.replace("models/", "")

            # hierarchical 모드에서 PlannerAgent는 반드시 delegation 필요
            allow_delegation = self.config.agent_allow_delegation
            if self.config.crew_process_type == "hierarchical" and self.role() == "작업 계획 및 조율 총괄 책임자":
                allow_delegation = True

            self._agent = Agent(
                role=self.role(),
                goal=self.goal(),
                backstory=self.backstory(),
                tools=self.tools(),
                llm=f"gemini/{model_name}",  # LiteLLM을 통한 Gemini 사용
                verbose=False,  # Rich console 출력 비활성화 (step_callback으로 대체)
                memory=True,  # CrewAI 메모리 활성화
                max_iter=self.config.agent_max_iter,  # Config에서 최대 반복 횟수 읽기
                allow_delegation=allow_delegation,
            )
            self.logger.info(f"Agent '{self.role()}' 생성 완료")
        return self._agent

    def get_memory_context(self, query: str, top_k: int = 3) -> str:
        """메모리에서 관련 컨텍스트 조회"""
        if not self.memory_service:
            return ""

        try:
            memories = self.memory_service.repository.search(query, top_k=top_k)
            if not memories:
                return ""

            context = "### 관련 경험:\n"
            for mem in memories:
                context += f"- {mem.summary}\n"
            return context
        except Exception as e:
            self.logger.warning(f"메모리 조회 실패: {e}")
            return ""

    def reset(self):
        """에이전트 인스턴스 초기화"""
        self._agent = None
        self.logger.debug(f"Agent '{self.role()}' 초기화됨")