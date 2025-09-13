"""
Personal AI Assistant (Angmini)의 메인 실행 파일입니다.
이 파일은 애플리케이션을 초기화하고 실행하는 진입점 역할을 합니다.
"""
import sys
import asyncio
from ai.core.config import config
from ai.core.logger import logger
from ai.core.exceptions import ConfigurationError

def show_interface_menu():
    """사용자에게 인터페이스 선택 메뉴를 보여줍니다."""
    print("\n🤖 Personal AI Assistant (Angmini)")
    print("=" * 40)
    print("사용할 인터페이스를 선택해주세요:")
    print("1. CLI (터미널 인터페이스)")
    print("2. Discord Bot")
    print("3. 종료")
    print("=" * 40)

def main():
    """
    애플리케이션의 메인 함수입니다.
    설정 및 로거를 초기화하고, 환경변수에 설정된 기본 인터페이스를 실행합니다.
    """
    try:
        logger.info("애플리케이션을 시작합니다.")
        
        # Rule 2: Explicit Failure Handling
        # 설정 파일에서 로드한 필수 값들이 정상적으로 로드되었는지 확인합니다.
        logger.info(f"Google API Key: ...{config.google_api_key[-4:]}")
        logger.info(f"Discord Token: ...{config.discord_token[-4:]}")
        logger.info(f"기본 인터페이스: {config.default_interface}")
        logger.info("성공적으로 설정을 로드했습니다.")

        # 명령행 인수가 있으면 우선 적용
        if len(sys.argv) > 1:
            interface_choice = sys.argv[1].lower()
            logger.info(f"명령행 인수로 인터페이스 선택: {interface_choice}")
        else:
            # 환경변수에서 기본 인터페이스 가져오기
            interface_choice = config.default_interface
            logger.info(f"환경변수(DEFAULT_INTERFACE)에서 인터페이스 선택: {interface_choice}")

        # 인터페이스 실행
        if interface_choice in ['cli', 'terminal']:
            run_cli_interface()
        elif interface_choice in ['discord', 'bot']:
            asyncio.run(run_discord_interface())
        elif interface_choice == 'menu':
            # 대화형 메뉴 표시
            run_interactive_menu()
        else:
            print(f"❌ 알 수 없는 인터페이스: {interface_choice}")
            print("💡 .env 파일의 DEFAULT_INTERFACE를 다음 중 하나로 설정하세요:")
            print("   - cli: 터미널 인터페이스")
            print("   - discord: Discord 봇")
            print("   - menu: 선택 메뉴 표시")
            print("📝 또는 명령행에서: python main.py [cli|discord|menu]")

    except ConfigurationError as e:
        logger.error(f"설정 오류가 발생했습니다: {e}")
        logger.error(".env 파일에 필요한 환경 변수가 올바르게 설정되었는지 확인해주세요.")
        return
    except Exception as e:
        logger.critical(f"예상치 못한 오류가 발생했습니다: {e}", exc_info=True)
        return

def run_interactive_menu():
    """대화형 메뉴를 표시합니다."""
    while True:
        show_interface_menu()
        try:
            choice = input("선택하세요 (1-3): ").strip()
            
            if choice == '1':
                run_cli_interface()
                break
            elif choice == '2':
                asyncio.run(run_discord_interface())
                break
            elif choice == '3':
                print("프로그램을 종료합니다. 안녕히 가세요! 👋")
                break
            else:
                print("❌ 잘못된 선택입니다. 1, 2, 또는 3을 입력해주세요.")
                
        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다. 안녕히 가세요! 👋")
            break

def run_cli_interface():
    """CLI 인터페이스를 실행합니다."""
    try:
        from interface.cli import run_cli
        logger.info("CLI 인터페이스를 시작합니다.")
        run_cli()
    except Exception as e:
        logger.error(f"CLI 인터페이스 실행 중 오류: {e}")
        print("CLI 인터페이스를 시작할 수 없습니다.")

async def run_discord_interface():
    """Discord 봇 인터페이스를 실행합니다."""
    try:
        from interface.discord_bot import run_discord_bot
        logger.info("Discord 봇을 시작합니다.")
        await run_discord_bot()
    except ConfigurationError as e:
        logger.error(f"Discord 봇 설정 오류: {e}")
        print("Discord 봇을 시작할 수 없습니다. 토큰을 확인해주세요.")
    except Exception as e:
        logger.error(f"Discord 봇 실행 중 오류: {e}")
        print("Discord 봇을 시작할 수 없습니다.")

if __name__ == "__main__":
    main()
