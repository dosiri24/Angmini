"""
Tools 테스트

Why: TDD로 각 Tool의 동작을 검증하여
     LLM Agent가 올바르게 Tool을 호출할 수 있음을 보장한다.

Note: CLAUDE.md 순수 LLM 기반 원칙에 따라
      - 자연어 파싱은 LLM이 담당
      - Tool은 구조화된 데이터(ISO 형식)만 처리
"""
import pytest
from datetime import date, time

from tools import (
    TOOL_DEFINITIONS,
    add_schedule,
    get_schedules_for_date,
    complete_schedule,
    check_travel_time,
    execute_tool,
)
from database import Database
from models import Schedule


# ==================== Fixtures ====================

@pytest.fixture
def db(tmp_path):
    """테스트용 임시 DB"""
    db_path = str(tmp_path / "test.db")
    database = Database(db_path)
    database.init_schema()
    yield database
    database.close()


@pytest.fixture
def sample_schedule(db) -> int:
    """테스트용 샘플 일정 (ID 반환)"""
    schedule = Schedule(
        title="팀 미팅",
        scheduled_date=date.today(),
        start_time=time(14, 0),
        end_time=time(15, 0),
        location="회의실 A",
        major_category="업무",
    )
    return db.insert(schedule)


# ==================== 3.1 Tool 스키마 정의 테스트 ====================

class TestToolDefinitions:
    """Tool 스키마 정의 테스트"""

    def test_tool_definitions_is_dict(self):
        """TOOL_DEFINITIONS가 딕셔너리 형태인지 확인"""
        assert isinstance(TOOL_DEFINITIONS, dict)

    def test_required_tools_exist(self):
        """필수 Tool들이 정의되어 있는지 확인"""
        required_tools = [
            "add_schedule",
            "get_schedules_for_date",
            "complete_schedule",
            "check_travel_time",
        ]
        for tool_name in required_tools:
            assert tool_name in TOOL_DEFINITIONS, f"{tool_name} not found"

    def test_tool_has_required_fields(self):
        """각 Tool이 필수 필드를 가지는지 확인 (Gemini 형식)"""
        for tool_name, tool_def in TOOL_DEFINITIONS.items():
            assert "name" in tool_def, f"{tool_name}: missing 'name'"
            assert "description" in tool_def, f"{tool_name}: missing 'description'"
            assert "parameters" in tool_def, f"{tool_name}: missing 'parameters'"

    def test_tool_parameters_specify_iso_format(self):
        """Tool 파라미터가 ISO 형식을 명시하는지 확인 (순수 LLM 원칙)"""
        # add_schedule의 date 파라미터는 ISO 형식을 요구해야 함
        add_schedule_def = TOOL_DEFINITIONS["add_schedule"]
        date_param = add_schedule_def["parameters"]["properties"]["date"]
        assert "YYYY-MM-DD" in date_param.get("description", ""), \
            "date 파라미터는 ISO 형식(YYYY-MM-DD)을 명시해야 합니다"


# ==================== 3.2 add_schedule Tool 테스트 ====================

class TestAddSchedule:
    """
    add_schedule Tool 테스트

    Note: 모든 날짜/시간은 ISO 형식으로 전달됨 (LLM이 변환 담당)
    """

    def test_add_schedule_success(self, db):
        """정상 입력 시 일정 추가 (ISO 형식)"""
        result = add_schedule(
            db=db,
            title="점심 약속",
            date="2025-11-27",  # ISO 형식
            start_time="12:00",  # HH:MM 형식
            location="강남역",
            category="약속",
        )

        assert result["success"] is True
        assert "id" in result
        assert result["title"] == "점심 약속"

        # DB에 실제로 저장되었는지 확인
        saved = db.get_by_id(result["id"])
        assert saved is not None
        assert saved.title == "점심 약속"

    def test_add_schedule_minimal(self, db):
        """최소 필수 정보만으로 일정 추가"""
        result = add_schedule(
            db=db,
            title="할 일",
            date="2025-11-27",  # ISO 형식 필수
        )

        assert result["success"] is True
        assert result["title"] == "할 일"

        saved = db.get_by_id(result["id"])
        assert saved.major_category == "기타"  # 기본값
        assert saved.start_time is None

    def test_add_schedule_with_end_time(self, db):
        """시작/종료 시간 모두 있는 일정"""
        result = add_schedule(
            db=db,
            title="회의",
            date="2025-11-27",
            start_time="14:00",
            end_time="15:30",
            category="업무",
        )

        assert result["success"] is True
        saved = db.get_by_id(result["id"])
        assert saved.start_time == time(14, 0)
        assert saved.end_time == time(15, 30)

    def test_add_schedule_invalid_category(self, db):
        """잘못된 카테고리 입력 시 에러"""
        result = add_schedule(
            db=db,
            title="테스트",
            date="2025-11-27",
            category="잘못된카테고리",
        )

        assert result["success"] is False
        assert "error" in result

    def test_add_schedule_invalid_date_format(self, db):
        """잘못된 날짜 형식 시 에러 (ISO 형식만 허용)"""
        result = add_schedule(
            db=db,
            title="테스트",
            date="내일",  # ❌ 자연어 - Tool에서 거부해야 함
        )

        assert result["success"] is False
        assert "error" in result


