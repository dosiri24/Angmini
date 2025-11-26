"""
Schedule 모델 테스트
- TDD Red 단계: 구현 전 테스트 먼저 작성
"""
import pytest
from datetime import date, time, datetime


class TestScheduleCreation:
    """1.1 Schedule 객체 생성 테스트"""

    def test_create_schedule_with_required_fields(self):
        """필수 필드만으로 Schedule 생성 가능"""
        from models import Schedule

        schedule = Schedule(
            title="팀 미팅",
            scheduled_date=date(2025, 11, 26),
            major_category="업무"
        )

        assert schedule.title == "팀 미팅"
        assert schedule.scheduled_date == date(2025, 11, 26)
        assert schedule.major_category == "업무"
        assert schedule.status == "예정"  # 기본값

    def test_create_schedule_with_all_fields(self):
        """모든 필드를 지정하여 Schedule 생성"""
        from models import Schedule

        schedule = Schedule(
            id=1,
            title="치과 예약",
            scheduled_date=date(2025, 11, 27),
            start_time=time(14, 30),
            end_time=time(15, 30),
            location="강남역 치과",
            major_category="개인",
            status="예정",
            created_at=datetime(2025, 11, 26, 10, 0, 0)
        )

        assert schedule.id == 1
        assert schedule.title == "치과 예약"
        assert schedule.start_time == time(14, 30)
        assert schedule.end_time == time(15, 30)
        assert schedule.location == "강남역 치과"

    def test_schedule_optional_fields_default_to_none(self):
        """선택 필드는 None이 기본값"""
        from models import Schedule

        schedule = Schedule(
            title="과제 제출",
            scheduled_date=date(2025, 11, 28),
            major_category="학업"
        )

        assert schedule.id is None
        assert schedule.start_time is None
        assert schedule.end_time is None
        assert schedule.location is None

    def test_schedule_created_at_auto_generated(self):
        """created_at은 자동 생성"""
        from models import Schedule

        before = datetime.now()
        schedule = Schedule(
            title="테스트",
            scheduled_date=date(2025, 11, 26),
            major_category="기타"
        )
        after = datetime.now()

        assert before <= schedule.created_at <= after


class TestScheduleValidation:
    """1.2 Schedule 유효성 검증 테스트"""

    def test_empty_title_raises_error(self):
        """빈 title은 거부"""
        from models import Schedule, ScheduleValidationError

        with pytest.raises(ScheduleValidationError) as exc_info:
            Schedule(
                title="",  # 빈 문자열
                scheduled_date=date(2025, 11, 26),
                major_category="업무"
            ).validate()

        assert "title" in str(exc_info.value).lower()

    def test_whitespace_only_title_raises_error(self):
        """공백만 있는 title도 거부"""
        from models import Schedule, ScheduleValidationError

        with pytest.raises(ScheduleValidationError):
            Schedule(
                title="   ",
                scheduled_date=date(2025, 11, 26),
                major_category="업무"
            ).validate()

    def test_invalid_category_raises_error(self):
        """허용되지 않은 category는 거부"""
        from models import Schedule, ScheduleValidationError

        with pytest.raises(ScheduleValidationError) as exc_info:
            Schedule(
                title="테스트",
                scheduled_date=date(2025, 11, 26),
                major_category="잘못된카테고리"
            ).validate()

        assert "category" in str(exc_info.value).lower()

    def test_valid_categories_accepted(self):
        """허용된 category들은 통과"""
        from models import Schedule, VALID_CATEGORIES

        for category in VALID_CATEGORIES:
            schedule = Schedule(
                title="테스트",
                scheduled_date=date(2025, 11, 26),
                major_category=category
            )
            # validate()가 예외 없이 통과해야 함
            schedule.validate()

    def test_invalid_status_raises_error(self):
        """허용되지 않은 status는 거부"""
        from models import Schedule, ScheduleValidationError

        with pytest.raises(ScheduleValidationError) as exc_info:
            Schedule(
                title="테스트",
                scheduled_date=date(2025, 11, 26),
                major_category="업무",
                status="잘못된상태"
            ).validate()

        assert "status" in str(exc_info.value).lower()

    def test_end_time_before_start_time_raises_error(self):
        """종료 시간이 시작 시간보다 빠르면 거부"""
        from models import Schedule, ScheduleValidationError

        with pytest.raises(ScheduleValidationError):
            Schedule(
                title="미팅",
                scheduled_date=date(2025, 11, 26),
                start_time=time(15, 0),
                end_time=time(14, 0),  # 시작보다 빠름
                major_category="업무"
            ).validate()


