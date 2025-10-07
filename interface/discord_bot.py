"""Discord bot interface for the Personal AI Assistant with CrewAI."""

from __future__ import annotations

import asyncio
import os
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from datetime import datetime
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


def _cleanup_temp_files(logger: logging.Logger, temp_dir_path: str) -> None:
    """
    세션 시작 시 임시 첨부 파일 디렉토리를 정리합니다.

    Args:
        logger: 로거 인스턴스
        temp_dir_path: 임시 파일 디렉토리 경로 (Fix #14)
    """
    temp_dir = Path(temp_dir_path)

    if not temp_dir.exists():
        logger.debug("Temp directory does not exist, skipping cleanup")
        return

    try:
        deleted_count = 0
        for file_path in temp_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()
                deleted_count += 1

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} temporary file(s) from previous session")
        else:
            logger.debug("No temporary files to clean up")

    except Exception as exc:
        logger.warning(f"Failed to clean up temporary files: {exc}")


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

    # 세션 시작 시 임시 파일 정리 (Fix #14)
    _cleanup_temp_files(logger, config.temp_attachments_dir)

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


async def _save_attachments(
    attachments: List["discord.Attachment"],
    logger: logging.Logger,
    temp_dir_path: str,
) -> List[Dict[str, Any]]:
    """
    Discord 메시지 첨부 파일을 임시 저장소에 저장하고 메타데이터 반환.

    Args:
        attachments: Discord 첨부 파일 리스트
        logger: 로거 인스턴스
        temp_dir_path: 임시 파일 디렉토리 경로 (Fix #14)

    Returns:
        파일 메타데이터 리스트 (각 항목: {filename, original_filename, filepath, content_type, size})
    """
    # 임시 저장 디렉토리 생성
    temp_dir = Path(temp_dir_path)
    temp_dir.mkdir(parents=True, exist_ok=True)

    file_metadata = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for idx, attachment in enumerate(attachments):
        try:
            # 파일 확장자 추출
            original_name = attachment.filename
            file_ext = Path(original_name).suffix

            # 타임스탬프 기반 파일명 생성
            new_filename = f"{timestamp}_{idx}{file_ext}"
            file_path = temp_dir / new_filename

            # 파일 다운로드 및 저장
            await attachment.save(file_path)

            # 메타데이터 수집
            metadata = {
                "filename": new_filename,
                "original_filename": original_name,
                "filepath": str(file_path),
                "content_type": attachment.content_type or "unknown",
                "size": attachment.size,
            }
            file_metadata.append(metadata)

            logger.info(f"Saved attachment: {original_name} → {new_filename} ({attachment.size} bytes)")

        except Exception as exc:
            logger.error(f"Failed to save attachment {attachment.filename}: {exc}")
            continue

    return file_metadata


async def _wait_for_follow_up(
    client: "discord.Client",
    initial_message: "discord.Message",
    wait_seconds: int = 10,
    logger: Optional[logging.Logger] = None,
) -> List[str]:
    """
    파일 첨부 후 사용자의 후속 메시지를 대기하고 수집.

    Args:
        client: Discord 클라이언트
        initial_message: 초기 메시지 (파일이 첨부된 메시지)
        wait_seconds: 대기 시간 (초)
        logger: 로거 인스턴스

    Returns:
        후속 메시지 내용 리스트
    """
    if logger:
        logger.info(f"Waiting {wait_seconds} seconds for follow-up messages...")

    follow_up_messages = []

    def check(msg: "discord.Message") -> bool:
        """같은 채널, 같은 사용자의 메시지인지 확인"""
        return (
            msg.channel.id == initial_message.channel.id
            and msg.author.id == initial_message.author.id
            and not msg.author.bot
        )

    try:
        # wait_seconds 동안 메시지 수집
        end_time = asyncio.get_event_loop().time() + wait_seconds

        while asyncio.get_event_loop().time() < end_time:
            remaining = end_time - asyncio.get_event_loop().time()
            if remaining <= 0:
                break

            try:
                message = await client.wait_for("message", check=check, timeout=remaining)
                content = message.content.strip()
                if content:
                    follow_up_messages.append(content)
                    if logger:
                        logger.debug(f"Collected follow-up message: {content[:50]}...")
            except asyncio.TimeoutError:
                # 타임아웃은 정상 종료 조건
                break

    except Exception as exc:
        if logger:
            logger.error(f"Error while waiting for follow-up messages: {exc}")

    if logger:
        logger.info(f"Collected {len(follow_up_messages)} follow-up message(s)")

    return follow_up_messages


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
        has_attachments = len(message.attachments) > 0

        # 텍스트 메시지도 없고 첨부파일도 없으면 무시
        if not content and not has_attachments:
            return

        # 파일 첨부가 있는 경우 처리
        file_metadata: List[Dict[str, Any]] = []
        if has_attachments:
            logger.info(f"Detected {len(message.attachments)} attachment(s)")
            file_metadata = await _save_attachments(
                message.attachments, logger, config.temp_attachments_dir
            )

            # 10초 대기하여 후속 메시지 수집
            follow_up_messages = await _wait_for_follow_up(
                client=client,
                initial_message=message,
                wait_seconds=10,
                logger=logger,
            )

            # 후속 메시지를 초기 메시지에 병합
            if follow_up_messages:
                all_messages = [content] + follow_up_messages if content else follow_up_messages
                content = "\n".join(all_messages)
                logger.info(f"Combined {len(all_messages)} message(s) for processing")

        # CrewAI 실행 준비
        async with message.channel.typing():
            try:
                # 파일 메타데이터가 있으면 dict 형태로 전달, 없으면 string 전달
                if file_metadata:
                    crew_input: Union[str, Dict[str, Any]] = {
                        "user_input": content or "첨부된 파일을 분석해주세요.",
                        "file_metadata": file_metadata,
                    }
                    logger.info(f"Passing multimodal input: {len(file_metadata)} file(s)")
                else:
                    crew_input = content

                # CrewAI는 동기 실행이므로 asyncio.to_thread 사용
                result = await asyncio.to_thread(crew.kickoff, crew_input)

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