# ==================== 3.3 get_schedules_for_date Tool 테스트 ====================

class TestGetSchedulesForDate:
    """
    get_schedules_for_date Tool 테스트

    Note: 날짜는 ISO 형식(YYYY-MM-DD)으로만 전달
    """

    def test_get_schedules_returns_list(self, db, sample_schedule):
        """특정 날짜 조회 시 리스트 반환 (ISO 형식)"""
        today_iso = date.today().isoformat()  # YYYY-MM-DD
        result = get_schedules_for_date(db=db, date=today_iso)

        assert result["success"] is True
        assert isinstance(result["schedules"], list)
        assert len(result["schedules"]) >= 1

    def test_get_schedules_empty_date(self, db):
        """일정 없는 날짜는 빈 리스트"""
        result = get_schedules_for_date(db=db, date="2099-12-31")

        assert result["success"] is True
        assert result["schedules"] == []

    def test_get_schedules_invalid_date_format(self, db):
        """잘못된 날짜 형식 시 에러"""
        result = get_schedules_for_date(db=db, date="오늘")  # ❌ 자연어

        assert result["success"] is False
        assert "error" in result


# ==================== 3.4 complete_schedule Tool 테스트 ====================

class TestCompleteSchedule:
    """complete_schedule Tool 테스트"""

    def test_complete_schedule_success(self, db, sample_schedule):
        """완료 처리 후 status 변경"""
        result = complete_schedule(db=db, schedule_id=sample_schedule)

        assert result["success"] is True
        assert result["status"] == "완료"

        # DB에서 확인
        updated = db.get_by_id(sample_schedule)
        assert updated.status == "완료"

    def test_complete_schedule_not_found(self, db):
        """없는 ID 에러 처리"""
        result = complete_schedule(db=db, schedule_id=99999)

        assert result["success"] is False
        assert "error" in result


# ==================== 3.5 check_travel_time Tool 테스트 ====================

class TestCheckTravelTime:
    """
    check_travel_time Tool 테스트

    Note: 날짜/시간은 ISO 형식으로만 전달
    """

    def test_check_travel_time_with_previous(self, db):
        """이전 일정이 있을 때 이동시간 추정"""
        # 기존 일정 추가 (14:00~15:00)
        existing = Schedule(
            title="기존 미팅",
            scheduled_date=date.today(),
            start_time=time(14, 0),
            end_time=time(15, 0),
            location="강남역",
            major_category="업무",
        )
        db.insert(existing)

        # 15:30에 다른 장소로 가려고 함 (ISO 형식으로 전달)
        today_iso = date.today().isoformat()
        result = check_travel_time(
            db=db,
            date=today_iso,  # ISO 형식
            time="15:30",     # HH:MM 형식
            new_location="홍대입구역",
        )

        assert result["success"] is True
        assert "previous_schedule" in result
        assert "estimated_travel_minutes" in result
        assert "warning" in result or "message" in result

    def test_check_travel_time_no_previous(self, db):
        """이전 일정 없을 때"""
        result = check_travel_time(
            db=db,
            date="2099-12-31",  # ISO 형식
            time="10:00",       # HH:MM 형식
            new_location="어딘가",
        )

        assert result["success"] is True
        assert result["previous_schedule"] is None

    def test_check_travel_time_invalid_date_format(self, db):
        """잘못된 날짜 형식 시 에러"""
        result = check_travel_time(
            db=db,
            date="내일",  # ❌ 자연어
            time="10:00",
            new_location="어딘가",
        )

        assert result["success"] is False
        assert "error" in result


# ==================== 3.6 Tool 실행기 테스트 ====================

class TestExecuteTool:
    """execute_tool 함수 테스트"""

    def test_execute_tool_add_schedule(self, db):
        """tool_name으로 add_schedule 호출"""
        result = execute_tool(
            db=db,
            tool_name="add_schedule",
            params={
                "title": "테스트 일정",
                "date": "2025-11-27",  # ISO 형식
            }
        )

        assert result["success"] is True
        assert "id" in result

    def test_execute_tool_unknown(self, db):
        """알 수 없는 Tool 이름"""
        result = execute_tool(
            db=db,
            tool_name="unknown_tool",
            params={}
        )

        assert result["success"] is False
        assert "error" in result
