"""
Tool 정의 및 구현

Why: LLM Agent가 호출할 수 있는 도구들을 정의하여
     일정 관리 기능을 수행한다.

Note: CLAUDE.md 순수 LLM 기반 원칙 준수
      - 자연어 파싱 없음 (LLM이 담당)
      - Tool은 구조화된 데이터(ISO 형식)만 처리
"""
from datetime import date, time, datetime
from typing import Optional, Dict, Any, List

from database import Database
from models import Schedule, VALID_CATEGORIES, ScheduleValidationError


# ==================== Tool 스키마 정의 ====================
# Gemini Function Calling 형식

TOOL_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "add_schedule": {
        "name": "add_schedule",
        "description": "새 일정을 추가합니다. 날짜와 시간은 반드시 ISO 형식으로 전달해야 합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "일정 제목"
                },
                "date": {
                    "type": "string",
                    "description": "날짜 (YYYY-MM-DD 형식). 예: 2025-11-27. '내일', '다음주' 등 자연어가 아닌 ISO 형식으로 변환하여 전달."
                },
                "start_time": {
                    "type": "string",
                    "description": "시작 시간 (HH:MM 24시간제). 예: 14:30. 없으면 null."
                },
                "end_time": {
                    "type": "string",
                    "description": "종료 시간 (HH:MM 24시간제). 예: 15:30. 없으면 null."
                },
                "location": {
                    "type": "string",
                    "description": "장소. 없으면 null."
                },
                "memo": {
                    "type": "string",
                    "description": "메모. 없으면 null."
                },
                "category": {
                    "type": "string",
                    "description": f"대분류 카테고리. 허용값: {VALID_CATEGORIES}. 기본값: 기타",
                    "enum": list(VALID_CATEGORIES)
                }
            },
            "required": ["title", "date"]
        }
    },
    "get_schedules_for_date": {
        "name": "get_schedules_for_date",
        "description": "특정 날짜의 일정 목록을 조회합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "조회할 날짜 (YYYY-MM-DD 형식). 예: 2025-11-27"
                }
            },
            "required": ["date"]
        }
    },
    "complete_schedule": {
        "name": "complete_schedule",
        "description": "일정을 완료 상태로 변경합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "schedule_id": {
                    "type": "integer",
                    "description": "완료할 일정의 ID"
                }
            },
            "required": ["schedule_id"]
        }
    },
    "check_travel_time": {
        "name": "check_travel_time",
        "description": "새 일정 추가 전 이동시간을 확인합니다. 직전 일정과 장소가 다르면 이동시간 경고를 제공합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "확인할 날짜 (YYYY-MM-DD 형식)"
                },
                "time": {
                    "type": "string",
                    "description": "새 일정 시작 시간 (HH:MM 형식)"
                },
                "new_location": {
                    "type": "string",
                    "description": "새 일정 장소"
                }
            },
            "required": ["date", "time", "new_location"]
        }
    },
    "get_all_schedules": {
        "name": "get_all_schedules",
        "description": "모든 일정을 조회합니다. 데스크톱 앱과 동기화할 때 사용합니다. 사용자가 '일정 동기화', '전체 일정 보여줘', '일정 새로고침' 등을 요청하면 이 도구를 사용하세요.",
        "parameters": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "오늘부터 몇 일 후까지의 일정을 조회할지 (기본값: 30)"
                },
                "include_past": {
                    "type": "boolean",
                    "description": "과거 일정도 포함할지 (기본값: false)"
                }
            },
            "required": []
        }
    }
}


# ==================== 헬퍼 함수 ====================

