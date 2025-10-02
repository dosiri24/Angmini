"""Command-line interface for the Personal AI Assistant with CrewAI."""

from __future__ import annotations

from typing import Iterable
import platform
import logging
import sys
import time

from ai.core.config import Config
from ai.core.exceptions import EngineError, InterfaceError
from ai.core.logger import get_logger
from ai.memory.factory import create_memory_service
from ai.ai_brain import AIBrain
from crew import AngminiCrew
from .streaming import stream_lines, stream_text

_EXIT_COMMANDS: tuple[str, ...] = ("exit", "quit", "종료")


def run(config: Config) -> None:
    """Launch a simple interactive CLI session with CrewAI integration."""
    logger = get_logger(__name__)
    logger.info("Starting CLI interface (CrewAI mode)")

    # AI Brain 초기화
    try:
        ai_brain = AIBrain(config)
        logger.info("AI Brain initialized")
    except EngineError as exc:
        logger.error("Failed to initialize AIBrain: %s", exc)
        print(f"⚠️ AI 엔진을 초기화하지 못했습니다: {exc}")
        return

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
            verbose=config.log_level == "DEBUG"  # DEBUG 모드에서만 verbose
        )
        logger.info("AngminiCrew initialized")
    except Exception as exc:
        logger.error("Failed to initialize AngminiCrew: %s", exc)
        print(f"⚠️ CrewAI를 초기화하지 못했습니다: {exc}")
        return

    # Apple MCP 서버 사전 시작 (macOS에서만)
    if platform.system() == "Darwin":
        _initialize_apple_mcp_server(logger)

    print("🤖 Angmini AI Assistant (CrewAI Mode)")
    print("종료하려면 'exit'를 입력하세요.")
    print("-" * 50)

    _interactive_loop(_EXIT_COMMANDS, logger, crew, config)
    print("다음에 또 만나요! 👋")


def _initialize_apple_mcp_server(logger: logging.Logger) -> None:
    """Apple MCP 서버를 사전에 시작합니다."""
    try:
        from mcp.apple_mcp_manager import AppleMCPManager

        manager = AppleMCPManager()
        if manager.start_server():
            logger.info("Apple MCP server ready")
            print("🍎 Apple MCP 서버가 준비되었습니다!")
        else:
            logger.warning("Apple MCP server failed to start")
            print("⚠️ Apple MCP 서버를 시작할 수 없습니다.")
    except ImportError:
        logger.debug("Apple MCP not available")
    except Exception as exc:
        logger.error("Apple MCP 서버 초기화 중 오류: %s", exc)


def _interactive_loop(
    exit_commands: Iterable[str],
    logger: logging.Logger,
    crew: AngminiCrew,
    config: Config,
) -> None:
    """대화형 루프 실행"""
    normalized = {cmd.lower() for cmd in exit_commands}

    while True:
        try:
            user_input = input("\n👤 You: ").strip()
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
            # 스트리밍 효과로 "생각 중" 표시
            print("🤖 Angmini: ", end="", flush=True)

            # CrewAI verbose 모드가 아닐 때만 생각 중 표시
            if config.log_level != "DEBUG":
                thinking_msg = "생각 중..."
                for char in thinking_msg:
                    print(char, end="", flush=True)
                    time.sleep(0.05)
                print("\r🤖 Angmini: ", end="", flush=True)

            # Crew 실행
            result = crew.kickoff(user_input)

            # CrewAI verbose 모드가 아닐 때만 결과 출력
            if config.log_level != "DEBUG":
                # 스트리밍 효과로 결과 출력
                if config.stream_delay > 0:
                    for char in result:
                        print(char, end="", flush=True)
                        time.sleep(config.stream_delay)
                    print()  # 마지막 줄바꿈
                else:
                    print(result)
            else:
                # DEBUG 모드에서는 이미 CrewAI가 출력했으므로 최종 결과만 표시
                print(f"\n📝 최종 결과: {result}")

        except EngineError as exc:
            logger.error("Goal execution failed: %s", exc)
            print(f"\n⚠️ 작업을 완료하지 못했어요: {exc}")
            continue
        except Exception as exc:
            logger.exception("Unexpected error while processing CLI command")
            print(f"\n⚠️ 오류가 발생했습니다: {exc}")
            print("자세한 내용은 로그를 확인해 주세요.")
            continue


def _display_execution_summary(context, config: Config) -> None:
    """실행 요약 표시 (필요시 사용)"""
    try:
        from .summary import format_execution_summary

        summary = format_execution_summary(context)
        if summary:
            print("\n" + "=" * 50)
            print("📊 실행 요약")
            print("=" * 50)
            for line in summary.split("\n"):
                print(line)
            print("=" * 50)
    except Exception as e:
        logger = get_logger(__name__)
        logger.warning(f"실행 요약 표시 실패: {e}")


if __name__ == "__main__":
    # 직접 실행 시
    try:
        config = Config.load()
        run(config)
    except Exception as e:
        print(f"오류: {e}")
        sys.exit(1)