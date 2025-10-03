"""
ai/core/utils.py
공통 유틸리티 함수
"""
from datetime import datetime
from zoneinfo import ZoneInfo


def get_current_datetime_kst() -> datetime:
    """현재 한국 시간(KST, GMT+9) 반환"""
    return datetime.now(ZoneInfo("Asia/Seoul"))


def get_current_datetime_context() -> str:
    """
    에이전트에게 제공할 현재 날짜/시간 컨텍스트 문자열 생성

    Returns:
        str: 형식화된 현재 시간 정보 (예: "현재 시간: 2025년 10월 3일 목요일 오후 3시 45분 (한국 시간, GMT+9)")
    """
    now = get_current_datetime_kst()

    # 요일 한글 매핑
    weekdays_kr = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    weekday_kr = weekdays_kr[now.weekday()]

    # 오전/오후 구분
    am_pm = "오전" if now.hour < 12 else "오후"
    hour_12 = now.hour if now.hour <= 12 else now.hour - 12
    if hour_12 == 0:
        hour_12 = 12

    # 포맷팅
    datetime_str = (
        f"현재 시간: {now.year}년 {now.month}월 {now.day}일 {weekday_kr} "
        f"{am_pm} {hour_12}시 {now.minute}분 (한국 시간, GMT+9)"
    )

    return datetime_str


def format_datetime_for_notion(dt: datetime) -> str:
    """
    datetime 객체를 Notion API용 ISO 8601 형식(KST)으로 변환

    Args:
        dt: datetime 객체

    Returns:
        str: ISO 8601 형식 문자열 (예: "2025-10-03T15:45:00+09:00")
    """
    # 타임존이 없는 경우 KST로 간주
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("Asia/Seoul"))
    else:
        # 다른 타임존인 경우 KST로 변환
        dt = dt.astimezone(ZoneInfo("Asia/Seoul"))

    return dt.isoformat()
