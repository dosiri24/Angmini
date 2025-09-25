"""Determines how the agent should adapt when steps fail."""

from __future__ import annotations

from ai.core.logger import get_logger

from .models import (
    ExecutionContext,
    PlanStep,
    PlanningDecision,
    PlanningDecisionEvent,
    StepOutcome,
    StepResult,
)
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
        decision = self._determine_decision(step, result, loop_reason)
        self._record_decision(context, step, result, decision, loop_reason)
        return decision

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _determine_decision(
        self,
        step: PlanStep,
        result: StepResult,
        loop_reason: str | None,
    ) -> PlanningDecision:
        if result.outcome == StepOutcome.SUCCESS:
            return PlanningDecision(action="proceed", reason="step succeeded")

        max_attempts = self._safety_guard.max_attempts_per_step if self._safety_guard else 3
        error_summary = result.error_reason or "자세한 오류 정보 없음"
        step_label = f"Step {step.id}"

        if loop_reason:
            reason = f"{step_label} 반복 실패 감지: {loop_reason}. 재계획합니다."
            return PlanningDecision(action="replan", reason=reason)

        if result.outcome == StepOutcome.RETRY:
            if result.should_retry(max_attempts):
                remaining = max_attempts - result.attempt
                reason = (
                    f"{step_label} 시도 {result.attempt}/{max_attempts} 실패: {error_summary}. "
                    f"재시도 진행 (잔여 {remaining}회)."
                )
                return PlanningDecision(action="retry", reason=reason)

            reason = (
                f"{step_label}가 시도 {result.attempt}/{max_attempts}에서 계속 실패: "
                f"{error_summary}. 새로운 계획이 필요합니다."
            )
            return PlanningDecision(action="replan", reason=reason)

        if result.outcome == StepOutcome.FAILED:
            category = None
            if isinstance(result.data, dict):
                category = result.data.get("error_category")
            if category:
                reason = f"{step_label} {category} 오류: {error_summary}. 재계획합니다."
            else:
                reason = f"{step_label} 실패: {error_summary}. 재계획합니다."
            return PlanningDecision(action="replan", reason=reason)

        reason = f"{step_label}에서 처리되지 않은 결과 '{result.outcome.value}' 발생"
        if result.error_reason:
            reason += f": {result.error_reason}"
        return PlanningDecision(action="abort", reason=reason)

    def _record_decision(
        self,
        context: ExecutionContext,
        step: PlanStep,
        result: StepResult,
        decision: PlanningDecision,
        loop_reason: str | None,
    ) -> None:
        if decision.action == "proceed":
            return

        event = PlanningDecisionEvent(
            step_id=step.id,
            decision=decision.action,
            reason=decision.reason,
            attempt=result.attempt,
            error_reason=result.error_reason,
        )
        context.record_event(event)

        history = context.metadata.setdefault("planning_decisions", [])
        history.append(
            {
                "step_id": step.id,
                "decision": decision.action,
                "reason": decision.reason,
                "attempt": result.attempt,
                "error_reason": result.error_reason,
                "loop_reason": loop_reason,
            }
        )

        context.append_scratch(f"planning decision: {decision.reason}")
