"""
Discord Bot 테스트 모듈.

Why: Discord Bot의 핵심 로직(메시지 처리, 응답 포맷팅)을 검증한다.
실제 Discord API 호출은 모킹하여 단위 테스트로 진행한다.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
import sys
import os

# 테스트 대상
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot import split_message


class TestMessageHandler:
    """on_message 핸들러 테스트."""

    def test_ignore_bot_message(self):
        """봇 자신의 메시지는 무시해야 한다."""
        # Given: 봇이 보낸 메시지
        # When: on_message 처리
        # Then: 무시됨 (Agent 호출 안 함)
        pass  # TODO: bot.py 구현 후 활성화

    def test_ignore_other_channel(self):
        """지정된 채널이 아닌 메시지는 무시해야 한다."""
        # Given: 다른 채널의 메시지
        # When: on_message 처리
        # Then: 무시됨
        pass  # TODO: bot.py 구현 후 활성화

    def test_process_message_in_target_channel(self):
        """지정된 채널의 메시지는 Agent로 처리해야 한다."""
        # Given: 지정된 채널의 사용자 메시지
        # When: on_message 처리
        # Then: Agent.process_message() 호출됨
        pass  # TODO: bot.py 구현 후 활성화


class TestResponseFormatter:
    """응답 포맷팅 테스트."""

    def test_split_long_message(self):
        """2000자 초과 메시지는 분할해야 한다."""
        # Discord 메시지 제한: 2000자
        # Given: 2500자 응답
        # When: 포맷팅
        # Then: 2개 이상의 메시지로 분할
        long_text = "A" * 2500
        chunks = split_message(long_text)

        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 2000

    def test_preserve_short_message(self):
        """2000자 이하 메시지는 그대로 유지."""
        short_text = "짧은 메시지"
        chunks = split_message(short_text)

        assert len(chunks) == 1
        assert chunks[0] == short_text

    def test_split_at_newline(self):
        """긴 메시지는 줄바꿈에서 분할해야 한다."""
        # 1900자 + 줄바꿈 + 200자
        text = "A" * 1900 + "\n" + "B" * 200
        chunks = split_message(text)

        assert len(chunks) == 2
        assert chunks[0] == "A" * 1900
        assert chunks[1] == "B" * 200


class TestSlashCommands:
    """슬래시 커맨드 테스트."""

    def test_today_command_returns_schedules(self):
        """
        /today 커맨드는 오늘 일정을 반환해야 한다.

        Why: 빠른 조회를 위한 슬래시 커맨드 - CLAUDE.md 예외 허용
        """
        # Given: 오늘 일정이 2개 있음
        # When: /today 실행
        # Then: 2개 일정 목록 응답
        pass  # TODO: bot.py 구현 후 활성화

    def test_tomorrow_command_returns_schedules(self):
        """/tomorrow 커맨드는 내일 일정을 반환해야 한다."""
        pass  # TODO: bot.py 구현 후 활성화

    def test_tasks_command_returns_upcoming(self):
        """/tasks 커맨드는 다가오는 할일을 반환해야 한다."""
        pass  # TODO: bot.py 구현 후 활성화

    def test_done_command_marks_complete(self):
        """/done <id> 커맨드는 일정을 완료 처리해야 한다."""
        pass  # TODO: bot.py 구현 후 활성화


class TestErrorHandling:
    """에러 핸들링 테스트."""

    def test_agent_error_returns_friendly_message(self):
        """Agent 에러 시 사용자 친화적 메시지를 반환해야 한다."""
        # Given: Agent가 예외를 발생시킴
        # When: 메시지 처리
        # Then: "문제가 발생했어요" 형태의 메시지
        pass  # TODO: bot.py 구현 후 활성화
