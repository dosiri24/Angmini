"""Command-line interface for the Personal AI Assistant."""

from __future__ import annotations

from typing import Iterable

from ai.core.config import Config
from ai.core.exceptions import EngineError
from ai.core.logger import get_logger

_EXIT_COMMANDS: tuple[str, ...] = ("exit", "quit", "종료")


def run(config: Config) -> None:
    """Launch a simple interactive CLI session."""
    logger = get_logger(__name__)
    logger.info("Starting CLI interface (default interface=%s)", config.default_interface)
    print("Personal AI Assistant CLI입니다. 종료하려면 'exit'를 입력하세요.")
    _interactive_loop(_EXIT_COMMANDS)
    print("다음에 또 만나요!")


def _interactive_loop(exit_commands: Iterable[str]) -> None:
    normalized = {cmd.lower() for cmd in exit_commands}
    while True:
        try:
            user_input = input("assistant> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\n사용자 요청으로 종료합니다.")
            break

        if not user_input:
            continue

        if user_input.lower() in normalized:
            break

        raise EngineError("LLM API 연동 전이라 명령을 처리할 수 없습니다.")
