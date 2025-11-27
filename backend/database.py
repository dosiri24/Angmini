"""
Database 모듈 - SQLite 기반 일정 저장소

Why: 일정 데이터를 영구 저장하고 효율적으로 조회하기 위해
     SQLite를 사용하여 경량 로컬 DB를 구현한다.
"""
import sqlite3
from datetime import date, time, datetime, timedelta
from typing import Optional, List
from pathlib import Path

from models import Schedule


class Database:
    """
    SQLite 기반 일정 저장소

    Why: 파일 기반 DB로 별도 서버 없이 데이터 영구 저장 가능
    """

    def __init__(self, db_path: str):
        """
        Database 초기화

        Args:
            db_path: SQLite DB 파일 경로
        """
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self) -> None:
        """DB 연결 생성"""
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row  # dict처럼 접근 가능

    def close(self) -> None:
        """DB 연결 종료"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "Database":
        """Context manager 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager 종료"""
        self.close()

    def init_schema(self) -> None:
        """
        스키마 초기화 - schedules 테이블 생성

        Why: 애플리케이션 시작 시 테이블이 없으면 생성하여
             항상 일관된 스키마를 보장한다.
        """
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                scheduled_date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                location TEXT,
                memo TEXT,
                major_category TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '예정',
                created_at TEXT NOT NULL
            )
        """)
        self._conn.commit()

        # 기존 테이블에 memo 컬럼이 없으면 추가 (마이그레이션)
        self._migrate_add_memo_column()

    # ==================== CREATE ====================

    def insert(self, schedule: Schedule) -> int:
        """
        일정 추가

        Why: 새 일정을 DB에 저장하고 자동 생성된 ID를 반환한다.

        Args:
            schedule: 저장할 Schedule 객체

        Returns:
            int: 생성된 레코드의 ID
        """
        cursor = self._conn.execute("""
            INSERT INTO schedules (
                title, scheduled_date, start_time, end_time,
                location, memo, major_category, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            schedule.title,
            schedule.scheduled_date.isoformat(),
            schedule.start_time.strftime("%H:%M") if schedule.start_time else None,
            schedule.end_time.strftime("%H:%M") if schedule.end_time else None,
            schedule.location,
            schedule.memo,
            schedule.major_category,
            schedule.status,
            schedule.created_at.isoformat(),
        ))
        self._conn.commit()
        return cursor.lastrowid

    # ==================== READ ====================

    def get_by_id(self, schedule_id: int) -> Optional[Schedule]:
        """
        ID로 일정 조회

        Args:
            schedule_id: 조회할 일정 ID

        Returns:
            Schedule 또는 None (없는 경우)
        """
        cursor = self._conn.execute(
            "SELECT * FROM schedules WHERE id = ?",
            (schedule_id,)
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_schedule(row)

    def get_by_date(self, target_date: date) -> List[Schedule]:
        """
        특정 날짜의 일정 목록 조회

        Why: 하루 일정을 한눈에 보기 위해 날짜별 조회 필요

        Args:
            target_date: 조회할 날짜

        Returns:
            해당 날짜의 일정 목록 (시작 시간 순 정렬)
        """
        cursor = self._conn.execute("""
            SELECT * FROM schedules
            WHERE scheduled_date = ?
            ORDER BY start_time ASC NULLS LAST
        """, (target_date.isoformat(),))

        return [self._row_to_schedule(row) for row in cursor.fetchall()]

    # ==================== UPDATE ====================

    def update(self, schedule: Schedule) -> bool:
        """
        일정 수정

        Args:
            schedule: 수정할 Schedule 객체 (id 필수)

        Returns:
            bool: 수정 성공 여부
        """
        if schedule.id is None:
            return False

        cursor = self._conn.execute("""
            UPDATE schedules SET
                title = ?,
                scheduled_date = ?,
                start_time = ?,
                end_time = ?,
                location = ?,
                memo = ?,
                major_category = ?,
                status = ?
            WHERE id = ?
        """, (
            schedule.title,
            schedule.scheduled_date.isoformat(),
            schedule.start_time.strftime("%H:%M") if schedule.start_time else None,
            schedule.end_time.strftime("%H:%M") if schedule.end_time else None,
            schedule.location,
            schedule.memo,
            schedule.major_category,
            schedule.status,
            schedule.id,
        ))
        self._conn.commit()

        return cursor.rowcount > 0

    # ==================== DELETE ====================

    def delete(self, schedule_id: int) -> bool:
        """
        일정 삭제

        Args:
            schedule_id: 삭제할 일정 ID

        Returns:
            bool: 삭제 성공 여부
        """
        cursor = self._conn.execute(
            "DELETE FROM schedules WHERE id = ?",
            (schedule_id,)
        )
        self._conn.commit()

        return cursor.rowcount > 0

    # ==================== ADDITIONAL QUERIES ====================

    def get_upcoming(self, days: int = 7) -> List[Schedule]:
        """
        다가오는 일정 조회 (오늘 이후 ~ n일 이내)

        Why: 앞으로의 일정을 미리 확인하여 계획을 세우기 위함

        Args:
            days: 조회할 일수 (기본 7일)

        Returns:
            해당 기간 내 일정 목록 (날짜, 시간 순 정렬)
        """
        today = date.today()
        end_date = today + timedelta(days=days)

        cursor = self._conn.execute("""
            SELECT * FROM schedules
            WHERE scheduled_date >= ? AND scheduled_date <= ?
            ORDER BY scheduled_date ASC, start_time ASC NULLS LAST
        """, (today.isoformat(), end_date.isoformat()))

        return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def search(self, query: str) -> List[Schedule]:
        """
        키워드로 일정 검색

        Why: 제목이나 장소로 빠르게 일정을 찾기 위함

        Args:
            query: 검색어

        Returns:
            검색 결과 목록
        """
        search_pattern = f"%{query}%"

        cursor = self._conn.execute("""
            SELECT * FROM schedules
            WHERE title LIKE ? COLLATE NOCASE
               OR location LIKE ? COLLATE NOCASE
            ORDER BY scheduled_date DESC, start_time ASC
        """, (search_pattern, search_pattern))

        return [self._row_to_schedule(row) for row in cursor.fetchall()]

    # ==================== MIGRATION ====================

    def _migrate_add_memo_column(self) -> None:
        """
        기존 테이블에 memo 컬럼이 없으면 추가

        Why: 기존 데이터를 유지하면서 스키마를 확장하기 위함
        """
        cursor = self._conn.execute("PRAGMA table_info(schedules)")
        columns = [row[1] for row in cursor.fetchall()]

        if "memo" not in columns:
            self._conn.execute("ALTER TABLE schedules ADD COLUMN memo TEXT")
            self._conn.commit()

    # ==================== HELPER ====================

    def _row_to_schedule(self, row: sqlite3.Row) -> Schedule:
        """
        DB row를 Schedule 객체로 변환

        Why: DB 조회 결과를 도메인 객체로 변환하여
             타입 안전성과 비즈니스 로직 적용을 보장한다.
        """
        start_time = None
        if row["start_time"]:
            parts = row["start_time"].split(":")
            start_time = time(int(parts[0]), int(parts[1]))

        end_time = None
        if row["end_time"]:
            parts = row["end_time"].split(":")
            end_time = time(int(parts[0]), int(parts[1]))

        return Schedule(
            id=row["id"],
            title=row["title"],
            scheduled_date=date.fromisoformat(row["scheduled_date"]),
            start_time=start_time,
            end_time=end_time,
            location=row["location"],
            memo=row["memo"],
            major_category=row["major_category"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
