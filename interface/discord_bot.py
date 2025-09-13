"""
Discord Bot 인터페이스
Discord에서 사용자와 AI Assistant가 대화할 수 있는 인터페이스를 제공합니다.
"""
import discord
from discord.ext import commands
from ai.core.config import config
from ai.core.logger import logger
from ai.core.exceptions import ConfigurationError

class DiscordBot:
    """
    Discord 봇 인터페이스를 제공하는 클래스입니다.
    Discord 서버에서 사용자의 메시지를 받아 AI에게 전달하고, 응답을 전송하는 역할을 합니다.
    """
    
    def __init__(self):
        """Discord 봇을 초기화합니다."""
        # Rule 1: Design for Extensibility
        # Intents를 명시적으로 설정하여 필요한 권한만 요청하고,
        # 나중에 기능을 추가할 때 쉽게 확장할 수 있도록 합니다.
        intents = discord.Intents.default()
        intents.message_content = True  # 메시지 내용 읽기 권한
        
        # 봇 인스턴스 생성 (command_prefix는 나중에 사용할 슬래시 명령어를 위해 설정)
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        
        # 이벤트 핸들러 등록
        self._setup_events()
        
        logger.info("Discord 봇이 초기화되었습니다.")
    
    def _setup_events(self):
        """봇의 이벤트 핸들러들을 설정합니다."""
        
        @self.bot.event
        async def on_ready():
            """봇이 성공적으로 로그인했을 때 호출되는 이벤트입니다."""
            if self.bot.user:  # 타입 체크 추가
                logger.info(f'{self.bot.user.name}로 로그인했습니다!')
                logger.info(f'봇 ID: {self.bot.user.id}')
                print(f'🤖 {self.bot.user.name}가 준비되었습니다!')
            else:
                logger.error("봇 사용자 정보를 가져올 수 없습니다.")
        
        @self.bot.event
        async def on_message(message):
            """메시지가 전송될 때마다 호출되는 이벤트입니다."""
            # 봇 자신의 메시지는 무시
            if message.author == self.bot.user:
                return
            
            # 봇이 멘션되었거나 DM인 경우에만 응답
            if self.bot.user and (self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel)):
                try:
                    # 사용자 입력에서 봇 멘션 제거
                    user_input = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
                    
                    if not user_input:
                        await message.channel.send("안녕하세요! 무엇을 도와드릴까요?")
                        return
                    
                    logger.info(f"Discord에서 메시지 수신: {message.author.name} - {user_input}")
                    
                    # TODO: 여기에 AI 엔진 연동 로직 추가
                    # 현재는 간단한 응답만 제공
                    response = await self._process_message(user_input, message.author)
                    await message.channel.send(response)
                    
                except Exception as e:
                    logger.error(f"메시지 처리 중 오류 발생: {e}")
                    await message.channel.send("죄송합니다. 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
            
            # 다른 명령어들도 처리할 수 있도록 함
            await self.bot.process_commands(message)
    
    async def _process_message(self, user_input: str, author: discord.User) -> str:
        """
        사용자의 메시지를 처리하고 응답을 생성합니다.
        현재는 간단한 더미 응답을 제공하며, 나중에 AI 엔진과 연동될 예정입니다.
        
        Args:
            user_input (str): 사용자가 입력한 텍스트
            author (discord.User): 메시지를 보낸 사용자
            
        Returns:
            str: AI의 응답 텍스트
        """
        # TODO: Phase 2에서 ReAct Engine과 연동
        # 현재는 간단한 더미 응답 제공
        if "안녕" in user_input or "hello" in user_input.lower():
            return f"안녕하세요 {author.display_name}님! 저는 당신의 개인 AI 비서 Angmini입니다. 어떻게 도와드릴까요?"
        elif "도움" in user_input or "help" in user_input.lower():
            return """저는 다양한 작업을 도와드릴 수 있습니다:
            
• 파일 관리 및 정보 검색
• 일정 관리 (Notion 연동)
• 웹 검색 및 정보 수집
• 기타 여러 작업들

무엇이든 말씀해주세요!"""
        elif "기능" in user_input or "할 수 있" in user_input:
            return "현재는 기본적인 대화 기능만 제공하고 있지만, 곧 파일 관리, 웹 검색, Notion 연동 등 다양한 기능이 추가될 예정입니다!"
        else:
            return f"'{user_input}'에 대해 말씀해주셨군요! 현재는 기본 기능만 제공하고 있지만, 더 똑똑한 AI로 발전하고 있습니다. 조금만 기다려주세요! 🤖"
    
    async def start(self):
        """
        Discord 봇을 시작합니다.
        
        Raises:
            ConfigurationError: Discord 토큰이 설정되지 않은 경우
        """
        try:
            if not config.discord_token:
                raise ConfigurationError("Discord 토큰이 설정되지 않았습니다.")
            
            logger.info("Discord 봇을 시작합니다...")
            await self.bot.start(config.discord_token)
            
        except discord.LoginFailure:
            logger.error("Discord 토큰이 유효하지 않습니다.")
            raise ConfigurationError("유효하지 않은 Discord 토큰입니다.")
        except Exception as e:
            logger.error(f"Discord 봇 시작 중 오류 발생: {e}")
            raise
    
    async def stop(self):
        """Discord 봇을 종료합니다."""
        logger.info("Discord 봇을 종료합니다...")
        await self.bot.close()

async def run_discord_bot():
    """Discord 봇을 실행하는 비동기 함수입니다."""
    bot = DiscordBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("사용자에 의해 봇이 종료되었습니다.")
        await bot.stop()
    except Exception as e:
        logger.error(f"Discord 봇 실행 중 오류: {e}")
        await bot.stop()
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_discord_bot())
