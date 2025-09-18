"""Safety guardrails for the ReAct execution loop."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ai.core.exceptions import EngineError


@dataclass(slots=True)
class SafetyConfig:
    max_steps: int = 20
    max_attempts_per_step: int = 3
    max_runtime_seconds: int = 300


class SafetyGuard:
    """Tracks execution metrics and stops runs that exceed guardrails."""

    def __init__(self, config: SafetyConfig | None = None) -> None:
        self._config = config or SafetyConfig()
        self._started_at = datetime.utcnow()
        self._steps_executed = 0

    @property
    def max_attempts_per_step(self) -> int:
        return self._config.max_attempts_per_step

    def check(self) -> None:
        if self._steps_executed >= self._config.max_steps:
            raise EngineError(
                f"최대 실행 스텝 수({self._config.max_steps})를 초과했습니다."
            )
        elapsed = datetime.utcnow() - self._started_at
        if elapsed > timedelta(seconds=self._config.max_runtime_seconds):
            raise EngineError("ReAct 루프 실행 시간이 너무 오래 걸립니다.")

    def note_step(self) -> None:
        self._steps_executed += 1
