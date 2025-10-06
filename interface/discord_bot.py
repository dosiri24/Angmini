"""Discord bot interface for the Personal AI Assistant with CrewAI."""

from __future__ import annotations

import asyncio
import os
from typing import Optional
import logging

try:
    import discord
    import certifi
except ImportError as exc:  # pragma: no cover - optional dependency
    discord = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from ai.core.config import Config
from ai.core.exceptions import EngineError, InterfaceError
from ai.core.logger import get_logger
from ai.core.singleton import SingletonGuard
from ai.memory.factory import create_memory_service
from ai.ai_brain import AIBrain
from ai.crew import AngminiCrew
from ai.proactive import ProactiveScheduler


def run_bot(config: Config) -> None:
    """Start the Discord bot with CrewAI integration."""
    if _IMPORT_ERROR is not None or discord is None:
        raise InterfaceError(
            "discord.py 패키지가 설치되어 있지 않습니다. 'pip install discord.py' 후 다시 시도하세요."
        ) from _IMPORT_ERROR

    # 싱글톤 패턴: 중복 실행 방지
    singleton = SingletonGuard(pid_file_name=".angmini_discord.pid")
    if not singleton.acquire():
        raise InterfaceError("Discord 봇 싱글톤 잠금 획득 실패. 이미 실행 중인 인스턴스가 있습니다.")

    # Set SSL certificate path for aiohttp
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

    token = _coerce_token(config.discord_bot_token)
    intents = discord.Intents.default()
    intents.message_content = True

    logger = get_logger(__name__)
    logger.info("Starting Discord bot with CrewAI")
    logger.debug("SSL certificate path: %s", certifi.where())

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

    # 능동 알림 스케줄러 초기화 (Discord 전용)
    scheduler: Optional[ProactiveScheduler] = None
    try:
        # 스케줄러는 Discord 전송 콜백과 MemoryService와 함께 초기화
        # 실제 Discord 채널 객체는 클라이언트 빌드 후 설정
        scheduler = ProactiveScheduler(memory_service=memory_service)
        logger.info("Proactive scheduler initialized with MemoryService (will start after bot ready)")
    except Exception as exc:
        logger.warning("Failed to initialize proactive scheduler: %s", exc)
        # 스케줄러 실패는 봇 시작을 막지 않음

    client = _build_client(intents, crew, config, scheduler)

    try:
        client.run(token)
    except discord.LoginFailure as exc:  # pragma: no cover - runtime error from Discord
        logger.exception("Discord login failure")
        raise InterfaceError("Discord 봇 로그인에 실패했습니다. 토큰을 다시 확인해주세요.") from exc
    except Exception as exc:  # pragma: no cover - bubble up unexpected failures
        logger.exception("Unexpected error during Discord bot execution")
        raise InterfaceError(f"Discord 봇 실행 중 오류가 발생했습니다: {exc}") from exc


def _build_client(
    intents: "discord.Intents",
    crew: AngminiCrew,
    config: Config,
    scheduler: Optional[ProactiveScheduler] = None,
) -> "discord.Client":
    # SSL certificates are configured via environment variables (SSL_CERT_FILE)
    # in run_bot() before creating the client
    client = discord.Client(intents=intents)
    logger = get_logger(__name__)

    # 능동 알림 전송용 채널 ID (환경변수에서 읽기)
    proactive_channel_id_str = os.getenv("DISCORD_PROACTIVE_CHANNEL_ID")
    proactive_channel_id: Optional[int] = None
    if proactive_channel_id_str:
        try:
            proactive_channel_id = int(proactive_channel_id_str)
        except ValueError:
            logger.warning(f"Invalid DISCORD_PROACTIVE_CHANNEL_ID: {proactive_channel_id_str}")

    @client.event
    async def on_ready() -> None:  # type: ignore[misc]
        logger.info("Discord 봇이 %s 계정으로 로그인했습니다.", client.user)

        # 능동 알림 스케줄러 시작 (Discord 준비 완료 후)
        if scheduler and proactive_channel_id:
            # Discord 메시지 전송 콜백 설정
            def send_to_channel(message: str) -> None:
                """능동 알림을 Discord 채널에 전송합니다."""
                try:
                    channel = client.get_channel(proactive_channel_id)
                    if channel and hasattr(channel, 'send'):
                        # Discord 메시지 길이 제한 (2000자) 적용
                        truncated_message = _truncate_for_discord(message)

                        # asyncio.run_coroutine_threadsafe를 사용하여 백그라운드 스레드에서 비동기 함수 호출
                        future = asyncio.run_coroutine_threadsafe(
                            channel.send(
                                truncated_message,
                                allowed_mentions=discord.AllowedMentions.none()  # type: ignore[union-attr]
                            ),
                            client.loop
                        )
                        # 결과 대기 (타임아웃 10초)
                        future.result(timeout=10)
                        logger.debug(f"Sent proactive alert to channel {proactive_channel_id}")
                    else:
                        logger.error(f"Channel {proactive_channel_id} not found or not a text channel")
                except Exception as exc:
                    logger.exception(f"Failed to send proactive alert: {exc}")

            # 스케줄러에 콜백 설정
            scheduler._discord_send = send_to_channel

            # 스케줄러 시작
            scheduler.start()
            logger.info(f"Proactive scheduler started (target channel: {proactive_channel_id})")
        elif scheduler:
            logger.warning("Proactive scheduler not started: DISCORD_PROACTIVE_CHANNEL_ID not set")
        else:
            logger.info("Proactive scheduler disabled")

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

        await message.reply(
            _truncate_for_discord(response),
            allowed_mentions=discord.AllowedMentions.none()
        )

        # 능동 알림 스케줄러에 봇 응답 시간 업데이트
        if scheduler:
            scheduler.on_bot_response()

    return client


def _coerce_token(token: Optional[str]) -> str:
    if not token or not token.strip():
        raise InterfaceError("Discord 봇 토큰이 설정되지 않았습니다. .env 파일을 확인하세요.")
    return token.strip()


def _truncate_for_discord(message: str, limit: int = 1800) -> str:
    if len(message) <= limit:
        return message
    return message[:limit] + "\n... (메시지를 줄였어요)"