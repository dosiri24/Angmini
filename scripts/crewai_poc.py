"""CrewAI 기본 동작 확인용 POC"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crewai import Agent, Task, Crew, Process
from ai.core.config import Config
from ai.core.logger import get_logger

logger = get_logger(__name__)

def main():
    # 설정 로드
    config = Config.load()

    # CrewAI는 LiteLLM을 통해 Gemini를 지원
    # GEMINI_API_KEY 환경변수가 이미 설정되어 있어야 함
    if not config.gemini_api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

    # LiteLLM을 통한 Gemini 사용 설정
    os.environ["GEMINI_API_KEY"] = config.gemini_api_key

    # Gemini 모델명 정리 (models/ 접두사 제거)
    model_name = config.gemini_model
    if model_name.startswith("models/"):
        model_name = model_name.replace("models/", "")

    # Gemini를 LLM으로 사용하는 테스트 에이전트
    test_agent = Agent(
        role='테스트 에이전트',
        goal='CrewAI 동작 확인',
        backstory='CrewAI 통합 테스트를 위한 에이전트입니다. 간단한 인사를 수행합니다.',
        verbose=True,
        # LiteLLM을 통해 Gemini 사용 (CrewAI가 내부적으로 처리)
        llm=f"gemini/{model_name}"  # gemini/gemini-1.5-pro 형식
    )

    test_task = Task(
        description='안녕하세요라고 인사하고, CrewAI가 잘 작동하고 있다고 알려주세요',
        expected_output='간단한 인사말과 작동 확인 메시지',
        agent=test_agent
    )

    crew = Crew(
        agents=[test_agent],
        tasks=[test_task],
        process=Process.sequential,
        verbose=True
    )

    try:
        result = crew.kickoff()
        logger.info("POC 성공!")
        print(f"\n=== 결과 ===\n{result}")
    except Exception as e:
        logger.error(f"POC 실패: {e}", exc_info=True)
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    main()