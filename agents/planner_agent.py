"""
agents/planner_agent.py
메인 플래너 에이전트 - 작업 분석 및 조율
"""
from typing import Optional, List
from .base_agent import BaseAngminiAgent
from ai.react_engine.loop_detector import LoopDetector
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

    def role(self) -> str:
        return "작업 계획 및 조율 총괄 책임자"

    def goal(self) -> str:
        return "사용자 요청을 분석하여 최적의 실행 계획을 수립하고 서브 에이전트들을 조율"

    def backstory(self) -> str:
        # 기존 system_prompt 내용을 활용
        try:
            with open('ai/react_engine/prompt_templates/system_prompt.md', 'r', encoding='utf-8') as f:
                original_prompt = f.read()
        except:
            original_prompt = ""

        return f"""
        당신은 Angmini의 메인 플래너입니다.
        사용자 요청을 받아 어떤 전문 에이전트들이 필요한지 판단하고 작업을 조율합니다.

        **핵심 원칙**:
        {original_prompt[:500] if original_prompt else "사용자 중심 설계, 효율성, 신뢰성"}

        **추가 책임**:
        - 사용자 의도 파악 (대화 vs 작업 요청)
        - 필요한 전문 에이전트 선택
        - 작업 순서 결정 (순차/병렬)
        - 에이전트 간 데이터 전달 관리
        - 실패 시 재계획 수립
        - 최종 결과 통합 및 검증

        **사용 가능한 전문 에이전트**:
        - File Agent: 파일 시스템 작업
        - Notion Agent: Notion 워크스페이스 관리
        - Memory Agent: 과거 경험 검색
        - System Agent: macOS 시스템 작업

        **계획 수립 원칙**:
        1. 사용자 요청 정확히 이해
        2. 필요한 에이전트 최소화
        3. 병렬 실행 가능한 작업 파악
        4. 의존성 관계 고려
        5. 실패 시나리오 대비
        6. 효율적인 리소스 활용

        **무한 루프 방지**:
        - 반복되는 실패 패턴 감지
        - 최대 재시도 횟수 제한
        - 대안 전략 수립
        """

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

    def create_execution_plan(self, user_request: str) -> dict:
        """사용자 요청을 분석하여 실행 계획 수립"""
        # 메모리 컨텍스트 조회
        memory_context = self.get_memory_context(user_request, top_k=3)

        plan = {
            "user_intent": self._analyze_intent(user_request),
            "required_agents": [],
            "execution_order": "sequential",  # or "parallel"
            "tasks": [],
            "memory_context": memory_context,
        }

        # 의도 분석 기반 에이전트 선택
        if "파일" in user_request or "file" in user_request.lower():
            plan["required_agents"].append("FileAgent")
        if "notion" in user_request.lower() or "할일" in user_request:
            plan["required_agents"].append("NotionAgent")
        if "경험" in user_request or "예전" in user_request or "과거" in user_request:
            plan["required_agents"].append("MemoryAgent")
        if "메모" in user_request or "알림" in user_request or "캘린더" in user_request:
            plan["required_agents"].append("SystemAgent")

        return plan

    def _analyze_intent(self, user_request: str) -> str:
        """사용자 의도 분석"""
        request_lower = user_request.lower()

        # 인사/대화 패턴
        greetings = ["안녕", "hello", "hi", "반가워"]
        if any(g in request_lower for g in greetings):
            return "greeting"

        # 작업 요청 패턴
        action_words = ["만들", "생성", "추가", "삭제", "수정", "찾", "검색", "보여", "읽"]
        if any(a in user_request for a in action_words):
            return "task_request"

        # 질문 패턴
        if "?" in user_request or any(q in user_request for q in ["뭐", "어떻게", "왜", "언제"]):
            return "question"

        return "unknown"