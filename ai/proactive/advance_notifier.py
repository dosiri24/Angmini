"""D-2, D-3 advance notification for proactive alerts."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger
from mcp.tools.notion_tool import NotionTool

from .state_manager import StateManager

KST = ZoneInfo("Asia/Seoul")


class AdvanceNotifier:
    """
    D-2, D-3 사전 알림을 생성합니다.

    마감일이 2~3일 후인 미완료 TODO를 필터링하고,
    오늘 이미 알림을 보낸 TODO는 제외합니다.
    """

    def __init__(
        self,
        notion_tool: Optional[NotionTool] = None,
        state_manager: Optional[StateManager] = None
    ) -> None:
        self._notion_tool = notion_tool or NotionTool()
        self._state_manager = state_manager or StateManager()
        self._logger = get_logger(self.__class__.__name__)

    def check_advance_alerts(
        self,
        current_time: Optional[datetime] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        D-2, D-3 알림 대상 TODO를 조회합니다.

        Args:
            current_time: 현재 시간 (None이면 현재 시간 사용)

        Returns:
            {
                "d2_todos": List[Dict],  # D-2 (모레) 마감
                "d3_todos": List[Dict]   # D-3 마감
            }
        """
        if current_time is None:
            current_time = datetime.now(KST)

        # D-2 (모레) 마감 TODO
        d2_todos = self._fetch_d_day_todos(current_time, days=2)

        # D-3 마감 TODO
        d3_todos = self._fetch_d_day_todos(current_time, days=3)

        return {
            "d2_todos": d2_todos,
            "d3_todos": d3_todos
        }

    def _fetch_d_day_todos(
        self,
        current_time: datetime,
        days: int
    ) -> List[Dict[str, Any]]:
        """
        D-N일 후 마감 TODO를 조회합니다.

        Args:
            current_time: 현재 시간
            days: N일 (2 또는 3)

        Returns:
            D-N일 마감 TODO 목록
        """
        try:
            # D-N일의 시작/종료 시간
            target_date = current_time.date() + timedelta(days=days)
            target_start = datetime.combine(target_date, datetime.min.time(), tzinfo=KST)
            target_end = datetime.combine(target_date, datetime.max.time(), tzinfo=KST)

            # Notion API 필터 (D-N일 마감)
            filter_payload = {
                "and": [
                    {
                        "property": "마감일",
                        "date": {
                            "on_or_after": target_start.isoformat()
                        }
                    },
                    {
                        "property": "마감일",
                        "date": {
                            "before": target_end.isoformat()
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
                self._logger.error(f"Failed to fetch D-{days} todos: {result.error}")
                return []

            items = result.data.get("items", [])

            # 미완료 + 오늘 아직 알림 안 보낸 것만 필터링
            todos = []
            for item in items:
                status = item.get("status", "")
                if status and "완료" in status.lower():
                    continue

                title = item.get("title", "제목 없음")
                due_date = item.get("date")

                # 오늘 이미 알림 보냈는지 확인
                if self._state_manager.is_todo_alerted_today(title, due_date or ""):
                    self._logger.debug(f"Skipping already alerted todo: {title}")
                    continue

                # 예상 소요 시간 파싱 (TODO: Notion 필드에서 읽어오도록 수정)
                estimated_hours = self._parse_estimated_hours(item)

                todos.append({
                    "id": item.get("id"),
                    "title": title,
                    "status": status,
                    "due_date": due_date,
                    "estimated_hours": estimated_hours,
                    "url": item.get("url")
                })

            self._logger.info(f"Found {len(todos)} D-{days} todos (not alerted today)")
            return todos

        except ToolError as exc:
            self._logger.error(f"Notion API error: {exc}")
            return []
        except Exception as exc:
            self._logger.exception(f"Unexpected error fetching D-{days} todos: {exc}")
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

    def mark_as_alerted(self, todos: List[Dict[str, Any]]) -> None:
        """
        알림을 보낸 TODO를 상태 관리자에 기록합니다.

        Args:
            todos: 알림을 보낸 TODO 목록
        """
        for todo in todos:
            title = todo.get("title", "")
            due_date = todo.get("due_date", "")
            if title and due_date:
                self._state_manager.add_d2_d3_alert(title, due_date)
                self._logger.debug(f"Marked as alerted: {title}")
