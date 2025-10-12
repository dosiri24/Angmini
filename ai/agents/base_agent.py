"""
agents/base_agent.py
모든 에이전트의 공통 인터페이스 및 유틸리티
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path
from crewai import Agent
from ai.ai_brain import AIBrain
from ai.memory.service import MemoryService
from ai.core.logger import get_logger
from ai.core.config import Config
from ai.core.exceptions import PromptLoadError
from ai.core.utils import get_current_datetime_context
import os
import re


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

            # 현재 날짜/시간 정보를 backstory에 추가
            backstory_with_time = self._add_datetime_context_to_backstory(self.backstory())

            self._agent = Agent(
                role=self.role(),
                goal=self.goal(),
                backstory=backstory_with_time,
                tools=self.tools(),
                llm=f"gemini/{model_name}",  # LiteLLM을 통한 Gemini 사용
                verbose=False,  # Rich console 출력 비활성화 (step_callback으로 대체)
                memory=True,  # CrewAI 메모리 활성화
                max_iter=self.config.agent_max_iter,  # Config에서 최대 반복 횟수 읽기
                allow_delegation=allow_delegation,
            )
            self.logger.info(f"Agent '{self.role()}' 생성 완료")
        return self._agent

    def _add_datetime_context_to_backstory(self, backstory: str) -> str:
        """
        backstory에 현재 날짜/시간 정보 추가

        Args:
            backstory: 원본 backstory 문자열

        Returns:
            str: 현재 시간 정보가 추가된 backstory
        """
        datetime_context = get_current_datetime_context()
        return f"{backstory}\n\n### 현재 시간 정보\n{datetime_context}\n별도 지시가 없는 한 모든 날짜/시간은 한국 시간(GMT+9)을 기준으로 합니다."

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

    @classmethod
    def _load_prompt_from_markdown(cls, prompt_filename: Optional[str] = None) -> Dict[str, str]:
        """
        마크다운 파일에서 프롬프트 로드

        Args:
            prompt_filename: 프롬프트 파일명 (None이면 클래스 이름 기반 자동 생성)

        Returns:
            Dict with 'role', 'goal', 'backstory' keys

        Raises:
            PromptLoadError: 파일을 찾을 수 없거나 파싱 실패 시
        """
        # 프롬프트 파일명 결정
        if prompt_filename is None:
            # 클래스 이름에서 파일명 생성 (예: PlannerAgent -> planner_agent_prompt.md)
            # 특별 케이스: AppleAppsAgent -> apple_apps_agent_prompt.md
            if cls.__name__ == "AppleAppsAgent":
                prompt_filename = "apple_apps_agent_prompt.md"
            else:
                # CamelCase를 snake_case로 변환
                class_name = cls.__name__
                # "Agent" 접미사 제거
                if class_name.endswith("Agent"):
                    class_name = class_name[:-5]  # "Agent" 제거

                # CamelCase를 snake_case로 변환
                snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
                prompt_filename = f"{snake_case}_agent_prompt.md"

        # 프롬프트 파일 경로
        prompts_dir = Path(__file__).parent / "prompts"
        prompt_file = prompts_dir / prompt_filename

        # 파일 존재 확인
        if not prompt_file.exists():
            raise PromptLoadError(
                f"프롬프트 파일을 찾을 수 없습니다: {prompt_file}\n"
                f"에이전트 클래스: {cls.__name__}"
            )

        # 파일 읽기
        try:
            content = prompt_file.read_text(encoding="utf-8")
        except Exception as e:
            raise PromptLoadError(
                f"프롬프트 파일을 읽을 수 없습니다: {prompt_file}\n"
                f"오류: {e}"
            )

        # 마크다운 파싱
        prompts = {}

        # ## Role 섹션 추출
        role_match = re.search(r'##\s*Role\s*\n+(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if not role_match:
            raise PromptLoadError(
                f"프롬프트 파일에서 '## Role' 섹션을 찾을 수 없습니다: {prompt_file}"
            )
        prompts['role'] = role_match.group(1).strip()

        # ## Goal 섹션 추출
        goal_match = re.search(r'##\s*Goal\s*\n+(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if not goal_match:
            raise PromptLoadError(
                f"프롬프트 파일에서 '## Goal' 섹션을 찾을 수 없습니다: {prompt_file}"
            )
        prompts['goal'] = goal_match.group(1).strip()

        # ## Backstory 섹션 추출
        backstory_match = re.search(r'##\s*Backstory\s*\n+(.*?)(?=\Z)', content, re.DOTALL)
        if not backstory_match:
            raise PromptLoadError(
                f"프롬프트 파일에서 '## Backstory' 섹션을 찾을 수 없습니다: {prompt_file}"
            )
        prompts['backstory'] = backstory_match.group(1).strip()

        return prompts