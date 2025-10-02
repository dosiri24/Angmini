#!/usr/bin/env python
"""CrewAI 통합 테스트 스크립트"""

from ai.core.config import Config
from ai.ai_brain import AIBrain
from ai.memory.factory import create_memory_service
from crew import AngminiCrew

def main():
    # 설정 로드
    config = Config.load()

    # AI Brain 초기화
    ai_brain = AIBrain(config)
    print("✅ AI Brain 초기화 완료")

    # 메모리 서비스 초기화
    try:
        memory_service = create_memory_service()
        print("✅ 메모리 서비스 초기화 완료")
    except Exception as e:
        print(f"⚠️ 메모리 서비스 초기화 실패: {e}")
        memory_service = None

    # CrewAI 초기화
    crew = AngminiCrew(
        ai_brain=ai_brain,
        memory_service=memory_service,
        config=config,
        verbose=True  # 상세 출력
    )
    print("✅ AngminiCrew 초기화 완료")

    # 테스트 쿼리
    test_queries = [
        "안녕하세요!",
        "현재 디렉토리 파일 목록 보여줘"
    ]

    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"🎯 쿼리: {query}")
        print('='*50)

        try:
            result = crew.kickoff(query)
            print(f"\n✅ 결과: {result}")
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()