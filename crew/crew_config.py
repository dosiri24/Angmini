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
        verbose: bool = True
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

    def create_crew(self, tasks: List, process_type: str = "hierarchical") -> Crew:
        """Crew 인스턴스 생성"""
        all_agents = [agent.build_agent() for agent in self.worker_agents]

        # Gemini 모델명 정리
        model_name = self.config.gemini_model
        if model_name.startswith("models/"):
            model_name = model_name.replace("models/", "")

        if process_type == "hierarchical":
            # Planner가 Manager 역할
            crew = Crew(
                agents=all_agents,
                tasks=tasks,
                process=Process.hierarchical,
                manager_agent=self.planner.build_agent(),
                verbose=self.verbose,
                memory=False,  # Disable CrewAI memory (we use our own)
                manager_llm=f"gemini/{model_name}",  # Manager용 LLM 명시
            )
        else:
            # 순차 실행
            crew = Crew(
                agents=all_agents,
                tasks=tasks,
                process=Process.sequential,
                verbose=self.verbose,
                memory=False  # Disable CrewAI memory (we use our own)
            )

        return crew

    def kickoff(self, user_input: str) -> str:
        """사용자 요청 실행"""
        from .task_factory import TaskFactory

        # Task 생성
        task_factory = TaskFactory(
            planner=self.planner,
            worker_agents=self.worker_agents,
            memory_service=self.memory_service
        )

        tasks = task_factory.create_tasks_from_input(user_input)

        # Crew 실행
        crew = self.create_crew(tasks, process_type="hierarchical")

        try:
            result = crew.kickoff()
            self.logger.info(f"Crew 실행 완료 - 결과: {len(str(result))} 문자")

            # 메모리에 저장 (성공한 작업)
            if self.memory_service:
                try:
                    from ai.react_engine.models import ExecutionContext
                    context = ExecutionContext()
                    context.goal = user_input
                    context.final_message = str(result)
                    self.memory_service.capture(context)
                except Exception as e:
                    self.logger.warning(f"메모리 저장 실패: {e}")

            return str(result)

        except Exception as e:
            self.logger.error(f"Crew 실행 오류: {e}", exc_info=True)
            raise

    def reset(self):
        """Crew 및 에이전트 상태 초기화"""
        self.planner.reset()
        for agent in self.worker_agents:
            agent.reset()
        self.logger.debug("Crew 초기화 완료")