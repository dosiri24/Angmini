"""
crew/task_factory.py
사용자 입력을 CrewAI Task로 변환
"""
from typing import List, Optional, Dict, Any
from crewai import Task
from agents.planner_agent import PlannerAgent
from agents.base_agent import BaseAngminiAgent
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
        """사용자 입력으로부터 Task 리스트 생성"""

        # 메모리에서 관련 컨텍스트 조회
        memory_context = ""
        if self.memory_service:
            try:
                memories = self.memory_service.repository.search(user_input, top_k=3)
                if memories:
                    memory_context = "\n\n### 관련 경험:\n"
                    for mem in memories:
                        memory_context += f"- {mem.summary}\n"
                        if hasattr(mem, 'tools_used') and mem.tools_used:
                            memory_context += f"  (사용 도구: {', '.join(mem.tools_used)})\n"
            except Exception as e:
                self.logger.warning(f"메모리 조회 실패: {e}")

        # Planner의 실행 계획 생성
        plan = self.planner.create_execution_plan(user_input)

        # 의도에 따른 Task 생성
        if plan["user_intent"] == "greeting":
            # 인사는 Planner가 직접 처리
            return [self._create_greeting_task(user_input)]

        elif plan["user_intent"] == "task_request":
            # 작업 요청은 Hierarchical로 처리
            return [self._create_planning_task(user_input, memory_context, plan)]

        elif plan["user_intent"] == "question":
            # 질문은 적절한 에이전트에게 위임
            return [self._create_question_task(user_input, memory_context, plan)]

        else:
            # 알 수 없는 요청은 Planner가 분석
            return [self._create_analysis_task(user_input, memory_context)]

    def _create_greeting_task(self, user_input: str) -> Task:
        """인사 응답 Task"""
        return Task(
            description=f"사용자 인사에 친근하게 응답: {user_input}",
            expected_output="친근한 인사말과 도움 제안",
            agent=self.planner.build_agent()
        )

    def _create_planning_task(
        self,
        user_input: str,
        memory_context: str,
        plan: Dict[str, Any]
    ) -> Task:
        """작업 계획 Task"""
        required_agents = plan.get("required_agents", [])
        agents_desc = ", ".join(required_agents) if required_agents else "적절한 에이전트"

        description = f"""
        사용자 요청: {user_input}
        {memory_context}

        다음을 수행하세요:
        1. 사용자 의도 정확히 파악
        2. 필요한 전문 에이전트 결정 (추천: {agents_desc})
        3. 작업 순서 결정 (병렬/순차)
        4. 각 에이전트에게 명확한 지시사항 전달
        5. 결과 통합 및 검증

        사용 가능한 에이전트:
        - 파일 시스템 관리 전문가: 파일/디렉토리 작업
        - Notion 워크스페이스 관리 전문가: 할일/프로젝트 관리
        - 장기 기억 및 경험 관리 전문가: 과거 경험 검색
        - macOS 시스템 통합 전문가: Apple 앱 연동
        """

        return Task(
            description=description,
            expected_output="실행 계획 및 에이전트 할당 결과",
            agent=self.planner.build_agent()
        )

    def _create_question_task(
        self,
        user_input: str,
        memory_context: str,
        plan: Dict[str, Any]
    ) -> Task:
        """질문 응답 Task"""
        description = f"""
        사용자 질문: {user_input}
        {memory_context}

        질문에 대해 정확하고 도움이 되는 답변을 제공하세요.
        필요한 경우 관련 에이전트의 도움을 받으세요.
        """

        return Task(
            description=description,
            expected_output="질문에 대한 명확한 답변",
            agent=self.planner.build_agent()
        )

    def _create_analysis_task(self, user_input: str, memory_context: str) -> Task:
        """분석 Task"""
        return Task(
            description=f"""
            사용자 요청 분석: {user_input}
            {memory_context}

            요청의 의도를 파악하고 적절한 대응 방안을 제시하세요.
            """,
            expected_output="요청 분석 결과 및 대응 방안",
            agent=self.planner.build_agent()
        )

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