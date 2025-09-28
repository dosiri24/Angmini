"""Helpers for streaming text output with configurable typing delay."""

from __future__ import annotations

import os
import sys
import time
from typing import Iterable, Optional

_BASE_DELAY = 0.05
_ENV_KEYS = ("ANGMINI_STREAM_DELAY", "STREAM_DELAY")


def _parse_delay(value: Optional[str]) -> float:
    if value is None:
        return _BASE_DELAY
    try:
        parsed = float(value.strip())
    except (ValueError, AttributeError):
        return _BASE_DELAY
    if parsed < 0:
        return 0.0
    return parsed


_DEFAULT_DELAY = _parse_delay(os.getenv("ANGMINI_STREAM_DELAY") or os.getenv("STREAM_DELAY"))


def get_stream_delay(override: Optional[float] = None) -> float:
    """Return the delay (in seconds) between streamed characters."""
    if override is not None:
        return max(override, 0.0)
    for key in _ENV_KEYS:
        value = os.getenv(key)
        if value is not None:
            return _parse_delay(value)
    return _DEFAULT_DELAY


def stream_text(text: str, *, delay: Optional[float] = None, newline: bool = True) -> None:
    """Print ``text`` character by character with the configured delay."""
    if not text:
        if newline:
            print()
        return

    sleep_for = get_stream_delay(delay)
    for char in text:
        print(char, end="", flush=True)
        if sleep_for > 0:
            time.sleep(sleep_for)
    if newline:
        print()
    sys.stdout.flush()


def stream_lines(lines: Iterable[str], *, prefix: str = "", delay: Optional[float] = None) -> None:
    """Stream each line from ``lines`` with an optional prefix."""
    for line in lines:
        if prefix:
            print(prefix, end="", flush=True)
        stream_text(line, delay=delay)


__all__ = ["get_stream_delay", "stream_text", "stream_lines"]
