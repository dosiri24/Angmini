"""Lightweight in-memory conversation store for ongoing sessions."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable, List

from ai.core.logger import get_logger


@dataclass(slots=True)
class ConversationTurn:
    """Represents a single user/assistant exchange."""

    user: str
    assistant: str | None = None


class ConversationMemory:
    """Maintains a rolling window of recent conversation turns."""

    def __init__(self, *, max_turns: int = 20) -> None:
        self._turns: Deque[ConversationTurn] = deque(maxlen=max_turns)
        self._logger = get_logger(self.__class__.__name__)

    def add_turn(self, user_text: str, assistant_text: str | None) -> None:
        user_clean = (user_text or "").strip()
        assistant_clean = (assistant_text or "").strip() or None
        if not user_clean and assistant_clean is None:
            return
        self._turns.append(ConversationTurn(user=user_clean, assistant=assistant_clean))
        self._logger.debug(
            "Turn added (total=%d): user='%s', assistant_present=%s",
            len(self._turns),
            user_clean,
            assistant_clean is not None,
        )

    def as_lines(self, limit: int | None = None) -> List[str]:
        turns: Iterable[ConversationTurn]
        if limit is None or limit >= len(self._turns):
            turns = self._turns
        else:
            turns = list(self._turns)[-limit:]
        lines: List[str] = []
        for idx, turn in enumerate(turns, start=1):
            if turn.user:
                lines.append(f"{idx}. 사용자: {turn.user}")
            if turn.assistant:
                lines.append(f"   어시스턴트: {turn.assistant}")
        return lines

    def formatted(self, limit: int | None = None) -> str:
        lines = self.as_lines(limit=limit)
        return "\n".join(lines) if lines else "(최근 대화 기록 없음)"

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._turns)

    def clear(self) -> None:
        self._turns.clear()


__all__ = ["ConversationMemory", "ConversationTurn"]
