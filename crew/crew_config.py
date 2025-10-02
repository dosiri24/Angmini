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
from agents import AgentFactory
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

    def create_crew(self, tasks: List, process_type: Optional[str] = None) -> Crew:
        """Crew 인스턴스 생성"""
        all_agents = [agent.build_agent() for agent in self.worker_agents]

        # Gemini 모델명 정리
        model_name = self.config.gemini_model
        if model_name.startswith("models/"):
            model_name = model_name.replace("models/", "")

        # process_type이 지정되지 않으면 Config에서 읽기
        if process_type is None:
            process_type = self.config.crew_process_type

        self.logger.debug(f"Creating crew with {len(all_agents)} agents, process: {process_type}")
        self.logger.debug(f"Tasks: {[t.description[:50] + '...' if len(t.description) > 50 else t.description for t in tasks]}")

        if process_type == "hierarchical":
            # Planner가 Manager 역할
            crew = Crew(
                agents=all_agents,
                tasks=tasks,
                process=Process.hierarchical,
                manager_agent=self.planner.build_agent(),
                verbose=False,  # 박스 출력 완전 비활성화
                memory=self.config.crew_memory_enabled,
                manager_llm=f"gemini/{model_name}",
                output_log_file=False,  # 출력 로그 파일 비활성화
            )
        else:
            # 순차 실행
            crew = Crew(
                agents=all_agents,
                tasks=tasks,
                process=Process.sequential,
                verbose=False,  # 박스 출력 완전 비활성화
                memory=self.config.crew_memory_enabled,
                output_log_file=False,  # 출력 로그 파일 비활성화
            )

        return crew

    def kickoff(self, user_input: str) -> str:
        """사용자 요청 실행"""
        from .task_factory import TaskFactory
        import time
        import sys
        from io import StringIO

        start_time = time.time()

        # Task 생성
        task_factory = TaskFactory(
            planner=self.planner,
            worker_agents=self.worker_agents,
            memory_service=self.memory_service
        )

        tasks = task_factory.create_tasks_from_input(user_input)
        self.logger.info(f"CrewAI 작업 시작 - Task: {len(tasks)}개")

        # Crew 실행 (Rich 출력 억제)
        crew = self.create_crew(tasks)

        try:
            # Rich 콘솔 출력을 캡처하여 억제
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()

            try:
                result = crew.kickoff()
            finally:
                # stdout/stderr 복원
                sys.stdout = old_stdout
                sys.stderr = old_stderr

            execution_time = time.time() - start_time

            # 간단한 로그 출력
            result_text = str(result).strip()
            self.logger.info(f"CrewAI 완료 [{execution_time:.1f}초] - 결과: {len(result_text)}자")

            # 메트릭 간단히 출력
            if hasattr(crew, 'usage_metrics'):
                metrics = crew.usage_metrics
                total_tokens = getattr(metrics, 'total_tokens', 0)
                prompt_tokens = getattr(metrics, 'prompt_tokens', 0)
                completion_tokens = getattr(metrics, 'completion_tokens', 0)
                self.logger.debug(f"토큰: {total_tokens} (입력: {prompt_tokens}, 출력: {completion_tokens})")

            # 메모리에 저장 (성공한 작업)
            if self.memory_service:
                try:
                    from ai.react_engine.models import ExecutionContext
                    context = ExecutionContext(goal=user_input)
                    context.final_message = str(result)
                    self.memory_service.capture(context)
                    self.logger.debug("메모리 저장 완료")
                except Exception as e:
                    self.logger.debug(f"메모리 저장 건너뜀: {e}")

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