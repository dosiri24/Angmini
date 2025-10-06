"""JSON-based state management for proactive alert system."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from ai.core.logger import get_logger

KST = ZoneInfo("Asia/Seoul")


class StateManager:
    """
    능동 알림 시스템의 상태를 JSON 파일로 관리합니다.

    상태 데이터:
    - last_bot_response: 마지막 봇 응답 시간
    - last_capacity_alert: 마지막 용량 분석 알림 시간
    - today_alert_count: 오늘 발송한 알림 수
    - d2_d3_alerts_today: 오늘 보낸 D-2, D-3 알림 목록
    - todo_alert_history: TODO별 알림 히스토리
    """

    DEFAULT_STATE_FILE = Path("data/proactive/alert_history.json")

    def __init__(self, state_file: Optional[Path] = None) -> None:
        self._state_file = state_file or self.DEFAULT_STATE_FILE
        self._logger = get_logger(self.__class__.__name__)
        self._state: Dict[str, Any] = {}
        self._lock = threading.RLock()  # Thread-safe access to state (reentrant for nested calls)
        self._ensure_state_file()
        self._load_state()

    def _ensure_state_file(self) -> None:
        """상태 파일과 디렉토리가 존재하는지 확인하고 없으면 생성합니다."""
        # Secure directory permissions (0o700)
        self._state_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Enforce permissions even if directory already existed
        try:
            os.chmod(self._state_file.parent, 0o700)
        except (OSError, PermissionError):
            pass  # Best-effort permission enforcement

        if not self._state_file.exists():
            initial_state = {
                "last_bot_response": None,
                "last_capacity_alert": None,
                "last_reset_date": None,
                "today_alert_count": 0,
                "d2_d3_alerts_today": [],
                "todo_alert_history": []
            }
            self._atomic_write(initial_state)
            # Secure file permissions (0o600)
            os.chmod(self._state_file, 0o600)
            self._logger.info(f"Created initial state file: {self._state_file}")

    def _load_state(self) -> None:
        """상태 파일을 읽어 메모리에 로드합니다."""
        with self._lock:
            try:
                content = self._state_file.read_text(encoding="utf-8")
                self._state = json.loads(content)

                # 자정 넘어갔으면 일일 카운터 초기화
                reset_performed = self._reset_daily_if_needed()

                # Reset이 발생했으면 즉시 저장하여 on-disk 상태와 동기화
                if reset_performed:
                    self._save_state()

                self._logger.debug(f"Loaded state from {self._state_file}")
            except (json.JSONDecodeError, FileNotFoundError) as exc:
                self._logger.error(f"Failed to load state file: {exc}")
                self._state = {
                    "last_bot_response": None,
                    "last_capacity_alert": None,
                    "last_reset_date": None,
                    "today_alert_count": 0,
                    "d2_d3_alerts_today": [],
                    "todo_alert_history": []
                }
                # Restore valid on-disk state immediately
                self._save_state()
                self._logger.info("Restored default state after load failure")

    def _save_state(self) -> None:
        """현재 상태를 파일에 저장합니다 (thread-safe, atomic write)."""
        with self._lock:
            try:
                self._atomic_write(self._state)
                self._logger.debug(f"Saved state to {self._state_file}")
            except Exception as exc:
                self._logger.error(f"Failed to save state: {exc}")

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        """
        원자적 쓰기로 파일 손상 방지.

        임시 파일에 쓴 후 os.replace로 원자적으로 교체합니다.
        """
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self._state_file.parent,
            prefix=".state_",
            suffix=".tmp"
        )
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk

            # Atomic replace
            os.replace(temp_path, self._state_file)
            # Secure permissions
            os.chmod(self._state_file, 0o600)

            # Fsync directory for durability (POSIX)
            try:
                dir_fd = os.open(
                    self._state_file.parent,
                    os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0)
                )
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except (OSError, AttributeError):
                pass  # Best-effort directory fsync
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise

    def _reset_daily_if_needed(self) -> bool:
        """
        자정이 지났으면 일일 카운터를 초기화합니다.

        last_reset_date 기준으로 날짜가 바뀌면 초기화:
        - today_alert_count = 0
        - d2_d3_alerts_today = []
        - last_reset_date = 오늘 날짜

        Returns:
            True if reset was performed, False otherwise
        """
        now = datetime.now(KST)
        today_str = now.date().isoformat()

        # 마지막 리셋 날짜 확인
        last_reset = self._state.get("last_reset_date")

        if last_reset != today_str:
            # 날짜가 바뀌었으므로 초기화
            self._logger.info(f"New day detected (last_reset: {last_reset}, today: {today_str}), resetting daily counters")
            self._state["today_alert_count"] = 0
            self._state["d2_d3_alerts_today"] = []
            self._state["last_reset_date"] = today_str
            return True
        else:
            # 오늘이 아닌 D-2, D-3 알림 필터링 (방어 코드)
            d2_d3_alerts = self._state.get("d2_d3_alerts_today", [])
            if d2_d3_alerts:
                self._state["d2_d3_alerts_today"] = [
                    alert for alert in d2_d3_alerts
                    if self._is_today(alert.get("alerted_at"))
                ]
            return False

    def _parse_iso_datetime(self, timestamp_str: str) -> Optional[datetime]:
        """
        ISO 8601 타임스탬프를 파싱합니다.

        'Z' suffix를 '+00:00'로 변환하여 Python 3.10 호환성 확보
        """
        if not timestamp_str:
            return None
        try:
            # Handle 'Z' suffix (UTC indicator)
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(timestamp_str)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=KST)
            return dt
        except (ValueError, TypeError):
            return None

    def _is_today(self, timestamp_str: Optional[str]) -> bool:
        """타임스탬프가 오늘인지 확인합니다."""
        dt = self._parse_iso_datetime(timestamp_str)
        if not dt:
            return False
        now = datetime.now(KST)
        return dt.date() == now.date()

    # ========== 상태 조회 메서드 ==========

    def get_last_bot_response(self) -> Optional[datetime]:
        """마지막 봇 응답 시간을 반환합니다."""
        with self._lock:
            timestamp_str = self._state.get("last_bot_response")
        return self._parse_iso_datetime(timestamp_str)

    def get_last_capacity_alert(self) -> Optional[datetime]:
        """마지막 용량 분석 알림 시간을 반환합니다."""
        with self._lock:
            timestamp_str = self._state.get("last_capacity_alert")
        return self._parse_iso_datetime(timestamp_str)

    def get_today_alert_count(self) -> int:
        """오늘 발송한 알림 수를 반환합니다."""
        with self._lock:
            return self._state.get("today_alert_count", 0)

    def get_d2_d3_alerts_today(self) -> List[Dict[str, Any]]:
        """오늘 발송한 D-2, D-3 알림 목록을 반환합니다 (defensive copy)."""
        with self._lock:
            return list(self._state.get("d2_d3_alerts_today", []))

    def is_todo_alerted_today(self, todo_title: str, due_date: str) -> bool:
        """
        특정 TODO에 대해 오늘 이미 알림을 보냈는지 확인합니다.

        Args:
            todo_title: TODO 제목
            due_date: 마감일 (ISO 8601 형식)

        Returns:
            오늘 이미 알림을 보냈으면 True, 아니면 False
        """
        alerts = self.get_d2_d3_alerts_today()
        for alert in alerts:
            if alert.get("todo_title") == todo_title and alert.get("due_date") == due_date:
                return True
        return False

    # ========== 상태 업데이트 메서드 ==========

    def update_bot_response(self, timestamp: Optional[datetime] = None) -> None:
        """
        마지막 봇 응답 시간을 업데이트합니다.

        Args:
            timestamp: 업데이트할 시간 (None이면 현재 시간)
        """
        if timestamp is None:
            timestamp = datetime.now(KST)

        with self._lock:
            self._reset_daily_if_needed()  # Ensure daily counters reset across midnight
            self._state["last_bot_response"] = timestamp.isoformat()
            self._save_state()
        self._logger.debug(f"Updated last_bot_response: {timestamp}")

    def update_capacity_alert(self, timestamp: Optional[datetime] = None) -> None:
        """
        마지막 용량 분석 알림 시간을 업데이트합니다.

        Args:
            timestamp: 업데이트할 시간 (None이면 현재 시간)
        """
        if timestamp is None:
            timestamp = datetime.now(KST)

        with self._lock:
            self._reset_daily_if_needed()  # Ensure daily counters reset across midnight
            self._state["last_capacity_alert"] = timestamp.isoformat()
            self._state["today_alert_count"] = self._state.get("today_alert_count", 0) + 1
            self._save_state()
        self._logger.debug(f"Updated last_capacity_alert: {timestamp}")

    def add_d2_d3_alert(self, todo_title: str, due_date: str) -> None:
        """
        D-2, D-3 알림을 발송했음을 기록합니다.

        Args:
            todo_title: TODO 제목
            due_date: 마감일 (ISO 8601 형식)
        """
        now = datetime.now(KST)
        alert_record = {
            "todo_title": todo_title,
            "due_date": due_date,
            "alerted_at": now.isoformat()
        }

        with self._lock:
            self._reset_daily_if_needed()  # Ensure daily counters reset across midnight
            alerts = self._state.get("d2_d3_alerts_today", [])
            alerts.append(alert_record)
            self._state["d2_d3_alerts_today"] = alerts
            self._state["today_alert_count"] = self._state.get("today_alert_count", 0) + 1
            self._save_state()
        self._logger.debug(f"Added D-2/D-3 alert: {todo_title} (due: {due_date})")

    def add_todo_alert_history(self, todo_id: str, alert_type: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        TODO 알림 히스토리를 추가합니다.

        Args:
            todo_id: TODO ID
            alert_type: 알림 유형 (capacity_analysis, d2_advance, d3_advance)
            metadata: 추가 메타데이터
        """
        now = datetime.now(KST)
        history_record = {
            "todo_id": todo_id,
            "alert_type": alert_type,
            "timestamp": now.isoformat(),
            "metadata": metadata or {}
        }

        with self._lock:
            self._reset_daily_if_needed()  # Ensure daily counters reset across midnight
            history = self._state.get("todo_alert_history", [])
            history.append(history_record)

            # 히스토리가 너무 길면 오래된 것 삭제 (최대 1000개)
            if len(history) > 1000:
                history = history[-1000:]

            self._state["todo_alert_history"] = history
            self._save_state()
        self._logger.debug(f"Added alert history: {alert_type} for TODO {todo_id}")

    def cleanup_old_history(self, days: int = 30) -> int:
        """
        오래된 히스토리를 정리합니다.

        Args:
            days: 보관 기간 (일)

        Returns:
            삭제된 레코드 수
        """
        now = datetime.now(KST)
        # Fix: Use timedelta instead of incorrect day arithmetic
        cutoff = now - timedelta(days=days)
        cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)

        with self._lock:
            history = self._state.get("todo_alert_history", [])
            old_count = len(history)

            # cutoff 이후의 레코드만 유지
            cleaned = []
            for record in history:
                timestamp_str = record.get("timestamp")
                dt = self._parse_iso_datetime(timestamp_str)
                if dt and dt >= cutoff:
                    cleaned.append(record)

            self._state["todo_alert_history"] = cleaned
            self._save_state()

            deleted_count = old_count - len(cleaned)
            if deleted_count > 0:
                self._logger.info(f"Cleaned up {deleted_count} old history records (older than {days} days)")

            return deleted_count
