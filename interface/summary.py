"""Presentation helpers shared by user-facing interfaces."""

from __future__ import annotations

import json
from typing import Any, Iterable, Sequence

from ai.react_engine.models import ExecutionContext, PlanStep, PlanStepStatus, StepCompletedEvent


def format_execution_summary(context: ExecutionContext, *, max_failures: int = 3) -> str:
    """Return a human-friendly summary of the latest execution."""
    lines: list[str] = []
    lines.extend(_render_plan(context.plan_steps))

    if context.fail_log:
        lines.append("⚠️ 최근 실패 기록:")
        for entry in context.fail_log[-max_failures:]:
            lines.append(
                f"  - step {entry.step_id} (attempt {entry.attempt}): {entry.error_message}"
            )
    else:
        lines.append("💡 실패 기록은 없습니다.")

    payload = _latest_payload(context.events)
    if payload is not None:
        lines.append("📦 마지막 결과 데이터:")
        formatted = _format_payload(payload)
        lines.extend(f"  {line}" for line in formatted.splitlines())

    return "\n".join(lines)


def _render_plan(plan_steps: Sequence[PlanStep]) -> Iterable[str]:
    if not plan_steps:
        return ["(계획이 비어 있습니다)"]

    lines = ["📋 계획 체크리스트:"]
    for step in plan_steps:
        symbol = {
            PlanStepStatus.TODO: "⬜",
            PlanStepStatus.IN_PROGRESS: "🔄",
            PlanStepStatus.DONE: "✅",
        }[step.status]
        tool_hint = f" (tool: {step.tool_name})" if step.tool_name else ""
        lines.append(f"{symbol} #{step.id}{tool_hint} - {step.description}")

    if all(step.status == PlanStepStatus.DONE for step in plan_steps):
        lines.append("✨ 모든 단계가 완료됐어요!")
    else:
        lines.append("⏳ 아직 완료하지 않은 단계가 있어요.")
    return lines


def _latest_payload(events: Sequence[Any]) -> Any | None:
    for event in reversed(events):
        if isinstance(event, StepCompletedEvent) and event.data is not None:
            return event.data
    return None


def _format_payload(payload: Any) -> str:
    try:
        text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    except TypeError:
        text = str(payload)

    max_length = 800
    if len(text) > max_length:
        return text[:max_length] + "\n  ... (이후 내용은 생략했어요)"
    return text


__all__ = ["format_execution_summary"]
