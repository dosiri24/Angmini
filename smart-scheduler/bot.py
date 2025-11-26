"""
Discord Bot 모듈 - 앙미니(Angmini) 일정 관리 봇.

Why: Discord를 통해 사용자와 상호작용하는 인터페이스를 제공한다.
자연어 처리는 100% Agent(LLM)에게 위임하고, 봇은 메시지 라우팅만 담당한다.
(CLAUDE.md 순수 LLM 원칙)
"""

import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import config, ConfigError
from agent import Agent
from database import Database

# 로깅 설정
logger = logging.getLogger(__name__)

# Discord 메시지 최대 길이
MAX_MESSAGE_LENGTH = 2000


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """
    긴 메시지를 Discord 제한에 맞게 분할한다.

    Why: Discord 메시지는 2000자 제한이 있으므로 긴 응답은 분할 필요.

    Args:
        text: 분할할 텍스트
        max_length: 최대 길이 (기본 2000)

    Returns:
        분할된 메시지 리스트
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break

        # 줄바꿈 기준으로 자르기 시도
        split_pos = text.rfind("\n", 0, max_length)
        if split_pos == -1:
            # 줄바꿈이 없으면 공백 기준
            split_pos = text.rfind(" ", 0, max_length)
        if split_pos == -1:
            # 공백도 없으면 강제 분할
            split_pos = max_length

        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip()

    return chunks


class AngminiBot(commands.Bot):
    """
    앙미니 Discord Bot.

    Why: commands.Bot을 상속하여 슬래시 커맨드와 메시지 이벤트를 통합 관리.
    """

    def __init__(self, agent: Agent, target_channel_id: Optional[str] = None):
        """
        Args:
            agent: LLM Agent 인스턴스
            target_channel_id: 응답할 채널 ID (None이면 모든 채널)
        """
        # Intents 설정 - 메시지 내용 읽기 권한 필요
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        self._agent = agent
        self._target_channel_id = int(target_channel_id) if target_channel_id else None

        logger.info(f"Bot initialized. Target channel: {self._target_channel_id}")

    async def setup_hook(self) -> None:
        """
        봇 시작 시 호출되는 설정 훅.

        Why: 슬래시 커맨드 동기화를 위해 필요.
        """
        # 슬래시 커맨드 등록
        self._setup_slash_commands()
        await self.tree.sync()
        logger.info("Slash commands synced")

    def _setup_slash_commands(self) -> None:
        """슬래시 커맨드를 등록한다."""

        @self.tree.command(name="today", description="오늘 일정을 조회합니다")
        async def today_command(interaction: discord.Interaction):
            """오늘 일정 조회."""
            await interaction.response.defer()
            response = await self._agent.process_message(
                f"오늘({date.today().isoformat()}) 일정 알려줘"
            )
            await self._send_response(interaction, response)

        @self.tree.command(name="tomorrow", description="내일 일정을 조회합니다")
        async def tomorrow_command(interaction: discord.Interaction):
            """내일 일정 조회."""
            await interaction.response.defer()
            tomorrow = date.today() + timedelta(days=1)
            response = await self._agent.process_message(
                f"내일({tomorrow.isoformat()}) 일정 알려줘"
            )
            await self._send_response(interaction, response)

        @self.tree.command(name="tasks", description="다가오는 일정을 조회합니다")
        async def tasks_command(interaction: discord.Interaction):
            """다가오는 일정 조회."""
            await interaction.response.defer()
            response = await self._agent.process_message(
                "다가오는 일정 7일치 보여줘"
            )
            await self._send_response(interaction, response)

        @self.tree.command(name="done", description="일정을 완료 처리합니다")
        @app_commands.describe(schedule_id="완료할 일정 ID")
        async def done_command(interaction: discord.Interaction, schedule_id: int):
            """일정 완료 처리."""
            await interaction.response.defer()
            response = await self._agent.process_message(
                f"일정 ID {schedule_id}번 완료 처리해줘"
            )
            await self._send_response(interaction, response)

        @self.tree.command(name="help", description="앙미니 사용법을 안내합니다")
        async def help_command(interaction: discord.Interaction):
            """도움말."""
            help_text = """**🐱 앙미니(Angmini) 사용 가이드**

**자연어로 대화하기**
그냥 말하듯이 메시지를 보내면 됩니다!
• "내일 오후 3시에 팀 미팅 추가해줘"
• "이번 주 일정 알려줘"
• "친구 만남 약속 등록해줘"

**빠른 명령어 (슬래시 커맨드)**
• `/today` - 오늘 일정 조회
• `/tomorrow` - 내일 일정 조회
• `/tasks` - 다가오는 7일 일정
• `/done <ID>` - 일정 완료 처리
• `/help` - 이 도움말

**카테고리 자동 분류**
일정 내용을 보고 자동으로 분류해요:
학업 📚 | 약속 🤝 | 개인 🏃 | 업무 💼 | 루틴 🔄 | 기타 📌
"""
            await interaction.response.send_message(help_text)

    async def _send_response(
        self, interaction: discord.Interaction, response: str
    ) -> None:
        """
        응답을 전송한다 (긴 메시지 분할 처리).

        Args:
            interaction: Discord Interaction
            response: 응답 텍스트
        """
        chunks = split_message(response)

        # 첫 번째 청크는 followup으로 전송 (defer 후이므로)
        await interaction.followup.send(chunks[0])

        # 나머지 청크는 추가 메시지로 전송
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)

    async def on_ready(self) -> None:
        """봇이 준비되었을 때 호출된다."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")

        # 상태 메시지 설정
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="일정 요청",
            )
        )

    async def on_message(self, message: discord.Message) -> None:
        """
        메시지 수신 시 호출된다.

        Why: 자연어 메시지를 Agent에게 전달하여 처리한다.
        키워드 파싱 없이 100% LLM이 의도를 파악한다. (CLAUDE.md 원칙)
        """
        # 봇 자신의 메시지 무시
        if message.author == self.user:
            return

        # 봇 멘션 없고, 지정 채널이 아니면 무시
        if self._target_channel_id:
            if message.channel.id != self._target_channel_id:
                # 봇 멘션된 경우에만 다른 채널에서도 응답
                if self.user not in message.mentions:
                    return

        # DM은 처리 (선택적)
        if isinstance(message.channel, discord.DMChannel):
            pass  # DM 허용

        # 타이핑 표시
        async with message.channel.typing():
            try:
                # Agent에게 메시지 처리 위임 (자연어 → 구조화는 LLM이 담당)
                response = await self._agent.process_message(message.content)

                # 응답 전송 (긴 메시지 분할)
                chunks = split_message(response)
                for chunk in chunks:
                    await message.reply(chunk, mention_author=False)

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await message.reply(
                    "죄송해요, 요청을 처리하는 중 문제가 발생했어요. 😅\n"
                    "잠시 후 다시 시도해주세요!",
                    mention_author=False,
                )


def create_bot() -> AngminiBot:
    """
    Bot 인스턴스를 생성한다.

    Why: 팩토리 함수로 분리하여 설정 로드 및 의존성 주입을 명확히 한다.

    Returns:
        설정된 AngminiBot 인스턴스

    Raises:
        ConfigError: 필수 설정이 누락된 경우
    """
    cfg = config()

    # Discord 토큰 검증
    if not cfg.discord_bot_token:
        raise ConfigError(
            "DISCORD_BOT_TOKEN 환경변수가 설정되지 않았습니다. "
            ".env 파일을 확인하세요."
        )

    # Agent 생성
    db = Database(cfg.database_path)
    db.init_schema()
    agent = Agent(db=db)

    # Bot 생성
    bot = AngminiBot(
        agent=agent,
        target_channel_id=cfg.discord_channel_id,
    )

    return bot


async def main() -> None:
    """봇 실행 진입점."""
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting Angmini Bot...")

    try:
        bot = create_bot()
        cfg = config()
        await bot.start(cfg.discord_bot_token)
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except discord.LoginFailure:
        logger.error("Invalid Discord token. Please check DISCORD_BOT_TOKEN.")
        raise
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
