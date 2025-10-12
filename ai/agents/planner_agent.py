"""
agents/planner_agent.py
메인 플래너 에이전트 - 작업 분석 및 조율
"""
from typing import Optional, List
from .base_agent import BaseAngminiAgent
from ai.shared.loop_detector import LoopDetector
from ai.core.logger import get_logger
from ai.ai_brain import AIBrain
from ai.memory.service import MemoryService
from ai.core.config import Config


class PlannerAgent(BaseAngminiAgent):
    """작업 계획 및 조율 전문가"""

    def __init__(
        self,
        ai_brain: Optional[AIBrain] = None,
        memory_service: Optional[MemoryService] = None,
        config: Optional[Config] = None,
        verbose: bool = True
    ):
        super().__init__(ai_brain, memory_service, config, verbose)
        self.loop_detector = LoopDetector()  # 기존 로직 재사용
        self.logger = get_logger(__name__)
        # 마크다운에서 프롬프트 로드
        self._prompts = self._load_prompt_from_markdown()

    def role(self) -> str:
        return self._prompts['role']

    def goal(self) -> str:
        return self._prompts['goal']

    def backstory(self) -> str:
        # 마크다운에서 로드한 backstory에서 "Angmini"를 config의 assistant_name으로 교체
        assistant_name = self.config.ai_assistant_name if self.config else "Angmini"
        backstory = self._prompts['backstory']
        # "Angmini"를 실제 어시스턴트 이름으로 교체
        if assistant_name != "Angmini":
            backstory = backstory.replace("Angmini", assistant_name)
        return backstory

    def tools(self) -> list:
        # Planner는 직접 도구를 사용하지 않고, 다른 에이전트에게 위임
        return []

    def check_loop_risk(self, task_history: List[str]) -> bool:
        """무한 루프 위험 감지 (기존 LoopDetector 활용)"""
        if len(task_history) < 3:
            return False

        # 최근 3개 작업이 동일한지 확인
        recent_tasks = task_history[-3:]
        if len(set(recent_tasks)) == 1:
            self.logger.warning(f"루프 감지: 동일한 작업 반복 - {recent_tasks[0]}")
            return True

        return False
