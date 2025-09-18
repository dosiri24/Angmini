"""Logging utilities shared across the Personal AI Assistant."""

from __future__ import annotations

import logging
from typing import Optional

_DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_DEFAULT_LOGGER_NAME = "personal_ai_assistant"

_CONFIGURED = False


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger exactly once and update the log level."""
    global _CONFIGURED

    root_logger = logging.getLogger()
    numeric_level = _coerce_level(level)
    root_logger.setLevel(numeric_level)

    if not _CONFIGURED:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_DEFAULT_LOG_FORMAT))
        root_logger.handlers.clear()
        root_logger.addHandler(handler)
        _CONFIGURED = True
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(logging.Formatter(_DEFAULT_LOG_FORMAT))


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a configured logger, creating it on first use."""
    logger_name = name or _DEFAULT_LOGGER_NAME
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_DEFAULT_LOG_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(logging.getLogger().level or logging.INFO)
        logger.propagate = False
    return logger


def _coerce_level(level: str) -> int:
    level_name = level.upper()
    if level_name in logging._nameToLevel:  # type: ignore[attr-defined]
        return logging._nameToLevel[level_name]  # type: ignore[attr-defined]
    if level_name.isdigit():
        return int(level_name)
    return logging.INFO