def _validate_iso_date(date_str: str) -> Optional[date]:
    """
    ISO 형식 날짜 검증 (YYYY-MM-DD)

    Why: Tool은 구조화된 데이터만 처리하므로
         자연어가 아닌 ISO 형식만 허용한다.

    Returns:
        date 객체 또는 None (잘못된 형식)
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _validate_time(time_str: str) -> Optional[time]:
    """
    시간 형식 검증 (HH:MM)

    Returns:
        time 객체 또는 None (잘못된 형식)
    """
    if not time_str:
        return None
    try:
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError, TypeError):
        return None


def _estimate_travel_minutes(from_location: str, to_location: str) -> int:
    """
    두 장소 간 이동시간 추정 (MVP용 휴리스틱)

    Why: MVP에서는 간단한 휴리스틱으로 이동시간을 추정한다.
         실제 서비스에서는 지도 API로 대체 예정.

    Returns:
        예상 이동시간 (분)
    """
    # 같은 장소면 이동시간 없음
    if from_location == to_location:
        return 0

    # 둘 다 "역"이 포함되면 지하철 이동으로 가정 (30분)
    if "역" in from_location and "역" in to_location:
        return 30

    # 기본 이동시간 (20분)
    return 20


# ==================== Tool 구현 ====================

def add_schedule(
    db: Database,
    title: str,
    date: str,
    start_time: str = None,
    end_time: str = None,
    location: str = None,
    memo: str = None,
    category: str = "기타",
) -> Dict[str, Any]:
    """
    새 일정을 추가한다.

    Why: LLM이 자연어를 분석하여 구조화된 형식으로 전달하면
         Tool은 검증 후 DB에 저장한다.

    Args:
        db: Database 인스턴스
        title: 일정 제목
        date: 날짜 (YYYY-MM-DD 형식만 허용)
        start_time: 시작 시간 (HH:MM 형식, 선택)
        end_time: 종료 시간 (HH:MM 형식, 선택)
        location: 장소 (선택)
        memo: 메모 (선택)
        category: 대분류 카테고리 (기본: 기타)

    Returns:
        dict: {"success": bool, "id": int, "title": str} 또는 에러
    """
    # ISO 형식 검증 (자연어 거부)
    parsed_date = _validate_iso_date(date)
    if parsed_date is None:
        return {
            "success": False,
            "error": f"날짜는 YYYY-MM-DD 형식이어야 합니다. 입력값: {date}"
        }

    # 시간 검증
    parsed_start_time = _validate_time(start_time)
    parsed_end_time = _validate_time(end_time)

    # Schedule 객체 생성
    try:
        schedule = Schedule(
            title=title,
            scheduled_date=parsed_date,
            start_time=parsed_start_time,
            end_time=parsed_end_time,
            location=location,
            memo=memo,
            major_category=category,
        )
        schedule.validate()
    except ScheduleValidationError as e:
        return {"success": False, "error": str(e)}

    # DB 저장
    schedule_id = db.insert(schedule)

    return {
        "success": True,
        "id": schedule_id,
        "title": title,
        "date": date,
        "start_time": start_time,
        "location": location,
        "category": category,
    }


def get_schedules_for_date(
    db: Database,
    date: str,
) -> Dict[str, Any]:
    """
    특정 날짜의 일정 목록을 조회한다.

    Args:
        db: Database 인스턴스
        date: 조회할 날짜 (YYYY-MM-DD 형식만 허용)

    Returns:
        dict: {"success": bool, "schedules": List[dict]}
    """
    # ISO 형식 검증
    parsed_date = _validate_iso_date(date)
    if parsed_date is None:
        return {
            "success": False,
            "error": f"날짜는 YYYY-MM-DD 형식이어야 합니다. 입력값: {date}"
        }

    # DB 조회
    schedules = db.get_by_date(parsed_date)

    return {
        "success": True,
        "date": date,
        "schedules": [s.to_dict() for s in schedules],
        "count": len(schedules),
    }


def complete_schedule(
    db: Database,
    schedule_id: int,
) -> Dict[str, Any]:
    """
    일정을 완료 상태로 변경한다.

    Args:
        db: Database 인스턴스
        schedule_id: 완료할 일정 ID

    Returns:
        dict: {"success": bool, "status": str}
    """
    # 일정 조회
    schedule = db.get_by_id(schedule_id)
    if schedule is None:
        return {
            "success": False,
            "error": f"ID {schedule_id}에 해당하는 일정을 찾을 수 없습니다."
        }

    # 상태 변경
    schedule.status = "완료"
    db.update(schedule)

    return {
        "success": True,
        "id": schedule_id,
        "title": schedule.title,
        "status": "완료",
    }


def get_all_schedules(
    db: Database,
    days_ahead: int = 30,
    include_past: bool = False,
) -> Dict[str, Any]:
    """
    모든 일정을 조회한다. (데스크톱 앱 동기화용)

    Why: 데스크톱 앱이 백엔드 DB와 동기화할 때
         전체 일정을 한 번에 가져올 수 있게 한다.

    Args:
        db: Database 인스턴스
        days_ahead: 오늘부터 몇 일 후까지 조회 (기본 30일)
        include_past: 과거 일정 포함 여부 (기본 False)

    Returns:
        dict: {"success": bool, "schedules": List[dict], "sync_type": "full"}
    """
    from datetime import timedelta

    today = date.today()
    end_date = today + timedelta(days=days_ahead)

    # 과거 일정 포함 시 30일 전부터
    if include_past:
        start_date = today - timedelta(days=30)
    else:
        start_date = today

    # DB 조회 - 기간 내 모든 일정
    all_schedules = []
    cursor = db._conn.execute("""
        SELECT * FROM schedules
        WHERE scheduled_date >= ? AND scheduled_date <= ?
        ORDER BY scheduled_date ASC, start_time ASC NULLS LAST
    """, (start_date.isoformat(), end_date.isoformat()))

    for row in cursor.fetchall():
        schedule = db._row_to_schedule(row)
        all_schedules.append(schedule)

    # 데스크톱 앱용 형식으로 변환 (snake_case → 클라이언트가 기대하는 형식)
    schedules_for_client = []
    for s in all_schedules:
        schedules_for_client.append({
            "id": s.id,
            "title": s.title,
            "date": s.scheduled_date.isoformat(),
            "start_time": s.start_time.strftime("%H:%M") if s.start_time else None,
            "end_time": s.end_time.strftime("%H:%M") if s.end_time else None,
            "location": s.location,
            "memo": s.memo,
            "category": s.major_category,
            "status": s.status,
        })

    return {
        "success": True,
        "sync_type": "full",
        "schedules": schedules_for_client,
        "count": len(schedules_for_client),
        "sync_timestamp": datetime.now().isoformat(),
    }


def check_travel_time(
    db: Database,
    date: str,
    time: str,
    new_location: str,
) -> Dict[str, Any]:
    """
    새 일정 추가 전 이동시간을 확인한다.

    Why: 직전 일정과 장소가 다르면 이동시간을 추정하여
         사용자에게 경고를 제공한다.

    Args:
        db: Database 인스턴스
        date: 확인할 날짜 (YYYY-MM-DD 형식)
        time: 새 일정 시작 시간 (HH:MM 형식)
        new_location: 새 일정 장소

    Returns:
        dict: 이동시간 정보 및 경고
    """
    # ISO 형식 검증
    parsed_date = _validate_iso_date(date)
    if parsed_date is None:
        return {
            "success": False,
            "error": f"날짜는 YYYY-MM-DD 형식이어야 합니다. 입력값: {date}"
        }

    parsed_time = _validate_time(time)
    if parsed_time is None:
        return {
            "success": False,
            "error": f"시간은 HH:MM 형식이어야 합니다. 입력값: {time}"
        }

    # 해당 날짜의 일정 조회
    schedules = db.get_by_date(parsed_date)

    # 새 일정 시작 시간 이전에 끝나는 일정 중 가장 늦은 것 찾기
    previous_schedule = None
    for s in schedules:
        if s.end_time and s.end_time <= parsed_time:
            if previous_schedule is None or s.end_time > previous_schedule.end_time:
                previous_schedule = s

    # 이전 일정이 없는 경우
    if previous_schedule is None:
        return {
            "success": True,
            "previous_schedule": None,
            "message": "직전 일정이 없습니다. 이동시간 확인이 필요하지 않습니다.",
        }

    # 이동시간 추정
    from_location = previous_schedule.location or "알 수 없음"
    estimated_minutes = _estimate_travel_minutes(from_location, new_location)

    # 여유 시간 계산
    end_datetime = datetime.combine(parsed_date, previous_schedule.end_time)
    new_datetime = datetime.combine(parsed_date, parsed_time)
    available_minutes = int((new_datetime - end_datetime).total_seconds() / 60)

    # 결과 생성
    result = {
        "success": True,
        "previous_schedule": {
            "id": previous_schedule.id,
            "title": previous_schedule.title,
            "end_time": previous_schedule.end_time.strftime("%H:%M"),
            "location": from_location,
        },
        "new_time": time,
        "new_location": new_location,
        "estimated_travel_minutes": estimated_minutes,
        "available_minutes": available_minutes,
    }

    # 경고 또는 메시지
    if estimated_minutes > available_minutes:
        result["warning"] = (
            f"⚠️ 이동시간 부족! "
            f"{from_location}에서 {new_location}까지 약 {estimated_minutes}분 예상되나, "
            f"여유시간은 {available_minutes}분입니다."
        )
    else:
        result["message"] = (
            f"✅ 이동 가능. "
            f"{from_location}에서 {new_location}까지 약 {estimated_minutes}분 예상, "
            f"여유시간 {available_minutes}분."
        )

    return result


# ==================== Tool 실행기 ====================

def execute_tool(
    db: Database,
    tool_name: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Tool 이름과 파라미터로 해당 Tool을 실행한다.

    Why: LLM이 Tool 호출을 결정하면 이 함수를 통해
         실제 Tool 함수를 실행한다.

    Args:
        db: Database 인스턴스
        tool_name: 실행할 Tool 이름
        params: Tool 파라미터 딕셔너리

    Returns:
        dict: Tool 실행 결과
    """
    # Tool 매핑
    tool_map = {
        "add_schedule": add_schedule,
        "get_schedules_for_date": get_schedules_for_date,
        "complete_schedule": complete_schedule,
        "check_travel_time": check_travel_time,
        "get_all_schedules": get_all_schedules,
    }

    # Tool 존재 확인
    if tool_name not in tool_map:
        return {
            "success": False,
            "error": f"알 수 없는 Tool: {tool_name}. 사용 가능: {list(tool_map.keys())}"
        }

    # Tool 실행
    tool_func = tool_map[tool_name]
    return tool_func(db=db, **params)
