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

    def _classify_intent(self, user_input: str) -> str:
        """LLM으로 사용자 의도 분류 (메모리 검색 전 실행)"""
        if not self.planner.ai_brain:
            return "task_request"  # 안전하게 작업 요청으로 간주

        classification_prompt = f"""다음 사용자 입력을 분석하여 의도를 판단하세요.

사용자 입력: {user_input}

의도 분류 기준:
- simple_conversation: 단순 인사, 일상 대화, 감사 표현 등
  예시: "안녕", "하이", "고마워", "잘 지내?", "수고했어", "반가워"

- task_request: 명확한 작업 요청이나 질문
  예시: "파일 목록 보여줘", "과거 작업 찾아줘", "Notion에서 할 일 가져와"

다음 중 정확히 하나만 응답하세요: simple_conversation 또는 task_request"""

        try:
            response = self.planner.ai_brain.generate_text(
                classification_prompt,
                temperature=0.3,
                max_output_tokens=50
            )
            intent = response.text.strip().lower()

            if "simple_conversation" in intent:
                self.logger.debug(f"의도 분류: 단순 대화 - '{user_input}'")
                return "simple_conversation"
            else:
                self.logger.debug(f"의도 분류: 작업 요청 - '{user_input}'")
                return "task_request"
        except Exception as e:
            self.logger.warning(f"의도 분류 실패: {e}, 기본값(task_request) 사용")
            return "task_request"

    def create_tasks_from_input(self, user_input: str) -> List[Task]:
        """사용자 입력으로부터 Task 리스트 생성 - 100% LLM 기반

        1단계: 의도 분류 (simple_conversation vs task_request)
        2단계: task_request인 경우에만 메모리 검색
        3단계: Task 생성
        """

        # 1단계: 의도 분류
        intent = self._classify_intent(user_input)

        # 2단계: 의도에 따라 메모리 검색 여부 결정
        memory_context = ""
        if intent == "task_request" and self.memory_service:
            try:
                self.logger.debug(f"메모리 검색 시작 (작업 요청 감지)")
                search_results = self.memory_service.repository.search(user_input, top_k=3)
                if search_results:
                    memory_context = "\n\n### 📚 관련 경험 (이미 검색 완료)\n"
                    for i, result in enumerate(search_results, 1):
                        memory_context += f"\n{i}. {result.summary}\n"
                        memory_context += f"   - 목표: {result.goal}\n"
                        if result.outcome:
                            memory_context += f"   - 결과: {result.outcome}\n"
                    memory_context += "\n**중요**: 위 내용은 이미 검색된 결과입니다. Memory Agent를 다시 호출하지 마세요.\n"
                else:
                    memory_context = "\n\n### 📚 관련 경험\n관련된 과거 기억이 없습니다.\n"
                self.logger.debug(f"메모리 검색 완료: {len(search_results)}개 발견")
            except Exception as e:
                self.logger.warning(f"메모리 검색 실패: {e}")
                memory_context = ""
        else:
            self.logger.debug(f"메모리 검색 건너뜀 (단순 대화)")

        # 3단계: Task 생성
        if intent == "simple_conversation":
            # 단순 대화: 메모리 검색 없이 바로 응답
            description = f"""
            사용자 요청: {user_input}

            위 요청은 단순 인사나 일상 대화입니다.
            자연스럽고 친근하게 응답하세요. 다른 에이전트에게 작업을 위임하지 마세요.

            **중요**: 최종 답변은 JSON이나 기술적 형식이 아닌, 자연스러운 한국어 문장으로 작성하세요.
            """.strip()
        else:
            # 작업 요청: 메모리 컨텍스트와 함께 작업 수행
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