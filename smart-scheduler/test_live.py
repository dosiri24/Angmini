"""
실제 Gemini API + Tool 호출 상세 테스트.
도구 호출과 DB 저장까지 전체 플로우를 확인한다.
"""
import asyncio
import logging
from datetime import date

from agent import Agent
from database import Database
from config import config

# 로깅 설정 - 상세하게
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_full_flow():
    """전체 플로우 테스트: 자연어 → LLM → Tool 호출 → DB 저장 → 응답"""

    print("\n" + "="*60)
    print("🧪 SmartScheduler 전체 플로우 테스트")
    print("="*60)

    # DB 초기화 (테스트용 임시 DB) - Agent와 공유
    db = Database(":memory:")
    db.init_schema()

    # Agent 생성 - DB 공유
    agent = Agent(db=db)

    # 테스트 케이스들
    test_cases = [
        {
            "name": "1. 인사 테스트 (Tool 호출 없음)",
            "input": "안녕! 넌 누구야?",
            "check_tool": False,
        },
        {
            "name": "2. 일정 추가 (Tool 호출 필요)",
            "input": "내일 오후 2시에 강남역에서 친구 만남 일정 추가해줘",
            "check_tool": True,
            "expected_tool": "add_schedule",
        },
        {
            "name": "3. 오늘 일정 조회 (Tool 호출 필요)",
            "input": "오늘 일정 뭐 있어?",
            "check_tool": True,
            "expected_tool": "get_schedules_for_date",
        },
        {
            "name": "4. 이동시간 확인 (Tool 호출 필요)",
            "input": "오늘 오후 4시에 판교에서 미팅이 있는데, 이동시간 괜찮을까?",
            "check_tool": True,
            "expected_tool": "check_travel_time",
        },
    ]

    for tc in test_cases:
        print(f"\n{'─'*60}")
        print(f"📝 {tc['name']}")
        print(f"   입력: {tc['input']}")
        print(f"{'─'*60}")

        try:
            response = await agent.process_message(tc["input"])
            print(f"   ✅ 응답: {response}")

            if tc.get("check_tool"):
                print(f"   🔧 예상 Tool: {tc.get('expected_tool', 'any')}")

        except Exception as e:
            print(f"   ❌ 에러: {e}")
            import traceback
            traceback.print_exc()

    # DB 확인
    print(f"\n{'='*60}")
    print("📊 DB 상태 확인")
    print(f"{'='*60}")

    # 오늘 및 내일 일정 조회
    from datetime import timedelta
    today = date.today()
    tomorrow = today + timedelta(days=1)

    print(f"\n오늘({today}) 일정:")
    schedules_today = db.get_by_date(today)
    if schedules_today:
        for s in schedules_today:
            print(f"  - {s.title} ({s.start_time}) @ {s.location}")
    else:
        print("  (없음)")

    print(f"\n내일({tomorrow}) 일정:")
    schedules_tomorrow = db.get_by_date(tomorrow)
    if schedules_tomorrow:
        for s in schedules_tomorrow:
            print(f"  - {s.title} ({s.start_time}) @ {s.location}")
    else:
        print("  (없음)")

    # 메모리 상태
    print(f"\n{'='*60}")
    print("💾 대화 메모리 상태")
    print(f"{'='*60}")
    print(f"저장된 메시지 수: {len(agent.memory)}")
    for msg in agent.memory.get_messages():
        content_preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
        print(f"  [{msg.role}] {content_preview}")

    print(f"\n{'='*60}")
    print("✅ 테스트 완료!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(test_full_flow())
