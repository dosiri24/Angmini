"""Application entry point for the Personal AI Assistant."""

from __future__ import annotations

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



def main() -> None:
    """Configure the application and dispatch to the selected interface."""
    try:
        config = Config.load(supported_interfaces=_INTERFACE_ENTRYPOINTS.keys())
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    setup_logging(config.log_level)
    logger = get_logger(__name__)
    log_file = session_log_path()
    if log_file:
        logger.debug("Session log file initialised at %s", log_file)
    logger.info("Launching Personal AI Assistant (interface=%s)", config.default_interface)
    logger.debug(
        "Configuration loaded (model=%s, gemini_key_present=%s, discord_token_present=%s)",
        config.gemini_model,
        bool(config.gemini_api_key),
        bool(config.discord_bot_token),
    )
    logger.debug("Configuration env path: %s", config.env_path or "<auto>")

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
