"""Command-line interface for the Personal AI Assistant."""

from __future__ import annotations

from typing import Iterable

import logging

from ai.core.config import Config
from ai.core.exceptions import EngineError
from ai.core.logger import get_logger
from ai.react_engine.models import StepCompletedEvent
from ai.react_engine.runtime import GoalExecutorFactory
from mcp import create_default_tool_manager
from .summary import format_execution_summary

_EXIT_COMMANDS: tuple[str, ...] = ("exit", "quit", "종료")


def run(config: Config) -> None:
    """Launch a simple interactive CLI session."""
    logger = get_logger(__name__)
    logger.info("Starting CLI interface (default interface=%s)", config.default_interface)
    tool_manager = create_default_tool_manager()
    logger.debug("Registered tools: %s", list(tool_manager.registered_names()))

    try:
        executor_factory = GoalExecutorFactory(config, tool_manager)
    except EngineError as exc:
        logger.error("Failed to initialise GoalExecutor: %s", exc)
        print(f"⚠️ 엔진을 초기화하지 못했습니다: {exc}")
        return

    print("Personal AI Assistant CLI입니다. 종료하려면 'exit'를 입력하세요.")
    _interactive_loop(_EXIT_COMMANDS, logger, executor_factory)
    print("다음에 또 만나요!")


def _interactive_loop(
    exit_commands: Iterable[str],
    logger: logging.Logger,
    executor_factory: GoalExecutorFactory,
) -> None:
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

        try:
            executor = executor_factory.create()
            context = executor.run(user_input)
        except EngineError as exc:
            logger.error("Goal execution failed: %s", exc)
            print(f"⚠️ 작업을 완료하지 못했어요: {exc}")
            continue
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Unexpected error while processing CLI command")
            print("⚠️ 알 수 없는 오류가 발생했습니다. 로그를 확인해 주세요.")
            continue

        root_level = logging.getLogger().getEffectiveLevel()
        if root_level <= logging.WARNING:
            print(format_execution_summary(context))
            printed_summary = True
        else:
            printed_summary = False

        message = _extract_direct_message(context)
        if message:
            if printed_summary:
                print()
            print(f"assistant 응답: {message}")

        executor_factory.record_turn(user_input, message)


def _extract_direct_message(context) -> str | None:
    metadata_message = context.metadata.get("final_message")
    if isinstance(metadata_message, str) and metadata_message.strip():
        return metadata_message.strip()

    for event in reversed(context.events):
        if isinstance(event, StepCompletedEvent):
            data = getattr(event, "data", None)
            if isinstance(data, dict) and data.get("type") == "direct_response":
                message = data.get("message")
                if isinstance(message, str) and message.strip():
                    return message.strip()
    return None