class TestScheduleSerialization:
    """1.3 Schedule 직렬화 테스트"""

    def test_to_dict_converts_all_fields(self):
        """to_dict()가 모든 필드를 dict로 변환"""
        from models import Schedule

        schedule = Schedule(
            id=1,
            title="미팅",
            scheduled_date=date(2025, 11, 26),
            start_time=time(10, 0),
            end_time=time(11, 0),
            location="회의실",
            major_category="업무",
            status="예정",
            created_at=datetime(2025, 11, 26, 9, 0, 0)
        )

        result = schedule.to_dict()

        assert result["id"] == 1
        assert result["title"] == "미팅"
        assert result["scheduled_date"] == "2025-11-26"
        assert result["start_time"] == "10:00"
        assert result["end_time"] == "11:00"
        assert result["location"] == "회의실"
        assert result["major_category"] == "업무"
        assert result["status"] == "예정"
        assert "created_at" in result

    def test_to_dict_handles_none_values(self):
        """to_dict()가 None 값을 올바르게 처리"""
        from models import Schedule

        schedule = Schedule(
            title="과제",
            scheduled_date=date(2025, 11, 26),
            major_category="학업"
        )

        result = schedule.to_dict()

        assert result["id"] is None
        assert result["start_time"] is None
        assert result["end_time"] is None
        assert result["location"] is None

    def test_from_dict_creates_schedule(self):
        """from_dict()가 dict에서 Schedule 객체 생성"""
        from models import Schedule

        data = {
            "id": 1,
            "title": "미팅",
            "scheduled_date": "2025-11-26",
            "start_time": "10:00",
            "end_time": "11:00",
            "location": "회의실",
            "major_category": "업무",
            "status": "예정",
            "created_at": "2025-11-26T09:00:00"
        }

        schedule = Schedule.from_dict(data)

        assert schedule.id == 1
        assert schedule.title == "미팅"
        assert schedule.scheduled_date == date(2025, 11, 26)
        assert schedule.start_time == time(10, 0)
        assert schedule.end_time == time(11, 0)
        assert schedule.location == "회의실"

    def test_from_dict_handles_none_values(self):
        """from_dict()가 None 값을 올바르게 처리"""
        from models import Schedule

        data = {
            "id": None,
            "title": "과제",
            "scheduled_date": "2025-11-26",
            "start_time": None,
            "end_time": None,
            "location": None,
            "major_category": "학업",
            "status": "예정",
            "created_at": "2025-11-26T09:00:00"
        }

        schedule = Schedule.from_dict(data)

        assert schedule.id is None
        assert schedule.start_time is None
        assert schedule.end_time is None
        assert schedule.location is None

    def test_roundtrip_serialization(self):
        """to_dict → from_dict 왕복 변환 검증"""
        from models import Schedule

        original = Schedule(
            id=1,
            title="원본 일정",
            scheduled_date=date(2025, 11, 26),
            start_time=time(14, 30),
            end_time=time(16, 0),
            location="카페",
            major_category="약속",
            status="예정"
        )

        data = original.to_dict()
        restored = Schedule.from_dict(data)

        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.scheduled_date == original.scheduled_date
        assert restored.start_time == original.start_time
        assert restored.end_time == original.end_time
        assert restored.location == original.location
        assert restored.major_category == original.major_category
        assert restored.status == original.status
