"""LLM-based message generation for proactive alerts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from ai.ai_brain import AIBrain, PromptMessage
from ai.core.config import Config
from ai.core.logger import get_logger

KST = ZoneInfo("Asia/Seoul")


class LLMMessageGenerator:
    """
    LLM을 활용하여 능동 알림 메시지를 자연스러운 비서 톤으로 생성합니다.

    구조화된 데이터를 입력받아 Gemini API를 통해 친근하고 격식 있는 한국어 메시지를 생성합니다.
    """

    def __init__(
        self,
        ai_brain: Optional[AIBrain] = None,
        config: Optional[Config] = None
    ) -> None:
        """
        Args:
            ai_brain: Gemini API 연동을 위한 AIBrain 인스턴스
            config: 설정 객체
        """
        self._config = config or Config.load()
        self._ai_brain = ai_brain or AIBrain(self._config)
        self._logger = get_logger(self.__class__.__name__)

    def generate_capacity_message(
        self,
        analysis: Dict[str, Any],
        current_time: Optional[datetime] = None,
        conversation_context: Optional[str] = None
    ) -> str:
        """
        작업 용량 분석 결과로부터 LLM 기반 메시지를 생성합니다.

        Args:
            analysis: CapacityAnalyzer의 분석 결과
            current_time: 현재 시간 (None이면 현재 시간 사용)
            conversation_context: 최근 대화 컨텍스트 (선택)

        Returns:
            LLM이 생성한 Discord 메시지 문자열
        """
        if current_time is None:
            current_time = datetime.now(KST)

        status = analysis.get("status", "알 수 없음")
        total_hours = analysis.get("total_hours", 0.0)
        remaining_hours = analysis.get("remaining_hours", 0.0)
        todos = analysis.get("todos", [])
        schedule = analysis.get("schedule", [])

        # 구조화된 데이터를 프롬프트로 변환
        prompt = self._build_capacity_prompt(
            status=status,
            total_hours=total_hours,
            remaining_hours=remaining_hours,
            todos=todos,
            schedule=schedule,
            current_time=current_time,
            conversation_context=conversation_context
        )

        # LLM 호출
        try:
            response = self._ai_brain.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_output_tokens=1000
            )
            message = response.text.strip()
            self._logger.debug(f"Generated capacity message: {len(message)} chars")
            return message
        except Exception as exc:
            self._logger.exception(f"Failed to generate LLM message: {exc}")
            # Fallback: 간단한 템플릿 메시지
            return self._fallback_capacity_message(analysis, current_time)

    def generate_advance_message(
        self,
        d2_todos: List[Dict[str, Any]],
        d3_todos: List[Dict[str, Any]],
        conversation_context: Optional[str] = None
    ) -> str:
        """
        D-2, D-3 사전 알림 메시지를 LLM으로 생성합니다.

        Args:
            d2_todos: D-2 (모레) 마감 TODO 목록
            d3_todos: D-3 (3일 후) 마감 TODO 목록
            conversation_context: 최근 대화 컨텍스트 (선택)

        Returns:
            LLM이 생성한 Discord 메시지 문자열
        """
        prompt = self._build_advance_prompt(
            d2_todos=d2_todos,
            d3_todos=d3_todos,
            conversation_context=conversation_context
        )

        try:
            response = self._ai_brain.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_output_tokens=800
            )
            message = response.text.strip()
            self._logger.debug(f"Generated advance message: {len(message)} chars")
            return message
        except Exception as exc:
            self._logger.exception(f"Failed to generate advance message: {exc}")
            # Fallback
            return self._fallback_advance_message(d2_todos, d3_todos)

    # ========== 프롬프트 빌더 ==========

    def _build_capacity_prompt(
        self,
        status: str,
        total_hours: float,
        remaining_hours: float,
        todos: List[Dict[str, Any]],
        schedule: List[Dict[str, Any]],
        current_time: datetime,
        conversation_context: Optional[str]
    ) -> str:
        """작업 용량 분석을 위한 LLM 프롬프트를 생성합니다."""
        time_str = current_time.strftime("%H:%M")

        # TODO 목록 포맷팅
        todos_text = ""
        for idx, todo in enumerate(todos, 1):
            title = todo.get("title", "제목 없음")
            est_hours = todo.get("estimated_hours", 0)
            due_date = self._format_due_date(todo.get("due_date", ""))
            todos_text += f"{idx}. [{title}] - 예상 {est_hours:.1f}시간 소요, 마감: {due_date}\n"

        # 권장 일정 포맷팅
        schedule_text = ""
        if schedule:
            for idx, task in enumerate(schedule, 1):
                title = task.get("title", "제목 없음")
                start = task.get("start_time", "")
                end = task.get("end_time", "")
                est = task.get("estimated_hours", 0)
                schedule_text += f"{idx}. [{title}] ({start}~{end}) - {est:.1f}시간\n"

        # 컨텍스트 포함 여부
        context_section = ""
        if conversation_context:
            context_section = f"""
최근 대화 컨텍스트:
{conversation_context}
"""

        prompt = f"""당신은 친근하고 격식 있는 AI 비서입니다. 사용자의 작업 일정을 관리하고 능동적으로 알림을 보냅니다.

현재 시각: {time_str}
작업 상태: {status}
총 예상 소요 시간: {total_hours:.1f}시간
남은 활동 시간: {remaining_hours:.1f}시간

