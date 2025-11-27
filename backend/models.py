"""
Schedule 데이터 모델

Why: 일정 데이터의 구조와 유효성을 보장하여
     시스템 전체에서 일관된 데이터 형태를 유지한다.
"""
from dataclasses import dataclass, field
from datetime import date, time, datetime
from typing import Optional


# 허용되는 대분류 카테고리
VALID_CATEGORIES = ("학업", "약속", "개인", "업무", "루틴", "기타")

# 허용되는 상태 값
VALID_STATUSES = ("예정", "완료", "취소")


class ScheduleValidationError(Exception):
    """Schedule 유효성 검증 실패 시 발생하는 예외"""
    pass


@dataclass
class Schedule:
    """
    일정 데이터를 나타내는 클래스

    Why: 일정의 모든 속성을 구조화하여 타입 안전성과
         직렬화/역직렬화의 일관성을 보장한다.
    """
    title: str
    scheduled_date: date
    major_category: str
    id: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None
    status: str = "예정"
    created_at: datetime = field(default_factory=datetime.now)

    def validate(self) -> None:
        """
        Schedule 데이터의 유효성을 검증한다.

        Why: 잘못된 데이터가 DB에 저장되는 것을 방지하여
             데이터 무결성을 보장한다.

        Raises:
            ScheduleValidationError: 유효성 검증 실패 시
        """
        # title 검증
        if not self.title or not self.title.strip():
            raise ScheduleValidationError("Title은 비어있을 수 없습니다.")

        # category 검증
        if self.major_category not in VALID_CATEGORIES:
            raise ScheduleValidationError(
                f"Category는 {VALID_CATEGORIES} 중 하나여야 합니다. "
                f"입력값: {self.major_category}"
            )

        # status 검증
        if self.status not in VALID_STATUSES:
            raise ScheduleValidationError(
                f"Status는 {VALID_STATUSES} 중 하나여야 합니다. "
                f"입력값: {self.status}"
            )

        # 시간 검증: end_time이 start_time보다 빠르면 안됨
        if self.start_time and self.end_time:
            if self.end_time < self.start_time:
                raise ScheduleValidationError(
                    "종료 시간이 시작 시간보다 빠를 수 없습니다."
                )

    def to_dict(self) -> dict:
        """
        Schedule을 딕셔너리로 변환한다.

        Why: JSON 직렬화나 DB 저장을 위해 표준 Python dict로 변환한다.

        Returns:
            dict: 모든 필드를 포함하는 딕셔너리
        """
        return {
            "id": self.id,
            "title": self.title,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "location": self.location,
            "major_category": self.major_category,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Schedule":
        """
        딕셔너리에서 Schedule 객체를 생성한다.

        Why: JSON 역직렬화나 DB 조회 결과를 Schedule 객체로 변환한다.

        Args:
            data: Schedule 필드를 포함하는 딕셔너리

        Returns:
            Schedule: 생성된 Schedule 객체
        """
        # 날짜/시간 문자열을 파싱 (scheduled_date는 필수)
        if not data.get("scheduled_date"):
            raise ValueError("scheduled_date는 필수 필드입니다.")
        scheduled_date = date.fromisoformat(data["scheduled_date"])

        start_time = None
        if data.get("start_time"):
            parts = data["start_time"].split(":")
            start_time = time(int(parts[0]), int(parts[1]))

        end_time = None
        if data.get("end_time"):
            parts = data["end_time"].split(":")
            end_time = time(int(parts[0]), int(parts[1]))

        created_at = (
            datetime.fromisoformat(data["created_at"])
            if data.get("created_at") else datetime.now()
        )

        return cls(
            id=data.get("id"),
            title=data["title"],
            scheduled_date=scheduled_date,
            start_time=start_time,
            end_time=end_time,
            location=data.get("location"),
            major_category=data["major_category"],
            status=data.get("status", "예정"),
            created_at=created_at,
        )
