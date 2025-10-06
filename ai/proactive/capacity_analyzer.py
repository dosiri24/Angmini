"""Work capacity analysis for proactive alerts."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger
from mcp.tools.notion_tool import NotionTool

KST = ZoneInfo("Asia/Seoul")


class CapacityAnalyzer:
    """
    Notion TODO를 분석하여 오늘의 작업 용량을 계산합니다.

    분석 결과:
    - 총 예상 소요 시간
    - 남은 활동 시간
    - 작업 가능 여부 (여유/빠듯/과부하)
    - 권장 일정
    """

    # 활동 시간 설정 (환경변수로 변경 가능)
    WORK_START_HOUR = 9
    WORK_END_HOUR = 23  # 23:59까지 (datetime.replace는 0-23만 허용)

    # 휴식 시간 (분)
    BREAK_MINUTES = 30

    # 작업 가능 여부 판단 기준
    THRESHOLD_COMFORTABLE = 1.0  # 총_소요 ≤ 남은시간 * 1.0
    THRESHOLD_TIGHT = 1.2        # 총_소요 ≤ 남은시간 * 1.2

    def __init__(self, notion_tool: Optional[NotionTool] = None) -> None:
        self._notion_tool = notion_tool or NotionTool()
        self._logger = get_logger(self.__class__.__name__)

    def analyze(self, current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        작업 용량을 분석하고 권장 일정을 생성합니다.

        Args:
            current_time: 분석 기준 시간 (None이면 현재 시간)

        Returns:
            분석 결과 딕셔너리:
            {
                "status": "여유" | "빠듯" | "과부하",
                "total_hours": float,
                "remaining_hours": float,
                "todos": List[Dict],
                "schedule": List[Dict]
            }
        """
        if current_time is None:
            current_time = datetime.now(KST)

        # Notion TODO 조회
        todos = self._fetch_relevant_todos()
        if not todos:
            return {
                "status": "여유",
                "total_hours": 0.0,
                "remaining_hours": self._calculate_remaining_hours(current_time),
                "todos": [],
                "schedule": []
            }

        # 총 예상 소요 시간 계산
        total_hours = sum(todo.get("estimated_hours", 0) for todo in todos)

        # 남은 활동 시간 계산
        remaining_hours = self._calculate_remaining_hours(current_time)

        # 작업 가능 여부 판단
        status = self._determine_status(total_hours, remaining_hours)

        # 권장 일정 생성
        schedule = self._generate_schedule(todos, current_time, status)

        return {
            "status": status,
            "total_hours": total_hours,
            "remaining_hours": remaining_hours,
            "todos": todos,
            "schedule": schedule
        }

    def _fetch_relevant_todos(self) -> List[Dict[str, Any]]:
        """
        Notion에서 관련 TODO를 조회합니다.

        대상: 오늘/내일 마감 + 마감 지났지만 미완료
        """
        try:
            now = datetime.now(KST)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            # 오늘 + 내일 = 2일간 (tomorrow_end는 모레 00:00:00, 즉 내일 마지막 순간 직전)
            tomorrow_end = today_start + timedelta(days=2)

            # Notion API 필터 (오늘 ~ 내일 마감 또는 마감 지난 미완료 작업)
            filter_payload = {
                "or": [
                    # 오늘 ~ 내일 마감
                    {
                        "and": [
                            {
                                "property": "마감일",
                                "date": {
                                    "on_or_after": today_start.isoformat()
                                }
                            },
                            {
                                "property": "마감일",
                                "date": {
                                    "before": tomorrow_end.isoformat()
                                }
                            }
                        ]
                    },
                    # 마감 지났지만 미완료
                    {
                        "property": "마감일",
                        "date": {
                            "before": today_start.isoformat()
                        }
                    }
                ]
            }

            # 정렬: 마감일 빠른 순
            sorts = [
                {
                    "property": "마감일",
                    "direction": "ascending"
                }
            ]

            result = self._notion_tool.run(
                operation="list_tasks",
                filter=filter_payload,
                sorts=sorts,
                page_size=50
            )

            if not result.success:
                self._logger.error(f"Failed to fetch todos: {result.error}")
                return []

            items = result.data.get("items", [])

            # 완료된 작업 제외 및 예상 소요 시간 파싱
            todos = []
            for item in items:
                status = item.get("status", "")
                if status and "완료" in status.lower():
                    continue

                # 예상 소요 시간 파싱 (TODO: Notion 필드에서 읽어오도록 수정 필요)
                # 현재는 기본값 2시간 사용
                estimated_hours = self._parse_estimated_hours(item)

                todos.append({
                    "id": item.get("id"),
                    "title": item.get("title", "제목 없음"),
                    "status": status,
                    "due_date": item.get("date"),
                    "estimated_hours": estimated_hours,
                    "url": item.get("url")
                })

            self._logger.info(f"Fetched {len(todos)} relevant todos")
            return todos

        except ToolError as exc:
            self._logger.error(f"Notion API error: {exc}")
            return []
        except Exception as exc:
            self._logger.exception(f"Unexpected error fetching todos: {exc}")
            return []

    def _parse_estimated_hours(self, todo_item: Dict[str, Any]) -> float:
        """
        TODO 항목에서 예상 소요 시간을 파싱합니다.

        Notion의 "예상 소요 시간" 필드에서 읽어옵니다.
        필드가 없거나 값이 없으면 기본값 2시간 반환
        """
        estimated = todo_item.get("estimated_hours")
        if isinstance(estimated, (int, float)) and estimated > 0:
            return float(estimated)

        return 2.0  # 기본값

    def _calculate_remaining_hours(self, current_time: datetime) -> float:
        """
        현재 시간부터 활동 종료 시간까지 남은 시간을 계산합니다.

        Args:
            current_time: 현재 시간

        Returns:
            남은 시간 (시간 단위, float)
        """
        work_end = current_time.replace(
            hour=self.WORK_END_HOUR,
            minute=59,
            second=59,
            microsecond=999999
        )

        if current_time >= work_end:
            # 이미 활동 시간 종료
            return 0.0

        remaining = work_end - current_time
        remaining_hours = remaining.total_seconds() / 3600.0

        # 음수 방지
        return max(0.0, remaining_hours)

    def _determine_status(self, total_hours: float, remaining_hours: float) -> str:
        """
        작업 가능 여부를 판단합니다.

        Args:
            total_hours: 총 예상 소요 시간
            remaining_hours: 남은 활동 시간

        Returns:
            "여유" | "빠듯" | "과부하"
        """
        if remaining_hours == 0:
            return "과부하" if total_hours > 0 else "여유"

        if total_hours <= remaining_hours * self.THRESHOLD_COMFORTABLE:
            return "여유"
        elif total_hours <= remaining_hours * self.THRESHOLD_TIGHT:
            return "빠듯"
        else:
            return "과부하"

    def _generate_schedule(
        self,
        todos: List[Dict[str, Any]],
        current_time: datetime,
        status: str
    ) -> List[Dict[str, Any]]:
        """
        권장 일정을 생성합니다.

        마감일 빠른 순으로 정렬하고, 휴식 시간 30분을 포함합니다.

        Args:
            todos: TODO 목록 (이미 마감일 순으로 정렬됨)
            current_time: 현재 시간
            status: 작업 가능 여부 (여유/빠듯/과부하)

        Returns:
            권장 일정 목록
        """
        schedule = []
        current_slot = current_time

        for idx, todo in enumerate(todos):
            estimated_hours = todo.get("estimated_hours", 0)
            if estimated_hours == 0:
                continue

            # 시작 시간
            start_time = current_slot

            # 종료 시간
            duration = timedelta(hours=estimated_hours)
            end_time = start_time + duration

            # 마감일 파싱
            due_date_str = todo.get("due_date")
            is_urgent = False
            if due_date_str:
                try:
                    # Handle 'Z' suffix (UTC indicator)
                    if due_date_str.endswith('Z'):
                        due_date_str_normalized = due_date_str[:-1] + '+00:00'
                    else:
                        due_date_str_normalized = due_date_str
                    due_dt = datetime.fromisoformat(due_date_str_normalized)
                    if not due_dt.tzinfo:
                        due_dt = due_dt.replace(tzinfo=KST)
                    # 3시간 이내 마감이면 긴급
                    if due_dt - current_time < timedelta(hours=3):
                        is_urgent = True
                except (ValueError, TypeError):
                    pass

            schedule_item = {
                "title": todo.get("title"),
                "start_time": start_time.strftime("%H:%M"),
                "end_time": end_time.strftime("%H:%M"),
                "estimated_hours": estimated_hours,
                "due_date": due_date_str,
                "is_urgent": is_urgent
            }
            schedule.append(schedule_item)

            # 다음 작업 시작 시간 (휴식 포함)
            current_slot = end_time + timedelta(minutes=self.BREAK_MINUTES)

        return schedule
