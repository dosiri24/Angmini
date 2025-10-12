"""Detects repeated step failures to avoid infinite loops."""

from __future__ import annotations

from dataclasses import dataclass

from ai.core.logger import get_logger

from .models import ExecutionContext, LoopDetectedEvent, PlanStep, StepResult


@dataclass(slots=True)
class LoopDetection:
    step_id: int
    attempts: int
    reason: str


class LoopDetector:
    """Analyzes execution context to identify repeated failure patterns."""

    def __init__(self, *, repeat_threshold: int = 3) -> None:
        self._repeat_threshold = repeat_threshold
        self._logger = get_logger(self.__class__.__name__)

    def evaluate(self, context: ExecutionContext, step: PlanStep, result: StepResult) -> LoopDetection | None:
        attempts = context.get_attempt(step.id)
        if attempts < self._repeat_threshold:
            return None

        recent_failures = context.recent_failures(step.id, limit=self._repeat_threshold)
        if len(recent_failures) < self._repeat_threshold:
            return None

        last_error = recent_failures[-1].error_message
        if not all(entry.error_message == last_error for entry in recent_failures):
            return None

        reason = (
            f"Step {step.id} failed {attempts} times with the same error: {last_error}"
        )
        context.record_event(LoopDetectedEvent(step_id=step.id, attempts=attempts, reason=reason))
        self._logger.warning(reason)
        return LoopDetection(step_id=step.id, attempts=attempts, reason=reason)
