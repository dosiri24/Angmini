"""
crew/task_factory.py
사용자 입력을 CrewAI Task로 변환
"""
from typing import List, Optional, Dict, Any
from crewai import Task
from ai.agents.planner_agent import PlannerAgent
from ai.agents.base_agent import BaseAngminiAgent
from ai.memory.service import MemoryService
from ai.core.logger import get_logger


class TaskFactory:
    """Task 생성 팩토리"""

    def __init__(
        self,
        planner: PlannerAgent,
        worker_agents: List[BaseAngminiAgent],
        memory_service: Optional[MemoryService] = None
    ):
        self.planner = planner
        self.worker_agents = {agent.role(): agent for agent in worker_agents}
        self.memory_service = memory_service
        self.logger = get_logger(__name__)

    def create_tasks_from_input(self, user_input: str) -> List[Task]:
        """사용자 입력으로부터 Task 리스트 생성 - 100% LLM 기반"""

        # 메모리에서 관련 컨텍스트 조회
        memory_context = ""
        if self.memory_service:
            try:
                search_results = self.memory_service.repository.search(user_input, top_k=3)
                if search_results:
                    memory_context = "\n\n### 관련 경험:\n"
                    for mem, score in search_results:
                        memory_context += f"- {mem.summary}\n"
                        if hasattr(mem, 'tools_used') and mem.tools_used:
                            memory_context += f"  (사용 도구: {', '.join(mem.tools_used)})\n"
            except Exception as e:
                self.logger.warning(f"메모리 조회 실패: {e}")

        # PlannerAgent에게 모든 판단을 위임 (키워드 파싱 없음)
        description = f"""
        사용자 요청: {user_input}
        {memory_context}

        위 요청을 분석하고 적절한 전문 에이전트를 선택하여 작업을 수행하세요.

        **중요**: 최종 답변은 JSON이나 기술적 형식이 아닌, 자연스러운 한국어 문장으로 작성하세요.
        """.strip()

        return [Task(
            description=description,
            expected_output="""사용자가 이해하기 쉬운 자연스러운 한국어 답변.
            기술적 JSON, 딕셔너리, 코드 형식이 아닌 일반 대화체로 작성.
            예: "바탕화면에 총 5개의 파일이 있습니다: test.txt, image.png, ..."
            """,
            agent=self.planner.build_agent()
        )]

    def create_sequential_tasks(
        self,
        descriptions: List[str],
        agent_names: List[str]
    ) -> List[Task]:
        """순차 실행용 Task 생성 (명시적 순서)"""
        from agents import AgentFactory

        tasks = []

        for desc, agent_name in zip(descriptions, agent_names):
            if agent_name not in self.worker_agents:
                self.logger.warning(f"알 수 없는 에이전트 역할: {agent_name}")
                continue

            agent = self.worker_agents[agent_name]
            task = Task(
                description=desc,
                expected_output=f"{agent_name} 작업 결과",
                agent=agent.build_agent()
            )
            tasks.append(task)

        # Task 의존성 설정 (순차 실행)
        for i in range(1, len(tasks)):
            tasks[i].context = [tasks[i-1]]  # 이전 Task 결과를 컨텍스트로 사용

        self.logger.debug(f"순차 Task {len(tasks)}개 생성 완료")
        return tasks

    def create_parallel_tasks(
        self,
        task_descriptions: Dict[str, str]
    ) -> List[Task]:
        """병렬 실행용 Task 생성"""
        from agents import AgentFactory

        tasks = []

        for agent_role, description in task_descriptions.items():
            if agent_role not in self.worker_agents:
                self.logger.warning(f"알 수 없는 에이전트 역할: {agent_role}")
                continue

            agent = self.worker_agents[agent_role]
            task = Task(
                description=description,
                expected_output=f"{agent_role} 작업 결과",
                agent=agent.build_agent()
            )
            tasks.append(task)

        # 병렬 실행이므로 의존성 설정 없음
        self.logger.debug(f"병렬 Task {len(tasks)}개 생성 완료")
        return tasks