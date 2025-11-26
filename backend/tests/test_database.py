"""
Database 테스트
- TDD Red 단계: 구현 전 테스트 먼저 작성
"""
import pytest
import tempfile
import os
from datetime import date, time, datetime
from pathlib import Path


@pytest.fixture
def temp_db():
    """임시 DB 파일을 생성하고 테스트 후 정리"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def db(temp_db):
    """Database 인스턴스를 생성하고 스키마 초기화"""
    from database import Database
    database = Database(temp_db)
    database.init_schema()
    yield database
    database.close()


@pytest.fixture
def sample_schedule():
    """테스트용 샘플 Schedule"""
    from models import Schedule
    return Schedule(
        title="팀 미팅",
        scheduled_date=date(2025, 11, 26),
        start_time=time(14, 0),
        end_time=time(15, 0),
        location="회의실 A",
        major_category="업무",
        status="예정"
    )


class TestDatabaseConnection:
    """2.1 SQLite 연결 및 스키마 테스트"""

    def test_database_file_created(self, temp_db):
        """DB 파일이 생성됨"""
        from database import Database

        db = Database(temp_db)
        db.init_schema()

        assert os.path.exists(temp_db)
        db.close()

    def test_init_schema_creates_table(self, db):
        """init_schema()가 schedules 테이블 생성"""
        # 테이블 존재 확인
        cursor = db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schedules'"
        )
        result = cursor.fetchone()

        assert result is not None
        assert result[0] == "schedules"

    def test_database_context_manager(self, temp_db):
        """with 문으로 DB 사용 가능"""
        from database import Database

        with Database(temp_db) as db:
            db.init_schema()
            assert db._conn is not None

        # with 블록 종료 후 연결 닫힘 확인은 구현에 따라 다름


class TestDatabaseCreate:
    """2.2 CRUD - Create 테스트"""

    def test_insert_returns_id(self, db, sample_schedule):
        """insert() 후 ID 반환"""
        schedule_id = db.insert(sample_schedule)

        assert schedule_id is not None
        assert isinstance(schedule_id, int)
        assert schedule_id > 0

    def test_insert_multiple_returns_different_ids(self, db):
        """여러 번 insert 시 서로 다른 ID 반환"""
        from models import Schedule

        ids = []
        for i in range(3):
            schedule = Schedule(
                title=f"일정 {i}",
                scheduled_date=date(2025, 11, 26),
                major_category="업무"
            )
            ids.append(db.insert(schedule))

        assert len(set(ids)) == 3  # 모두 다른 ID


class TestDatabaseRead:
    """2.3 CRUD - Read 테스트"""

    def test_get_by_id_returns_schedule(self, db, sample_schedule):
        """get_by_id()가 저장된 Schedule 반환"""
        schedule_id = db.insert(sample_schedule)

        result = db.get_by_id(schedule_id)

        assert result is not None
        assert result.id == schedule_id
        assert result.title == sample_schedule.title
        assert result.scheduled_date == sample_schedule.scheduled_date
        assert result.location == sample_schedule.location

    def test_get_by_id_returns_none_for_nonexistent(self, db):
        """존재하지 않는 ID는 None 반환"""
        result = db.get_by_id(99999)

        assert result is None

    def test_get_by_date_returns_schedules(self, db):
        """get_by_date()가 해당 날짜 일정 목록 반환"""
        from models import Schedule

        target_date = date(2025, 11, 26)

        # 같은 날짜 2개
        db.insert(Schedule(title="일정1", scheduled_date=target_date, major_category="업무"))
        db.insert(Schedule(title="일정2", scheduled_date=target_date, major_category="개인"))

        # 다른 날짜 1개
        db.insert(Schedule(title="일정3", scheduled_date=date(2025, 11, 27), major_category="업무"))

        result = db.get_by_date(target_date)

        assert len(result) == 2
        assert all(s.scheduled_date == target_date for s in result)

    def test_get_by_date_returns_empty_for_no_schedules(self, db):
        """일정 없는 날짜는 빈 리스트 반환"""
        result = db.get_by_date(date(2099, 12, 31))

        assert result == []

    def test_get_by_date_ordered_by_time(self, db):
        """get_by_date() 결과는 시작 시간 순 정렬"""
        from models import Schedule

        target_date = date(2025, 11, 26)

        # 순서 섞어서 추가
        db.insert(Schedule(
            title="오후 미팅",
            scheduled_date=target_date,
            start_time=time(15, 0),
            major_category="업무"
        ))
        db.insert(Schedule(
            title="아침 회의",
            scheduled_date=target_date,
            start_time=time(9, 0),
            major_category="업무"
        ))
        db.insert(Schedule(
            title="점심 약속",
            scheduled_date=target_date,
            start_time=time(12, 0),
            major_category="약속"
        ))

        result = db.get_by_date(target_date)

        assert result[0].title == "아침 회의"
        assert result[1].title == "점심 약속"
        assert result[2].title == "오후 미팅"


class TestDatabaseUpdate:
    """2.4 CRUD - Update 테스트"""

    def test_update_returns_true(self, db, sample_schedule):
        """update() 성공 시 True 반환"""
        schedule_id = db.insert(sample_schedule)
        sample_schedule.id = schedule_id
        sample_schedule.title = "수정된 제목"

        result = db.update(sample_schedule)

        assert result is True

    def test_update_changes_data(self, db, sample_schedule):
        """update() 후 데이터 변경 확인"""
        schedule_id = db.insert(sample_schedule)
        sample_schedule.id = schedule_id
        sample_schedule.title = "수정된 제목"
        sample_schedule.location = "새로운 장소"

        db.update(sample_schedule)
        result = db.get_by_id(schedule_id)

        assert result.title == "수정된 제목"
        assert result.location == "새로운 장소"

    def test_update_nonexistent_returns_false(self, db, sample_schedule):
        """존재하지 않는 ID update 시 False 반환"""
        sample_schedule.id = 99999

        result = db.update(sample_schedule)

        assert result is False


class TestDatabaseDelete:
    """2.5 CRUD - Delete 테스트"""

    def test_delete_returns_true(self, db, sample_schedule):
        """delete() 성공 시 True 반환"""
        schedule_id = db.insert(sample_schedule)

        result = db.delete(schedule_id)

        assert result is True

    def test_delete_removes_schedule(self, db, sample_schedule):
        """delete() 후 조회 시 None"""
        schedule_id = db.insert(sample_schedule)
        db.delete(schedule_id)

        result = db.get_by_id(schedule_id)

        assert result is None

    def test_delete_nonexistent_returns_false(self, db):
        """존재하지 않는 ID delete 시 False 반환"""
        result = db.delete(99999)

        assert result is False


class TestDatabaseAdditionalQueries:
    """2.6 추가 쿼리 테스트"""

    def test_get_upcoming_returns_future_schedules(self, db):
        """get_upcoming()이 n일 이내 일정 반환"""
        from models import Schedule
        from datetime import timedelta

        today = date.today()

        # 3일 후 (포함됨)
        db.insert(Schedule(
            title="3일 후",
            scheduled_date=today + timedelta(days=3),
            major_category="업무"
        ))
        # 7일 후 (포함됨 - 경계)
        db.insert(Schedule(
            title="7일 후",
            scheduled_date=today + timedelta(days=7),
            major_category="업무"
        ))
        # 10일 후 (제외됨)
        db.insert(Schedule(
            title="10일 후",
            scheduled_date=today + timedelta(days=10),
            major_category="업무"
        ))

        result = db.get_upcoming(days=7)

        assert len(result) == 2
        titles = [s.title for s in result]
        assert "3일 후" in titles
        assert "7일 후" in titles
        assert "10일 후" not in titles

    def test_get_upcoming_excludes_past(self, db):
        """get_upcoming()은 과거 일정 제외"""
        from models import Schedule
        from datetime import timedelta

        today = date.today()

        # 어제 (제외)
        db.insert(Schedule(
            title="어제",
            scheduled_date=today - timedelta(days=1),
            major_category="업무"
        ))
        # 내일 (포함)
        db.insert(Schedule(
            title="내일",
            scheduled_date=today + timedelta(days=1),
            major_category="업무"
        ))

        result = db.get_upcoming(days=7)

        assert len(result) == 1
        assert result[0].title == "내일"

    def test_search_finds_by_title(self, db):
        """search()가 제목으로 검색"""
        from models import Schedule

        db.insert(Schedule(title="팀 미팅 준비", scheduled_date=date(2025, 11, 26), major_category="업무"))
        db.insert(Schedule(title="개인 공부", scheduled_date=date(2025, 11, 26), major_category="개인"))
        db.insert(Schedule(title="팀 회식", scheduled_date=date(2025, 11, 27), major_category="약속"))

        result = db.search("팀")

        assert len(result) == 2
        titles = [s.title for s in result]
        assert "팀 미팅 준비" in titles
        assert "팀 회식" in titles

    def test_search_finds_by_location(self, db):
        """search()가 장소로도 검색"""
        from models import Schedule

        db.insert(Schedule(
            title="미팅",
            scheduled_date=date(2025, 11, 26),
            location="강남역 카페",
            major_category="약속"
        ))
        db.insert(Schedule(
            title="회의",
            scheduled_date=date(2025, 11, 26),
            location="회사 회의실",
            major_category="업무"
        ))

        result = db.search("강남")

        assert len(result) == 1
        assert result[0].title == "미팅"

    def test_search_returns_empty_for_no_match(self, db):
        """검색 결과 없으면 빈 리스트"""
        from models import Schedule

        db.insert(Schedule(title="테스트", scheduled_date=date(2025, 11, 26), major_category="업무"))

        result = db.search("없는키워드")

        assert result == []

    def test_search_case_insensitive(self, db):
        """대소문자 구분 없이 검색 (한글은 해당 없음)"""
        from models import Schedule

        db.insert(Schedule(
            title="Team Meeting",
            scheduled_date=date(2025, 11, 26),
            major_category="업무"
        ))

        result = db.search("team")

        assert len(result) == 1
