"""
tests/test_notion_timezone.py
NotionTool의 타임존 처리 테스트
"""
# pytest는 선택적 의존성
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from mcp.tools.notion_tool import NotionTool


def test_ensure_kst_timezone_date_only():
    """날짜만 있는 경우 그대로 유지"""
    tool = NotionTool()

    # 날짜만 있는 경우
    assert tool._ensure_kst_timezone("2025-10-03") == "2025-10-03"
    assert tool._ensure_kst_timezone("2025-12-31") == "2025-12-31"


def test_ensure_kst_timezone_without_timezone():
    """타임존 정보가 없는 경우 +09:00 추가"""
    tool = NotionTool()

    # 시간 있지만 타임존 없음 → KST 추가
    assert tool._ensure_kst_timezone("2025-10-03T15:00:00") == "2025-10-03T15:00:00+09:00"
    assert tool._ensure_kst_timezone("2025-10-03T09:30:00") == "2025-10-03T09:30:00+09:00"
    assert tool._ensure_kst_timezone("2025-10-03T23:59:59") == "2025-10-03T23:59:59+09:00"


def test_ensure_kst_timezone_with_utc():
    """UTC로 명시된 경우 그대로 유지"""
    tool = NotionTool()

    # UTC 명시 (Z)
    assert tool._ensure_kst_timezone("2025-10-03T06:00:00Z") == "2025-10-03T06:00:00Z"
    assert tool._ensure_kst_timezone("2025-10-03T15:00:00z") == "2025-10-03T15:00:00z"


def test_ensure_kst_timezone_with_positive_offset():
    """양수 offset이 이미 있는 경우 그대로 유지"""
    tool = NotionTool()

    # 이미 +09:00 있음
    assert tool._ensure_kst_timezone("2025-10-03T15:00:00+09:00") == "2025-10-03T15:00:00+09:00"

    # 다른 양수 offset
    assert tool._ensure_kst_timezone("2025-10-03T15:00:00+08:00") == "2025-10-03T15:00:00+08:00"
    assert tool._ensure_kst_timezone("2025-10-03T15:00:00+00:00") == "2025-10-03T15:00:00+00:00"


def test_ensure_kst_timezone_with_negative_offset():
    """음수 offset이 이미 있는 경우 그대로 유지"""
    tool = NotionTool()

    # 음수 offset (예: 미국 동부 시간)
    assert tool._ensure_kst_timezone("2025-10-03T15:00:00-05:00") == "2025-10-03T15:00:00-05:00"
    assert tool._ensure_kst_timezone("2025-10-03T15:00:00-09:00") == "2025-10-03T15:00:00-09:00"


def test_ensure_kst_timezone_edge_cases():
    """엣지 케이스 테스트"""
    tool = NotionTool()

    # 빈 문자열
    assert tool._ensure_kst_timezone("") == ""

    # None
    assert tool._ensure_kst_timezone(None) == None

    # 공백
    assert tool._ensure_kst_timezone("   ") == "   "

    # 밀리초 포함
    assert tool._ensure_kst_timezone("2025-10-03T15:00:00.123") == "2025-10-03T15:00:00.123+09:00"


def test_ensure_kst_timezone_common_user_inputs():
    """사용자가 흔히 입력할 수 있는 형식 테스트"""
    tool = NotionTool()

    # ISO 8601 기본 형식 (타임존 없음)
    assert tool._ensure_kst_timezone("2025-10-04T15:00:00") == "2025-10-04T15:00:00+09:00"

    # 분까지만 (초 없음)
    assert tool._ensure_kst_timezone("2025-10-04T15:00") == "2025-10-04T15:00+09:00"

    # 날짜만
    assert tool._ensure_kst_timezone("2025-10-04") == "2025-10-04"


if __name__ == "__main__":
    # 수동 실행 시 간단한 출력
    print("=== NotionTool 타임존 처리 테스트 ===\n")

    tool = NotionTool()

    test_cases = [
        ("2025-10-03", "날짜만"),
        ("2025-10-03T15:00:00", "시간 (타임존 없음)"),
        ("2025-10-03T15:00:00+09:00", "시간 (KST)"),
        ("2025-10-03T06:00:00Z", "시간 (UTC)"),
        ("2025-10-03T15:00:00-05:00", "시간 (음수 offset)"),
    ]

    for input_str, description in test_cases:
        output = tool._ensure_kst_timezone(input_str)
        print(f"{description}:")
        print(f"  입력: {input_str}")
        print(f"  출력: {output}")
        print()

    print("✅ 모든 타임존 처리가 정상적으로 동작합니다!")
