"""
crew/crew_config.py
Crew 초기화 및 설정 관리
"""
from typing import Optional, List
from crewai import Crew, Process
from ai.ai_brain import AIBrain
from ai.memory.service import MemoryService
from ai.core.config import Config
from ai.core.logger import get_logger
from ai.agents import AgentFactory
import os


class AngminiCrew:
    """Angmini CrewAI 설정 및 초기화"""

    def __init__(
        self,
        ai_brain: Optional[AIBrain] = None,
        memory_service: Optional[MemoryService] = None,
        config: Optional[Config] = None,
        verbose: bool = False
    ):
        self.config = config or Config.load()
        self.ai_brain = ai_brain or AIBrain(self.config)
        self.memory_service = memory_service
        self.verbose = verbose
        self.logger = get_logger(__name__)

        # Gemini API 키 설정
        if self.config.gemini_api_key:
            os.environ["GEMINI_API_KEY"] = self.config.gemini_api_key

        # 에이전트 생성
        self.planner = AgentFactory.create_planner(
            self.ai_brain, self.memory_service, self.config
        )
        self.worker_agents = AgentFactory.create_all_agents(
            self.ai_brain, self.memory_service, self.config
        )

        self.logger.info(f"Crew 초기화 완료 - Planner + {len(self.worker_agents)} 워커")

    def _step_callback(self, step_output):
        """CrewAI 각 단계 실행 시 호출되는 콜백 - 간단한 로그 출력"""
        try:
            # 에이전트 정보 추출
            agent_name = getattr(step_output, 'agent', None)
            if isinstance(agent_name, str):
                agent_role = agent_name
            elif hasattr(agent_name, 'role'):
                agent_role = agent_name.role
            else:
                agent_role = "Unknown"

            # 도구 사용 정보
            tool_name = getattr(step_output, 'tool', None)

            # 작업 설명
            task_desc = ""
            if hasattr(step_output, 'task'):
                task = step_output.task
                if hasattr(task, 'description'):
                    desc = str(task.description).replace('\n', ' ').strip()
                    task_desc = desc[:60] + '...' if len(desc) > 60 else desc

            # 한 줄 로그 출력
            if tool_name:
                self.logger.info(f"Agent [{agent_role}] → Tool [{tool_name}]")
            elif task_desc:
                self.logger.info(f"Agent [{agent_role}] 시작: {task_desc}")
            else:
                self.logger.info(f"Agent [{agent_role}] 작업 중")

        except Exception as e:
            # 콜백 오류는 무시 (CrewAI 실행에 영향 없도록)
            self.logger.debug(f"Step callback 오류: {e}")

    def create_crew(self, tasks: List, process_type: Optional[str] = None) -> Crew:
        """Crew 인스턴스 생성"""
        # Gemini 모델명 정리
        model_name = self.config.gemini_model
        if model_name.startswith("models/"):
            model_name = model_name.replace("models/", "")

        # process_type이 지정되지 않으면 Config에서 읽기
        if process_type is None:
            process_type = self.config.crew_process_type

        # hierarchical mode의 경우 Planner를 맨 앞에 배치 (delegation 활용)
        if process_type == "hierarchical":
            # Planner + Workers 순서로 배치
            all_agents = [self.planner.build_agent()] + [agent.build_agent() for agent in self.worker_agents]
        else:
            # Sequential mode는 workers만
            all_agents = [agent.build_agent() for agent in self.worker_agents]

        self.logger.debug(f"Creating crew with {len(all_agents)} agents, process: {process_type}")

        # Task description을 50자로 제한하여 로그 출력
        task_summaries = []
        for t in tasks:
            desc = t.description.replace('\n', ' ').strip()
            if len(desc) > 50:
                desc = desc[:50] + '...'
            task_summaries.append(desc)
        self.logger.debug(f"Tasks: {task_summaries}")

        if process_type == "hierarchical":
            # Hierarchical: Planner가 첫 agent로 실행되며 다른 agents에게 delegation
            crew = Crew(
                agents=all_agents,  # Planner + Workers
                tasks=tasks,
                process=Process.sequential,  # Sequential로 실행하되 delegation 활용
                verbose=False,  # Rich console 출력 비활성화
                memory=self.config.crew_memory_enabled,
                output_log_file=False,
                step_callback=self._step_callback,
            )
        else:
            # Sequential: Workers만 순차 실행
            crew = Crew(
                agents=all_agents,
                tasks=tasks,
                process=Process.sequential,
                verbose=False,  # Rich console 출력 비활성화
                memory=self.config.crew_memory_enabled,
                output_log_file=False,
                step_callback=self._step_callback,
            )

        return crew

    def kickoff(self, user_input: str) -> str:
        """사용자 요청 실행"""
        from .task_factory import TaskFactory
        import time

        start_time = time.time()

        # Task 생성
        task_factory = TaskFactory(
            planner=self.planner,
            worker_agents=self.worker_agents,
            memory_service=self.memory_service
        )

        tasks = task_factory.create_tasks_from_input(user_input)
        self.logger.info(f"CrewAI 작업 시작 - Task: {len(tasks)}개")

        # Crew 실행
        crew = self.create_crew(tasks)

        try:
            result = crew.kickoff()
            execution_time = time.time() - start_time

            # 간단한 로그 출력
            result_text = str(result).strip()
            self.logger.info(f"CrewAI 완료 [{execution_time:.1f}초] - 결과: {len(result_text)}자")

            # 메트릭 간단히 출력 (INFO 레벨로 변경하여 항상 보이도록)
            if hasattr(crew, 'usage_metrics'):
                metrics = crew.usage_metrics
                total_tokens = getattr(metrics, 'total_tokens', 0)
                prompt_tokens = getattr(metrics, 'prompt_tokens', 0)
                completion_tokens = getattr(metrics, 'completion_tokens', 0)
                self.logger.info(f"토큰: {total_tokens} (입력: {prompt_tokens}, 출력: {completion_tokens})")

            # 메모리에 저장 (성공한 작업)
            if self.memory_service:
                try:
                    # 토큰 수 확인 (짧은 대화는 메모리 저장 건너뛰기)
                    total_tokens = 0
                    if hasattr(crew, 'usage_metrics'):
                        total_tokens = getattr(crew.usage_metrics, 'total_tokens', 0)

                    # 100 토큰 미만의 짧은 대화는 메모리 저장 안 함 (인사, 간단한 응답 등)
                    MIN_CONVERSATION_TOKENS = 100
                    if total_tokens < MIN_CONVERSATION_TOKENS:
                        self.logger.debug(
                            f"메모리 저장 건너뜀 - 짧은 대화 (토큰: {total_tokens} < {MIN_CONVERSATION_TOKENS})"
                        )
                    else:
                        from ai.shared.models import ExecutionContext
                        context = ExecutionContext(goal=user_input)

                        # scratchpad에 풍부한 정보 추가 (retention policy가 저장 여부 판단에 사용)
                        context.append_scratch(f"[사용자 요청]\n{user_input}\n")
                        context.append_scratch(f"\n[실행 결과]\n{result_text[:500]}\n")

                        # 도구 사용 정보 추가 (있다면)
                        if hasattr(crew, 'usage_metrics'):
                            context.append_scratch(f"\n[토큰 사용]\n입력: {getattr(crew.usage_metrics, 'prompt_tokens', 0)}, 출력: {getattr(crew.usage_metrics, 'completion_tokens', 0)}")

                        # metadata에 상세 정보 저장
                        context.metadata['final_result'] = result_text
                        context.metadata['execution_time'] = execution_time
                        context.metadata['user_input'] = user_input
                        context.metadata['task_count'] = len(tasks)
                        context.metadata['final_message'] = result_text  # retention policy가 체크하는 필드
                        context.metadata['total_tokens'] = total_tokens

                        capture_result = self.memory_service.capture(context, user_request=user_input)

                        if capture_result.stored:
                            self.logger.info(f"메모리 저장 완료 - ID: {capture_result.record_id}, 분류: {capture_result.category}")
                        else:
                            self.logger.debug(f"메모리 저장 건너뜀 - 이유: {capture_result.reason}")
                except Exception as e:
                    self.logger.warning(f"메모리 저장 실패: {e}")

            return str(result)

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"CrewAI 오류 [{execution_time:.1f}초]: {e}")
            raise

    def reset(self):
        """Crew 및 에이전트 상태 초기화"""
        self.planner.reset()
        for agent in self.worker_agents:
            agent.reset()
        self.logger.debug("Crew 초기화 완료")