"""Determines how the agent should adapt when steps fail."""

from __future__ import annotations

from ai.core.logger import get_logger

from .models import ExecutionContext, PlanStep, PlanningDecision, StepOutcome, StepResult
from .safety_guard import SafetyGuard


class PlanningEngine:
    """Decides between retrying a step or requesting a new plan."""

    def __init__(self, safety_guard: SafetyGuard | None = None) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._safety_guard = safety_guard

    def evaluate(
        self,
        context: ExecutionContext,
        step: PlanStep,
        result: StepResult,
        loop_reason: str | None = None,
    ) -> PlanningDecision:
        if result.outcome == StepOutcome.SUCCESS:
            return PlanningDecision(action="proceed", reason="step succeeded")

        if loop_reason:
            return PlanningDecision(action="replan", reason=loop_reason)

        max_attempts = self._safety_guard.max_attempts_per_step if self._safety_guard else 3
        if result.outcome == StepOutcome.RETRY:
            if result.should_retry(max_attempts):
                return PlanningDecision(
                    action="retry",
                    reason=f"retry allowed (attempt {result.attempt} of {max_attempts})",
                )
            return PlanningDecision(
                action="replan",
                reason=f"retry limit {max_attempts} reached for step {step.id}",
            )

        # For any non-retry failure, surface as abort so caller can raise.
        return PlanningDecision(action="abort", reason=result.error_reason or "unknown failure")
