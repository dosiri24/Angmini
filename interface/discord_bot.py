"""Discord bot interface for the Personal AI Assistant with CrewAI."""

from __future__ import annotations

import asyncio
from typing import Optional
import logging

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
from ai.memory.factory import create_memory_service
from ai.ai_brain import AIBrain
from ai.crew import AngminiCrew


def run_bot(config: Config) -> None:
    """Start the Discord bot with CrewAI integration."""
    if _IMPORT_ERROR is not None or discord is None:
        raise InterfaceError(
            "discord.py 패키지가 설치되어 있지 않습니다. 'pip install discord.py' 후 다시 시도하세요."
        ) from _IMPORT_ERROR

    token = _coerce_token(config.discord_bot_token)
    intents = discord.Intents.default()
    intents.message_content = True

    logger = get_logger(__name__)
    logger.info("Starting Discord bot with CrewAI")

    # AI Brain 초기화
    try:
        ai_brain = AIBrain(config)
        logger.info("AI Brain initialized")
    except EngineError as exc:
        logger.error("Failed to initialize AIBrain: %s", exc)
        raise InterfaceError(str(exc)) from exc

    # 메모리 서비스 초기화
    try:
        memory_service = create_memory_service()
        logger.info("Memory service initialized")
    except Exception as exc:
        logger.warning("Failed to initialize memory service: %s", exc)
        memory_service = None

    # CrewAI 초기화
    try:
        crew = AngminiCrew(
            ai_brain=ai_brain,
            memory_service=memory_service,
            config=config,
            verbose=False  # Discord에서는 verbose 비활성화
        )
        logger.info("AngminiCrew initialized")
    except Exception as exc:
        logger.error("Failed to initialize AngminiCrew: %s", exc)
        raise InterfaceError(f"CrewAI를 초기화하지 못했습니다: {exc}") from exc

    client = _build_client(intents, crew, config)

    try:
        client.run(token)
    except discord.LoginFailure as exc:  # pragma: no cover - runtime error from Discord
        raise InterfaceError("Discord 봇 로그인에 실패했습니다. 토큰을 다시 확인해주세요.") from exc
    except Exception as exc:  # pragma: no cover - bubble up unexpected failures
        raise InterfaceError("Discord 봇 실행 중 알 수 없는 오류가 발생했습니다.") from exc


def _build_client(
    intents: "discord.Intents",
    crew: AngminiCrew,
    config: Config,
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
                # CrewAI는 동기 실행이므로 asyncio.to_thread 사용
                result = await asyncio.to_thread(crew.kickoff, content)

                # 결과 포맷팅
                if result:
                    response = f"🤖 Angmini: {result}"
                else:
                    response = "⚠️ 결과를 생성하지 못했습니다."

            except EngineError as exc:
                logger.error("Goal execution failed: %s", exc)
                response = f"⚠️ 작업을 완료하지 못했어요: {exc}"
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.exception("Unexpected error while handling Discord message")
                response = "⚠️ 알 수 없는 오류가 발생했습니다. 로그를 확인해 주세요."

        await message.reply(_truncate_for_discord(response))

    return client


def _coerce_token(token: Optional[str]) -> str:
    if not token or not token.strip():
        raise InterfaceError("Discord 봇 토큰이 설정되지 않았습니다. .env 파일을 확인하세요.")
    return token.strip()


def _truncate_for_discord(message: str, limit: int = 1800) -> str:
    if len(message) <= limit:
        return message
    return message[:limit] + "\n... (메시지를 줄였어요)"