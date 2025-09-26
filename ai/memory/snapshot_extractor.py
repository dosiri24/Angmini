"""Helpers for extracting memory source payloads from the execution context."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from ai.react_engine.models import ExecutionContext, PlanStep, StepCompletedEvent

from .memory_records import MemorySourceData


class SnapshotExtractor:
    """Collects the raw artefacts that feed the memory curator."""

    def collect(
        self,
        context: ExecutionContext,
        *,
        user_request: str,
    ) -> MemorySourceData:
        plan_text = context.as_plan_checklist()
        scratchpad = context.final_scratchpad_digest()
        failure_summary = context.fail_log_summary()
        final_response = self._final_response(context)
        tool_entries = list(self._tool_history(context))
        metadata: Dict[str, object] = {
            "planning_decisions": context.metadata.get("planning_decisions", []),
            "fail_log_count": len(context.fail_log),
            "total_steps": len(context.plan_steps),
        }

        return MemorySourceData(
            goal=context.goal,
            user_request=user_request,
            plan_checklist=plan_text,
            scratchpad_digest=scratchpad,
            tool_invocations=tool_entries,
            failure_log=failure_summary,
            final_response_draft=final_response,
            metadata=metadata,
        )

    def _tool_history(self, context: ExecutionContext) -> Iterable[Dict[str, object]]:
        steps_by_id: Dict[int, PlanStep] = {step.id: step for step in context.plan_steps}
        for event in context.events:
            if isinstance(event, StepCompletedEvent):
                step = steps_by_id.get(event.step_id)
                entry: Dict[str, object] = {
                    "step_id": event.step_id,
                    "outcome": event.outcome.value,
                }
                if step is not None:
                    entry["tool"] = step.tool_name
                    entry["description"] = step.description
                if event.data is not None:
                    entry["data"] = event.data
                if event.error_reason:
                    entry["error_reason"] = event.error_reason
                yield entry

    def _final_response(self, context: ExecutionContext) -> Optional[str]:
        final_message = context.metadata.get("final_message")
        if isinstance(final_message, str) and final_message.strip():
            return final_message.strip()
        return None
