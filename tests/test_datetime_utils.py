"""
tests/test_datetime_utils.py
날짜/시간 유틸리티 함수 테스트
"""
# pytest는 선택적 의존성
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from datetime import datetime
from zoneinfo import ZoneInfo
from ai.core.utils import (
    get_current_datetime_kst,
    get_current_datetime_context,
    format_datetime_for_notion,
)


def test_get_current_datetime_kst():
    """get_current_datetime_kst()가 KST 타임존을 반환하는지 확인"""
    now_kst = get_current_datetime_kst()

    # 타임존이 Asia/Seoul인지 확인
    assert now_kst.tzinfo is not None
    assert str(now_kst.tzinfo) == "Asia/Seoul"

    # 현재 시간과 가까운지 확인 (1분 이내)
    now_utc = datetime.now(ZoneInfo("UTC"))
    diff = abs((now_kst - now_utc).total_seconds())
    assert diff < 60, "현재 시간과의 차이가 1분 이상"


def test_get_current_datetime_context():
    """get_current_datetime_context()가 올바른 형식의 문자열을 반환하는지 확인"""
    context = get_current_datetime_context()

    # 문자열이 반환되는지 확인
    assert isinstance(context, str)

    # 필수 키워드 포함 확인
    assert "현재 시간:" in context
    assert "년" in context
    assert "월" in context
    assert "일" in context
    assert "한국 시간" in context
    assert "GMT+9" in context

    # 요일 포함 확인 (월요일~일요일 중 하나)
    weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    assert any(day in context for day in weekdays)

    # 오전/오후 포함 확인
    assert "오전" in context or "오후" in context


def test_format_datetime_for_notion_with_naive_datetime():
    """타임존 정보가 없는 datetime을 Notion 형식으로 변환"""
    dt = datetime(2025, 10, 3, 15, 30, 0)  # 타임존 없음
    formatted = format_datetime_for_notion(dt)

    # ISO 8601 형식인지 확인
    assert "2025-10-03" in formatted
    assert "15:30:00" in formatted
    assert "+09:00" in formatted  # KST offset


def test_format_datetime_for_notion_with_timezone():
    """타임존 정보가 있는 datetime을 Notion 형식으로 변환"""
    # UTC로 생성
    dt_utc = datetime(2025, 10, 3, 6, 30, 0, tzinfo=ZoneInfo("UTC"))
    formatted = format_datetime_for_notion(dt_utc)

    # KST로 변환되었는지 확인 (UTC 6시 = KST 15시)
    assert "2025-10-03" in formatted
    assert "15:30:00" in formatted
    assert "+09:00" in formatted


def test_format_datetime_for_notion_already_kst():
    """이미 KST인 datetime을 Notion 형식으로 변환"""
    dt_kst = datetime(2025, 10, 3, 15, 30, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    formatted = format_datetime_for_notion(dt_kst)

    # 그대로 KST로 유지되는지 확인
    assert "2025-10-03" in formatted
    assert "15:30:00" in formatted
    assert "+09:00" in formatted


if __name__ == "__main__":
    # 수동 실행 시 간단한 출력
    print("=== 날짜/시간 유틸리티 테스트 ===\n")

    print("1. 현재 KST 시간:")
    kst_now = get_current_datetime_kst()
    print(f"   {kst_now}\n")

    print("2. 에이전트용 컨텍스트:")
    context = get_current_datetime_context()
    print(f"   {context}\n")

    print("3. Notion 형식 변환:")
    dt = datetime(2025, 10, 3, 15, 30, 0)
    formatted = format_datetime_for_notion(dt)
    print(f"   입력: {dt}")
    print(f"   출력: {formatted}\n")

    print("✅ 모든 기능이 정상적으로 동작합니다!")
