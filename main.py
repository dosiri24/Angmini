"""Application entry point for the Personal AI Assistant."""

from __future__ import annotations

import argparse
import sys
from importlib import import_module
from types import ModuleType
from typing import Callable, Mapping, cast

from ai.core.config import Config
from ai.core.exceptions import ConfigError, EngineError, InterfaceError
from ai.core.logger import get_logger, session_log_path, setup_logging

InterfaceHandler = Callable[[Config], None]

_INTERFACE_ENTRYPOINTS: Mapping[str, tuple[str, str]] = {
    "cli": ("interface.cli", "run"),
    "discord": ("interface.discord_bot", "run_bot"),
}


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="angmini",
        description="Personal AI Assistant built on Google Gemini with CrewAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  angmini                              # Interactive mode
  angmini "파일 목록 보여줘"            # Single command execution
  angmini --debug "테스트"              # Debug mode with single command
  angmini --no-stream "빠른 질문"       # No streaming output
  angmini --interface discord          # Launch Discord bot
        """,
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Single command to execute (if omitted, enters interactive mode)",
    )

    parser.add_argument(
        "--interface",
        choices=["cli", "discord"],
        help="Interface to use (overrides DEFAULT_INTERFACE env var)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (verbose CrewAI output)",
    )

    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming output for faster response",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="Angmini 2.0.0 (CrewAI)",
    )

    return parser.parse_args()


def main() -> None:
    """Configure the application and dispatch to the selected interface."""
    from dataclasses import replace

    args = _parse_args()

    try:
        config = Config.load(supported_interfaces=_INTERFACE_ENTRYPOINTS.keys())
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    # Override config with CLI arguments (create new instance since config is frozen)
    config_overrides = {}
    if args.interface:
        config_overrides['default_interface'] = args.interface
    if args.debug:
        config_overrides['log_level'] = "DEBUG"
    if args.no_stream:
        config_overrides['stream_delay'] = 0.0

    if config_overrides:
        config = replace(config, **config_overrides)

    setup_logging(config.log_level)
    logger = get_logger(__name__)
    log_file = session_log_path()

    # Single command mode
    if args.query:
        logger.info("Single command mode: %s", args.query)
        try:
            from interface.cli import run_single_command
            run_single_command(config, args.query)
        except InterfaceError as exc:
            logger.error("Interface error: %s", exc)
            print(f"Interface error: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        except EngineError as exc:
            logger.error("Engine error: %s", exc)
            print(f"Engine error: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        return

    # Interactive mode
    logger.info("Launching Personal AI Assistant (interface=%s)", config.default_interface)
    logger.debug(
        "Config: model=%s, log=%s",
        config.gemini_model,
        log_file or "console-only",
    )

    try:
        interface_handler = _resolve_interface(config.default_interface)
    except InterfaceError as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc

    try:
        interface_handler(config)
    except InterfaceError as exc:
        logger.error("Interface error: %s", exc)
        print(f"Interface error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except EngineError as exc:
        logger.error("Engine error: %s", exc)
        print(f"Engine error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _resolve_interface(interface_name: str) -> InterfaceHandler:
    module_name, attribute_name = _INTERFACE_ENTRYPOINTS.get(interface_name, (None, None))
    if module_name is None:
        raise InterfaceError(f"Interface '{interface_name}' is not supported.")

    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        raise InterfaceError(
            f"Interface '{interface_name}' is not available yet. Implement '{module_name}' before selecting it."
        ) from exc

    handler = _get_attribute(module, attribute_name)
    if not callable(handler):
        raise InterfaceError(
            f"Interface '{interface_name}' entry point '{attribute_name}' is not callable."
        )
    return cast(InterfaceHandler, handler)


def _get_attribute(module: ModuleType, attribute_name: str) -> InterfaceHandler:
    try:
        return getattr(module, attribute_name)
    except AttributeError as exc:
        raise InterfaceError(
            f"Interface module '{module.__name__}' does not define '{attribute_name}'."
        ) from exc


if __name__ == "__main__":
    main()
