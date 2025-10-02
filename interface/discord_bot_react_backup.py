"""Discord bot interface for the Personal AI Assistant."""

from __future__ import annotations

import asyncio
from typing import Optional

try:
    import discord
except ImportError as exc:  # pragma: no cover - optional dependency
    discord = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from ai.core.config import Config
from ai.core.exceptions import EngineError, InterfaceError
from ai.core.logger import get_logger
from mcp import create_default_tool_manager
from ai.react_engine.runtime import GoalExecutorFactory
from .summary import format_execution_summary


def run_bot(config: Config) -> None:
    """Start the Discord bot, validating configuration beforehand."""
    if _IMPORT_ERROR is not None or discord is None:
        raise InterfaceError(
            "discord.py 패키지가 설치되어 있지 않습니다. 'pip install discord.py' 후 다시 시도하세요."
        ) from _IMPORT_ERROR

    token = _coerce_token(config.discord_bot_token)
    intents = discord.Intents.default()
    intents.message_content = True

    tool_manager = create_default_tool_manager()
    try:
        executor_factory = GoalExecutorFactory(config, tool_manager)
    except EngineError as exc:
        raise InterfaceError(str(exc)) from exc

    client = _build_client(intents, executor_factory)

    logger = get_logger(__name__)
    logger.info("Starting Discord bot")
    logger.debug("Registered tools: %s", list(tool_manager.registered_names()))

    try:
        client.run(token)
    except discord.LoginFailure as exc:  # pragma: no cover - runtime error from Discord
        raise InterfaceError("Discord 봇 로그인에 실패했습니다. 토큰을 다시 확인해주세요.") from exc
    except Exception as exc:  # pragma: no cover - bubble up unexpected failures
        raise InterfaceError("Discord 봇 실행 중 알 수 없는 오류가 발생했습니다.") from exc


def _build_client(
    intents: "discord.Intents",
    executor_factory: GoalExecutorFactory,
) -> "discord.Client":
    client = discord.Client(intents=intents)
    logger = get_logger(__name__)

    @client.event
    async def on_ready() -> None:  # type: ignore[misc]
        logger.info("Discord 봇이 %s 계정으로 로그인했습니다.", client.user)

    @client.event
    async def on_message(message: "discord.Message") -> None:  # type: ignore[misc]
        if message.author.bot:
            return

        content = message.content.strip()
        if not content:
            return

        async with message.channel.typing():
            try:
                context = await asyncio.to_thread(_execute_goal, executor_factory, content)
                summary = format_execution_summary(context)
            except EngineError as exc:
                logger.error("Goal execution failed: %s", exc)
                summary = f"⚠️ 작업을 완료하지 못했어요: {exc}"
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.exception("Unexpected error while handling Discord message")
                summary = "⚠️ 알 수 없는 오류가 발생했습니다. 로그를 확인해 주세요."

        await message.reply(_truncate_for_discord(summary))

    return client


def _coerce_token(token: Optional[str]) -> str:
    if not token or not token.strip():
        raise InterfaceError("Discord 봇 토큰이 설정되지 않았습니다. .env 파일을 확인하세요.")
    return token.strip()


def _execute_goal(executor_factory: GoalExecutorFactory, goal: str):
    executor = executor_factory.create()
    return executor.run(goal)


def _truncate_for_discord(message: str, limit: int = 1800) -> str:
    if len(message) <= limit:
        return message
    return message[:limit] + "\n... (메시지를 줄였어요)"