처리 대상 TODO ({len(todos)}건):
{todos_text}

권장 일정:
{schedule_text if schedule_text else "(일정이 없습니다)"}
{context_section}
위 정보를 바탕으로 사용자에게 친근하면서도 격식 있는 톤으로 작업 현황 알림을 작성하세요.

요구사항:
1. 이모지를 적절히 사용하여 가독성을 높이세요 (예: 🟢 여유, 🟡 빠듯, 🔴 과부하)
2. 현재 상황을 명확히 설명하고, 사용자에게 필요한 조언을 제공하세요
3. 권장 일정을 보기 쉽게 정리하여 제시하세요
4. 한국어로 작성하되, 비서다운 격식체를 사용하세요
5. 너무 길지 않게 간결하고 핵심적으로 작성하세요 (300자 이내)

알림 메시지를 작성하세요:"""

        return prompt

    def _build_advance_prompt(
        self,
        d2_todos: List[Dict[str, Any]],
        d3_todos: List[Dict[str, Any]],
        conversation_context: Optional[str]
    ) -> str:
        """D-2, D-3 사전 알림을 위한 LLM 프롬프트를 생성합니다."""
        d2_text = ""
        for todo in d2_todos:
            title = todo.get("title", "제목 없음")
            est = todo.get("estimated_hours", 0)
            due = self._format_due_date(todo.get("due_date", ""))
            d2_text += f"- [{title}] - {est:.1f}시간 소요, 마감: {due}\n"

        d3_text = ""
        for todo in d3_todos:
            title = todo.get("title", "제목 없음")
            est = todo.get("estimated_hours", 0)
            due = self._format_due_date(todo.get("due_date", ""))
            d3_text += f"- [{title}] - {est:.1f}시간 소요, 마감: {due}\n"

        context_section = ""
        if conversation_context:
            context_section = f"""
최근 대화 컨텍스트:
{conversation_context}
"""

        prompt = f"""당신은 친근하고 격식 있는 AI 비서입니다. 사용자의 마감일을 관리하고 사전에 알림을 보냅니다.

D-2 (모레 마감) 작업 ({len(d2_todos)}건):
{d2_text if d2_text else "(없음)"}

D-3 (3일 후 마감) 작업 ({len(d3_todos)}건):
{d3_text if d3_text else "(없음)"}
{context_section}
위 정보를 바탕으로 사용자에게 다가오는 마감일을 친근하게 알려주는 메시지를 작성하세요.

요구사항:
1. 이모지를 사용하여 긴급도를 표현하세요 (예: 🔴 D-2, 🟡 D-3)
2. 각 작업의 제목, 예상 소요 시간, 마감일을 명확히 전달하세요
3. 미리 일정을 확보하라는 조언을 자연스럽게 포함하세요
4. 한국어로 작성하되, 비서다운 격식체를 사용하세요
5. 간결하고 핵심적으로 작성하세요 (200자 이내)

알림 메시지를 작성하세요:"""

        return prompt

    # ========== Fallback 메시지 (LLM 실패 시) ==========

    def _fallback_capacity_message(
        self,
        analysis: Dict[str, Any],
        current_time: datetime
    ) -> str:
        """LLM 실패 시 사용할 간단한 템플릿 메시지입니다."""
        status = analysis.get("status", "알 수 없음")
        total_hours = analysis.get("total_hours", 0.0)
        remaining_hours = analysis.get("remaining_hours", 0.0)
        todos = analysis.get("todos", [])

        status_emoji = {"여유": "🟢", "빠듯": "🟡", "과부하": "🔴"}.get(status, "⚪")
        time_str = current_time.strftime("%H:%M")

        message = f"{status_emoji} **오늘의 작업 현황** ({time_str} 기준)\n\n"
        message += f"📋 처리 대상: {len(todos)}건 (총 {total_hours:.1f}시간)\n"
        message += f"⏰ 남은 시간: {remaining_hours:.1f}시간\n"
        message += f"📊 상태: **{status}**"

        return message

    def _fallback_advance_message(
        self,
        d2_todos: List[Dict[str, Any]],
        d3_todos: List[Dict[str, Any]]
    ) -> str:
        """LLM 실패 시 사용할 간단한 템플릿 메시지입니다."""
        message = "📅 **다가오는 마감일 알림**\n\n"

        if d2_todos:
            message += f"🔴 D-2 (모레 마감): {len(d2_todos)}건\n"
        if d3_todos:
            message += f"🟡 D-3: {len(d3_todos)}건\n"

        message += "\n💡 미리 일정을 확보하시는 것을 권장합니다."

        return message

    # ========== 유틸리티 ==========

    def _format_due_date(self, due_date_str: str) -> str:
        """마감일을 읽기 쉬운 형식으로 포맷팅합니다."""
        if not due_date_str:
            return "미정"

        try:
            # Handle 'Z' suffix (UTC indicator)
            if due_date_str.endswith('Z'):
                due_date_str = due_date_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(due_date_str)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=KST)

            weekday_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
            weekday = weekday_map.get(dt.weekday(), "")

            return f"{dt.strftime('%m/%d')} ({weekday}) {dt.strftime('%H:%M')}"
        except (ValueError, TypeError):
            return due_date_str
