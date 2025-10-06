"""Main scheduler for proactive alert system."""

from __future__ import annotations

import os
import random
import threading
import time
from datetime import datetime, time as dt_time, timedelta
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

from ai.core.logger import get_logger
from ai.memory.service import MemoryService

from .advance_notifier import AdvanceNotifier
from .capacity_analyzer import CapacityAnalyzer
from .llm_message_generator import LLMMessageGenerator
from .message_formatter import MessageFormatter
from .state_manager import StateManager

KST = ZoneInfo("Asia/Seoul")


def _getenv_bool(key: str, default: bool = False) -> bool:
    """환경변수를 boolean으로 변환합니다."""
    value = os.getenv(key, "").strip().lower()
    if not value:
        return default
    return value in ("true", "1", "yes", "on")


def _getenv_int(key: str, default: int) -> int:
    """환경변수를 int로 변환합니다."""
    value = os.getenv(key, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class ProactiveScheduler:
    """
    정규분포 기반 타이머로 주기적으로 Notion TODO를 분석하고
    Discord 채널에 능동 알림을 전송합니다.

    동작 방식:
    - 정규분포 기반 간격 (평균 30분, 표준편차 15분)
    - 활동 시간: 09:00 ~ 24:00 (KST)
    - 백그라운드 스레드로 실행
    - Discord 전용 (환경변수로 지정한 채널에만 메시지 전송)

    환경변수 설정:
    - PROACTIVE_ENABLED: 스케줄러 활성화 여부 (default: true)
    - PROACTIVE_WORK_START_HOUR: 활동 시작 시간 (default: 9)
    - PROACTIVE_WORK_END_HOUR: 활동 종료 시간 (default: 24)
    - PROACTIVE_INTERVAL_MEAN: 평균 실행 간격(분) (default: 30)
    - PROACTIVE_INTERVAL_STD: 표준편차(분) (default: 15)
    - PROACTIVE_D2_D3_ALERT: D-2/D-3 알림 활성화 (default: true)
    - PROACTIVE_CAPACITY_ALERT: 용량 분석 알림 활성화 (default: true)
    """

    def __init__(
        self,
        discord_send_callback: Optional[Callable[[str], None]] = None,
        capacity_analyzer: Optional[CapacityAnalyzer] = None,
        advance_notifier: Optional[AdvanceNotifier] = None,
        state_manager: Optional[StateManager] = None,
        message_formatter: Optional[MessageFormatter] = None,
        llm_generator: Optional[LLMMessageGenerator] = None,
        memory_service: Optional[MemoryService] = None,
    ) -> None:
        """
        Args:
            discord_send_callback: Discord 메시지 전송 콜백 함수
            capacity_analyzer: 작업 용량 분석기
            advance_notifier: D-2, D-3 알림기
            state_manager: 상태 관리자
            message_formatter: 메시지 포맷터 (fallback용)
            llm_generator: LLM 기반 메시지 생성기
            memory_service: 메모리 서비스 (대화 컨텍스트 제공)
        """
        self._discord_send = discord_send_callback
        # Shared StateManager instance to avoid race conditions
        self._state_manager = state_manager or StateManager()
        self._capacity_analyzer = capacity_analyzer or CapacityAnalyzer()
        # Share state_manager with advance_notifier to prevent duplicate instances
        self._advance_notifier = advance_notifier or AdvanceNotifier(state_manager=self._state_manager)
        self._message_formatter = message_formatter or MessageFormatter()
        self._llm_generator = llm_generator or LLMMessageGenerator()
        self._memory_service = memory_service  # Optional: None이면 컨텍스트 미제공
        self._logger = get_logger(self.__class__.__name__)

        # 환경변수에서 설정 로드
        self._enabled = _getenv_bool("PROACTIVE_ENABLED", True)
        self._interval_mean_minutes = _getenv_int("PROACTIVE_INTERVAL_MEAN", 30)
        self._interval_std_minutes = _getenv_int("PROACTIVE_INTERVAL_STD", 15)
        self._interval_min_minutes = 1  # 고정값
        self._interval_max_minutes = 60  # 고정값
        self._active_start_hour = _getenv_int("PROACTIVE_WORK_START_HOUR", 9)
        self._active_end_hour = _getenv_int("PROACTIVE_WORK_END_HOUR", 24)
        self._d2_d3_alert_enabled = _getenv_bool("PROACTIVE_D2_D3_ALERT", True)
        self._capacity_alert_enabled = _getenv_bool("PROACTIVE_CAPACITY_ALERT", True)
        self._min_capacity_alert_interval_minutes = 60  # 고정값
        self._min_bot_response_interval_minutes = 30  # 고정값

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """스케줄러를 시작합니다 (백그라운드 스레드)."""
        if not self._enabled:
            self._logger.info("Proactive scheduler disabled by PROACTIVE_ENABLED=false")
            return

        if self._running:
            self._logger.warning("Scheduler is already running")
            return

        if not self._discord_send:
            self._logger.warning("Discord send callback not set, scheduler will not send alerts")
            # 콜백이 없어도 시작은 가능 (테스트 용도)

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ProactiveScheduler")
        self._thread.start()
        self._logger.info(
            f"Proactive scheduler started "
            f"(interval: {self._interval_mean_minutes}±{self._interval_std_minutes}min, "
            f"hours: {self._active_start_hour}-{self._active_end_hour}, "
            f"capacity_alert: {self._capacity_alert_enabled}, "
            f"d2_d3_alert: {self._d2_d3_alert_enabled})"
        )

    def stop(self) -> None:
        """스케줄러를 중지합니다."""
        if not self._running:
            self._logger.warning("Scheduler is not running")
            return

        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._logger.info("Proactive scheduler stopped")

    def _run_loop(self) -> None:
        """메인 루프 (백그라운드 스레드에서 실행)."""
        self._logger.info("Scheduler loop started")

        while self._running:
            try:
                # 다음 실행 시간까지 대기
                next_interval_seconds = self._next_interval()
                self._logger.debug(f"Next check in {next_interval_seconds / 60:.1f} minutes")

                # 대기 (중간에 stop()이 호출되면 즉시 종료)
                if self._stop_event.wait(timeout=next_interval_seconds):
                    break

                # 활동 시간대 체크
                if not self._is_active_hours():
                    self._logger.debug("Outside active hours, skipping check")
                    continue

                # 알림 발송 가능 여부 판단
                if not self._should_alert():
                    self._logger.debug("Not ready to alert yet (recent bot response or capacity alert)")
                    continue

                # 알림 실행
                self._execute_alerts()

            except Exception as exc:
                self._logger.exception(f"Error in scheduler loop: {exc}")
                # 에러 발생 시 잠시 대기 후 재시도 (stop 이벤트에 반응)
                if self._stop_event.wait(timeout=60):
                    break

        self._logger.info("Scheduler loop ended")

    def _next_interval(self) -> float:
        """
        정규분포 기반 다음 실행 간격을 계산합니다 (초 단위).

        환경변수 설정값 사용 (평균, 표준편차, 최소, 최대)
        """
        interval_minutes = random.gauss(
            self._interval_mean_minutes,
            self._interval_std_minutes
        )

        # 범위 제한
        interval_minutes = max(self._interval_min_minutes, interval_minutes)
        interval_minutes = min(self._interval_max_minutes, interval_minutes)

        return interval_minutes * 60.0

    def _is_active_hours(self) -> bool:
        """활동 시간대인지 확인합니다 (환경변수 설정값 사용)."""
        now = datetime.now(KST)
        current_hour = now.hour

        return self._active_start_hour <= current_hour < self._active_end_hour

    def _should_alert(self) -> bool:
        """
        알림 발송 가능 여부를 판단합니다.

        조건:
        - 마지막 봇 응답 후 설정 시간 경과
        """
        now = datetime.now(KST)

        # 마지막 봇 응답 확인
        last_bot_response = self._state_manager.get_last_bot_response()
        if last_bot_response:
            elapsed = now - last_bot_response
            if elapsed < timedelta(minutes=self._min_bot_response_interval_minutes):
                return False

        return True

    def _execute_alerts(self) -> None:
        """알림을 실행합니다 (용량 분석 + D-2/D-3 알림)."""
        now = datetime.now(KST)

        # 1. 작업 용량 분석 알림 (환경변수 설정 확인)
        if self._capacity_alert_enabled:
            self._check_capacity_alert(now)

        # 2. D-2, D-3 사전 알림 (환경변수 설정 확인)
        if self._d2_d3_alert_enabled:
            self._check_advance_alert(now)

    def _check_capacity_alert(self, current_time: datetime) -> None:
        """
        작업 용량 분석 알림을 확인하고 발송합니다.

        발송 조건:
        - 처리 대상 TODO가 1개 이상
        - 총 예상 소요 시간 ≥ 1시간
        - 마지막 용량 분석 알림 후 1시간 경과
        """
        # 마지막 용량 알림 시간 확인
        last_capacity = self._state_manager.get_last_capacity_alert()
        if last_capacity:
            elapsed = current_time - last_capacity
            if elapsed < timedelta(minutes=self._min_capacity_alert_interval_minutes):
                self._logger.debug("Skipping capacity alert (too soon)")
                return

        # 작업 용량 분석
        try:
            analysis = self._capacity_analyzer.analyze(current_time)
        except Exception as exc:
            self._logger.exception(f"Failed to analyze capacity: {exc}")
            return

        # 발송 조건 확인
        todos = analysis.get("todos", [])
        total_hours = analysis.get("total_hours", 0.0)

        if len(todos) == 0:
            self._logger.debug("No todos to process, skipping capacity alert")
            return

        if total_hours < 1.0:
            self._logger.debug("Total hours < 1, skipping capacity alert")
            return

        # LLM 기반 메시지 생성 (최근 대화 컨텍스트 포함)
        conversation_context = self._get_recent_conversation_context()
        try:
            message = self._llm_generator.generate_capacity_message(
                analysis=analysis,
                current_time=current_time,
                conversation_context=conversation_context
            )
        except Exception as exc:
            self._logger.warning(f"LLM message generation failed, using fallback: {exc}")
            # Fallback: 기존 템플릿 메시지
            message = self._message_formatter.format_capacity_analysis(analysis, current_time)

        # Discord 전송
        self._send_to_discord(message)

        # 상태 업데이트
        self._state_manager.update_capacity_alert(current_time)

        self._logger.info(f"Sent capacity alert: {len(todos)} todos, {total_hours:.1f} hours")

    def _check_advance_alert(self, current_time: datetime) -> None:
        """
        D-2, D-3 사전 알림을 확인하고 발송합니다.

        발송 조건:
        - 마감일이 2~3일 후인 TODO가 있음
        - 해당 TODO에 대해 오늘 아직 알림 안 보냄
        """
        try:
            alert_data = self._advance_notifier.check_advance_alerts(current_time)
        except Exception as exc:
            self._logger.exception(f"Failed to check advance alerts: {exc}")
            return

        d2_todos = alert_data.get("d2_todos", [])
        d3_todos = alert_data.get("d3_todos", [])

        # 발송할 알림이 없으면 종료
        if not d2_todos and not d3_todos:
            self._logger.debug("No advance alerts to send")
            return

        # LLM 기반 메시지 생성 (최근 대화 컨텍스트 포함)
        conversation_context = self._get_recent_conversation_context()
        try:
            message = self._llm_generator.generate_advance_message(
                d2_todos=d2_todos,
                d3_todos=d3_todos,
                conversation_context=conversation_context
            )
        except Exception as exc:
            self._logger.warning(f"LLM advance message generation failed, using fallback: {exc}")
            # Fallback: 기존 템플릿 메시지
            message = self._message_formatter.format_advance_notification(d2_todos, d3_todos)

        # Discord 전송
        self._send_to_discord(message)

        # 상태 업데이트 (알림 보낸 TODO 기록)
        all_alerted = d2_todos + d3_todos
        self._advance_notifier.mark_as_alerted(all_alerted)

        self._logger.info(f"Sent advance alert: {len(d2_todos)} D-2, {len(d3_todos)} D-3")

    def _send_to_discord(self, message: str) -> None:
        """Discord에 메시지를 전송합니다."""
        if not self._discord_send:
            self._logger.warning("Discord send callback not set, message not sent")
            self._logger.debug(f"Message (not sent):\n{message}")
            return

        try:
            self._discord_send(message)
            self._logger.debug(f"Sent message to Discord: {len(message)} chars")
        except Exception as exc:
            self._logger.exception(f"Failed to send Discord message: {exc}")

    # ========== 유틸리티 메서드 ==========

    def _get_recent_conversation_context(self, max_chars: int = 500) -> Optional[str]:
        """
        MemoryService에서 최근 대화 컨텍스트를 가져옵니다.

        Args:
            max_chars: 최대 문자 수

        Returns:
            최근 대화 요약 (없으면 None)
        """
        if not self._memory_service:
            return None

        try:
            # MemoryRepository에서 최근 기록 조회
            all_records = list(self._memory_service.repository.list_all())
            if not all_records:
                return None

            # 최근 3개 기록 추출 (시간 역순)
            recent_records = sorted(
                all_records,
                key=lambda r: r.source_metadata.get("retention_timestamp", ""),
                reverse=True
            )[:3]

            # 요약 텍스트 생성
            context_parts = []
            for record in recent_records:
                summary = record.summary[:150] if record.summary else ""
                if summary:
                    context_parts.append(f"- {summary}")

            context = "\n".join(context_parts)
            if len(context) > max_chars:
                context = context[:max_chars] + "..."

            return context if context else None

        except Exception as exc:
            self._logger.warning(f"Failed to get conversation context: {exc}")
            return None

    # ========== 외부 이벤트 리스너 ==========

    def on_bot_response(self) -> None:
        """
        봇이 사용자 메시지에 응답했을 때 호출합니다.

        Discord 봇의 on_message 핸들러에서 호출하여
        마지막 봇 응답 시간을 업데이트합니다.
        """
        now = datetime.now(KST)
        self._state_manager.update_bot_response(now)
        self._logger.debug("Updated bot response timestamp")
