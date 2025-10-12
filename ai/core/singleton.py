"""Singleton pattern for ensuring only one instance of the application runs."""

from __future__ import annotations

import os
import signal
import atexit
from pathlib import Path
from typing import Optional

from ai.core.logger import get_logger

logger = get_logger(__name__)


class SingletonGuard:
    """
    PID 파일 기반 싱글톤 패턴 구현.

    Discord 봇이나 CLI가 시작할 때 이미 실행 중인 인스턴스가 있으면
    기존 인스턴스를 종료하고 새 인스턴스를 시작합니다.
    """

    def __init__(self, pid_file_name: str = ".angmini.pid"):
        """
        Initialize the singleton guard.

        Args:
            pid_file_name: PID 파일 이름 (프로젝트 루트에 생성됨)
        """
        # 프로젝트 루트 디렉토리 (main.py가 있는 위치)
        project_root = Path(__file__).parent.parent.parent
        self.pid_file = project_root / pid_file_name
        self.current_pid = os.getpid()

    def acquire(self) -> bool:
        """
        싱글톤 잠금 획득.

        이미 실행 중인 인스턴스가 있으면 종료하고 새 인스턴스를 시작합니다.

        Returns:
            True if singleton lock acquired successfully
        """
        existing_pid = self._read_pid_file()

        if existing_pid:
            if self._is_process_running(existing_pid):
                logger.warning(f"기존 인스턴스 발견 (PID: {existing_pid}). 종료합니다...")
                print(f"⚠️  기존 Angmini 인스턴스 발견 (PID: {existing_pid})")
                print("   기존 인스턴스를 종료하고 새로 시작합니다...")

                try:
                    os.kill(existing_pid, signal.SIGTERM)
                    logger.info(f"기존 프로세스 종료 완료: PID {existing_pid}")
                    print(f"✅ 기존 인스턴스 종료 완료 (PID: {existing_pid})")
                except ProcessLookupError:
                    logger.warning(f"PID {existing_pid}는 이미 종료되었습니다")
                except PermissionError:
                    logger.error(f"PID {existing_pid} 종료 권한이 없습니다")
                    print(f"❌ 기존 인스턴스 종료 실패 (권한 부족)")
                    return False
            else:
                # PID 파일은 있지만 프로세스가 없는 경우 (비정상 종료)
                logger.warning(f"PID 파일은 있지만 프로세스 없음 (PID: {existing_pid}). 삭제합니다.")
                self._remove_pid_file()

        # 새 PID 파일 생성
        self._write_pid_file()

        # 종료 시 PID 파일 자동 삭제
        atexit.register(self.release)

        logger.info(f"싱글톤 잠금 획득 완료: PID {self.current_pid}")
        return True

    def release(self) -> None:
        """싱글톤 잠금 해제 및 PID 파일 삭제."""
        self._remove_pid_file()
        logger.info(f"싱글톤 잠금 해제: PID {self.current_pid}")

    def _read_pid_file(self) -> Optional[int]:
        """PID 파일에서 PID 읽기."""
        if not self.pid_file.exists():
            return None

        try:
            pid_str = self.pid_file.read_text().strip()
            return int(pid_str)
        except (ValueError, OSError) as e:
            logger.warning(f"PID 파일 읽기 실패: {e}")
            return None

    def _write_pid_file(self) -> None:
        """현재 프로세스의 PID를 파일에 저장."""
        try:
            self.pid_file.write_text(str(self.current_pid))
            logger.debug(f"PID 파일 생성: {self.pid_file}")
        except OSError as e:
            logger.error(f"PID 파일 생성 실패: {e}")

    def _remove_pid_file(self) -> None:
        """PID 파일 삭제."""
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
                logger.debug(f"PID 파일 삭제: {self.pid_file}")
            except OSError as e:
                logger.warning(f"PID 파일 삭제 실패: {e}")

    @staticmethod
    def _is_process_running(pid: int) -> bool:
        """
        프로세스가 실행 중인지 확인.

        Args:
            pid: 확인할 프로세스 ID

        Returns:
            True if process is running
        """
        try:
            # Signal 0은 프로세스 존재 여부만 확인 (실제 시그널 전송 안 함)
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # 프로세스는 존재하지만 권한이 없는 경우
            # (다른 사용자의 프로세스)
            return True
