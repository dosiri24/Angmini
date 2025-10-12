"""Lightweight scratchpad for recording the agent's internal notes."""

from __future__ import annotations

from typing import Iterable, List


class AgentScratchpad:
    """Stores short textual notes about recent reasoning."""

    def __init__(self) -> None:
        self._entries: List[str] = []

    def add(self, entry: str) -> None:
        if entry.strip():
            self._entries.append(entry.strip())

    def extend(self, entries: Iterable[str]) -> None:
        for entry in entries:
            self.add(entry)

    def dump(self, limit: int | None = None) -> str:
        items = self._entries if limit is None else self._entries[-limit:]
        return "\n".join(items)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._entries)

    def __iter__(self):  # pragma: no cover - trivial
        return iter(self._entries)
