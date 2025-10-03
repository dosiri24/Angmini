"""
tests/test_timezone_simple.py
NotionTool 타임존 처리 간단 테스트 (의존성 없음)
"""


def ensure_kst_timezone(raw: str) -> str:
    """NotionTool._ensure_kst_timezone 로직 복사 (테스트용)"""
    text = (raw or "").strip()
    if not text:
        return raw
    if "T" not in text:
        # Date-only values should remain date-only
        return text
    # Time part exists; check for timezone designator
    time_part = text.split("T", 1)[1]
    if time_part.endswith("Z") or time_part.endswith("z"):
        # UTC로 명시된 경우 그대로 유지 (Notion이 UTC로 처리)
        return text
    if "+" in time_part:
        # 이미 양수 offset 있음 (예: +09:00, +00:00)
        return text
    # Detect negative offset like -09:00 in time part
    # The time format is HH:MM(:SS[.fff]) optionally followed by offset
    # A '-' in time_part (beyond the hour/minute section) indicates an offset
    if "-" in time_part[2:]:
        # 음수 offset 있음 (예: -05:00)
        return text
    # No timezone info → append KST offset (+09:00)
    # 이것이 기본 동작: 타임존 정보가 없으면 한국 시간(GMT+9)으로 간주
    return f"{text}+09:00"


if __name__ == "__main__":
    print("=== NotionTool 타임존 처리 간단 테스트 ===\n")

    test_cases = [
        # (입력, 예상 출력, 설명)
        ("2025-10-03", "2025-10-03", "날짜만"),
        ("2025-10-03T15:00:00", "2025-10-03T15:00:00+09:00", "시간 (타임존 없음)"),
        ("2025-10-03T15:00:00+09:00", "2025-10-03T15:00:00+09:00", "시간 (KST)"),
        ("2025-10-03T06:00:00Z", "2025-10-03T06:00:00Z", "시간 (UTC)"),
        ("2025-10-03T15:00:00-05:00", "2025-10-03T15:00:00-05:00", "시간 (음수 offset)"),
        ("2025-10-03T15:00", "2025-10-03T15:00+09:00", "시간 (분까지만)"),
        ("", "", "빈 문자열"),
    ]

    all_passed = True

    for input_str, expected, description in test_cases:
        output = ensure_kst_timezone(input_str)
        passed = output == expected

        status = "✅" if passed else "❌"
        print(f"{status} {description}:")
        print(f"   입력:    {repr(input_str)}")
        print(f"   예상:    {repr(expected)}")
        print(f"   실제:    {repr(output)}")

        if not passed:
            all_passed = False
            print(f"   ⚠️  불일치!")

        print()

    if all_passed:
        print("✅ 모든 타임존 처리 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패!")
