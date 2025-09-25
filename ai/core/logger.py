"""Logging utilities shared across the Personal AI Assistant."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

_CONSOLE_LOG_FORMAT = "%(asctime)s | %(levelname).1s | %(name)s | %(message)s"
_FILE_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_DATEFMT = "%H:%M:%S"
_DEFAULT_LOGGER_NAME = "personal_ai_assistant"
_DEFAULT_LOG_DIR = "logs"

_CONFIGURED = False
_SESSION_LOG_PATH: Path | None = None

_COLOUR_CODES = {
    logging.DEBUG: "\033[36m",  # Cyan
    logging.INFO: "\033[32m",  # Green
    logging.WARNING: "\033[33m",  # Yellow
    logging.ERROR: "\033[31m",  # Red
    logging.CRITICAL: "\033[35m",  # Magenta
}
_COLOUR_RESET = "\033[0m"


def setup_logging(level: str = "INFO", *, log_dir: str | Path | None = None) -> None:
    """Configure the root logger exactly once and update the log level."""
    global _CONFIGURED, _SESSION_LOG_PATH

    root_logger = logging.getLogger()
    numeric_level = _coerce_level(level)
    root_logger.setLevel(numeric_level)

    if not _CONFIGURED:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            _ColourFormatter(
                _CONSOLE_LOG_FORMAT,
                datefmt=_DATEFMT,
                use_colour=_supports_colour(console_handler.stream),
            )
        )

        handlers: list[logging.Handler] = [console_handler]

        target_dir = _resolve_log_dir(log_dir)
        if target_dir is not None:
            target_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            _SESSION_LOG_PATH = target_dir / f"{timestamp}.log"
            file_handler = logging.FileHandler(_SESSION_LOG_PATH, encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter(_FILE_LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
            )
            handlers.append(file_handler)
        else:
            _SESSION_LOG_PATH = None

        root_logger.handlers.clear()
        for handler in handlers:
            root_logger.addHandler(handler)

        _CONFIGURED = True
    else:
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setFormatter(
                    _ColourFormatter(
                        _CONSOLE_LOG_FORMAT,
                        datefmt=_DATEFMT,
                        use_colour=_supports_colour(getattr(handler, "stream", None)),
                    )
                )
            else:
                handler.setFormatter(
                    logging.Formatter(_FILE_LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
                )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger that shares the configured root handlers."""
    logger_name = name or _DEFAULT_LOGGER_NAME
    logger = logging.getLogger(logger_name)
    if logger.propagate is False:
        logger.propagate = True
    return logger


def session_log_path() -> Path | None:
    """Expose the current session log path for diagnostics."""
    return _SESSION_LOG_PATH


def _resolve_log_dir(log_dir: str | Path | None) -> Path | None:
    if log_dir is None:
        env_dir = os.getenv("LOG_DIR")
        if env_dir:
            return Path(env_dir)
        return Path(_DEFAULT_LOG_DIR)
    if isinstance(log_dir, Path):
        return log_dir
    return Path(log_dir)


def _coerce_level(level: str) -> int:
    level_name = level.upper()
    if level_name in logging._nameToLevel:  # type: ignore[attr-defined]
        return logging._nameToLevel[level_name]  # type: ignore[attr-defined]
    if level_name.isdigit():
        return int(level_name)
    return logging.INFO


def _supports_colour(stream) -> bool:
    if stream is None:
        return False
    if not hasattr(stream, "isatty"):
        return False
    try:
        return stream.isatty() and sys.platform != "win32"
    except Exception:  # pragma: no cover - defensive
        return False


class _ColourFormatter(logging.Formatter):
    def __init__(self, fmt: str, *, datefmt: str | None, use_colour: bool) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)
        self._use_colour = use_colour

    def format(self, record: logging.LogRecord) -> str:
        original_levelname = record.levelname
        if self._use_colour:
            colour = _COLOUR_CODES.get(record.levelno)
            if colour:
                record.levelname = f"{colour}{record.levelname}{_COLOUR_RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname
