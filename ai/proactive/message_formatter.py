"""Discord message formatting for proactive alerts."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from ai.core.logger import get_logger

KST = ZoneInfo("Asia/Seoul")


class MessageFormatter:
    """
    능동 알림 메시지를 Discord 형식으로 포맷팅합니다.

    비서 격식체 톤으로 작성하며, 이모지와 구조화된 레이아웃을 사용합니다.
    """

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)

    def format_capacity_analysis(
        self,
        analysis: Dict[str, Any],
        current_time: Optional[datetime] = None
    ) -> str:
        """
        작업 용량 분석 결과를 Discord 메시지로 포맷팅합니다.

        Args:
            analysis: capacity_analyzer의 분석 결과
            current_time: 현재 시간 (None이면 현재 시간 사용)

        Returns:
            Discord 메시지 문자열
        """
        if current_time is None:
            current_time = datetime.now(KST)

        status = analysis.get("status", "알 수 없음")
        total_hours = analysis.get("total_hours", 0.0)
        remaining_hours = analysis.get("remaining_hours", 0.0)
        todos = analysis.get("todos", [])
        schedule = analysis.get("schedule", [])

        # 상태 이모지 선택
        status_emoji = self._get_status_emoji(status)

        # 시간 표시
        time_str = current_time.strftime("%H:%M")

        # 메시지 헤더
        message = f"{status_emoji} **오늘의 작업 현황** ({time_str} 기준)\n\n"

        # 작업 개요
        message += f"📋 처리 대상: **{len(todos)}건** (총 {total_hours:.1f}시간 소요 예상)\n"
        message += f"⏰ 남은 시간: **{remaining_hours:.1f}시간**\n"
        message += f"📊 상태: **{status}**\n\n"

        # 상태별 메시지
        if status == "여유":
            message += "✅ 여유롭게 진행 가능합니다.\n\n"
        elif status == "빠듯":
            message += "⚠️ 시간이 빠듯합니다. 집중이 필요합니다.\n\n"
        elif status == "과부하":
            message += "🔴 **작업 과부하 경고**\n⚠️ 일정 조정이 필요합니다.\n\n"

        # 권장 일정
        if schedule:
            if status == "과부하":
                message += "**우선순위 작업:**\n"
                # 과부하일 때는 긴급한 것만 표시
                urgent_tasks = [s for s in schedule if s.get("is_urgent", False)]
                if urgent_tasks:
                    for idx, task in enumerate(urgent_tasks[:3], 1):
                        message += self._format_schedule_item(idx, task)
                    message += "\n"

                # 조정이 필요한 작업
                non_urgent = [s for s in schedule if not s.get("is_urgent", False)]
                if non_urgent:
                    message += "**⚠️ 다음 작업의 일정 조정을 권장합니다:**\n"
                    for task in non_urgent[:3]:
                        title = task.get("title", "제목 없음")
                        hours = task.get("estimated_hours", 0)
                        message += f"- [{title}] - {hours:.1f}시간 소요 예상\n"
            else:
                message += "**권장 일정:**\n"
                for idx, task in enumerate(schedule, 1):
                    message += self._format_schedule_item(idx, task)

        return message.strip()

    def format_advance_notification(
        self,
        d2_todos: List[Dict[str, Any]],
        d3_todos: List[Dict[str, Any]]
    ) -> str:
        """
        D-2, D-3 사전 알림을 Discord 메시지로 포맷팅합니다.

        Args:
            d2_todos: D-2 (모레) 마감 TODO 목록
            d3_todos: D-3 (3일 후) 마감 TODO 목록

        Returns:
            Discord 메시지 문자열
        """
        message = "📅 **다가오는 마감일 알림**\n\n"

        has_content = False

        # D-2 알림
        if d2_todos:
            has_content = True
            message += "**🔴 D-2 (모레 마감):**\n"
            for todo in d2_todos:
                title = todo.get("title", "제목 없음")
                due_date_str = todo.get("due_date", "")
                estimated_hours = todo.get("estimated_hours", 0)

                # 마감일 파싱
                due_display = self._format_due_date(due_date_str)

                message += f"- **[{title}]** - 예상 {estimated_hours:.1f}시간 소요\n"
                message += f"  마감: {due_display}\n"

            message += "\n"

        # D-3 알림
        if d3_todos:
            has_content = True
            message += "**🟡 D-3:**\n"
            for todo in d3_todos:
                title = todo.get("title", "제목 없음")
                due_date_str = todo.get("due_date", "")
                estimated_hours = todo.get("estimated_hours", 0)

                due_display = self._format_due_date(due_date_str)

                message += f"- **[{title}]** - 예상 {estimated_hours:.1f}시간 소요\n"
                message += f"  마감: {due_display}\n"

            message += "\n"

        if has_content:
            message += "💡 미리 일정을 확보하시는 것을 권장합니다."
        else:
            message = "📅 다가오는 마감일이 없습니다."

        return message.strip()

    # ========== 내부 헬퍼 메서드 ==========

    def _get_status_emoji(self, status: str) -> str:
        """상태에 따른 이모지를 반환합니다."""
        status_map = {
            "여유": "🟢",
            "빠듯": "🟡",
            "과부하": "🔴"
        }
        return status_map.get(status, "⚪")

    def _format_schedule_item(self, index: int, task: Dict[str, Any]) -> str:
        """일정 항목을 포맷팅합니다."""
        title = task.get("title", "제목 없음")
        start_time = task.get("start_time", "")
        end_time = task.get("end_time", "")
        estimated_hours = task.get("estimated_hours", 0)
        due_date_str = task.get("due_date", "")

        # 시간 범위 포맷팅
        time_range = ""
        if start_time and end_time:
            time_range = f" ({start_time}~{end_time})"

        # 마감일 포맷팅
        due_display = ""
        if due_date_str:
            due_dt = self._parse_datetime(due_date_str)
            if due_dt:
                due_display = f" | 마감: {due_dt.strftime('%m/%d %H:%M')}"

        message = f"{index}. **[{title}]**{time_range}\n"
        message += f"   - 예상 {estimated_hours:.1f}시간{due_display}\n\n"

        return message

    def _format_due_date(self, due_date_str: str) -> str:
        """마감일을 읽기 쉬운 형식으로 포맷팅합니다."""
        due_dt = self._parse_datetime(due_date_str)
        if not due_dt:
            return due_date_str

        now = datetime.now(KST)
        date_part = due_dt.strftime("%m월 %d일")
        time_part = due_dt.strftime("%H:%M")

        # 요일 추가
        weekday_map = {
            0: "월", 1: "화", 2: "수", 3: "목",
            4: "금", 5: "토", 6: "일"
        }
        weekday = weekday_map.get(due_dt.weekday(), "")

        return f"{date_part} ({weekday}) {time_part}"

    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """ISO 8601 형식의 datetime 문자열을 파싱합니다."""
        if not dt_str:
            return None
        try:
            # Handle 'Z' suffix (UTC indicator)
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(dt_str)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=KST)
            return dt
        except (ValueError, TypeError):
            return None
