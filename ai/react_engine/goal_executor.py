"""Coordinates planning and execution of user goals via the ReAct pattern."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from ai.ai_brain import AIBrain
from ai.core.exceptions import EngineError
from ai.core.logger import get_logger
from mcp.tool_manager import ToolManager

from .agent_scratchpad import AgentScratchpad
from .models import (
    ExecutionContext,
    FailureLogEntry,
    PlanStep,
    PlanStepStatus,
    PlanUpdatedEvent,
    StepCompletedEvent,
    StepOutcome,
    StepResult,
)
from .safety_guard import SafetyGuard
from .step_executor import StepExecutor


class GoalExecutor:
    """High-level orchestrator for planning and executing a user goal."""

    def __init__(
        self,
        brain: AIBrain,
        tool_manager: ToolManager,
        step_executor: StepExecutor,
        safety_guard: SafetyGuard,
        scratchpad: AgentScratchpad,
        *,
        template_dir: Optional[Path] = None,
    ) -> None:
        self._brain = brain
        self._tool_manager = tool_manager
        self._step_executor = step_executor
        self._safety_guard = safety_guard
        self._scratchpad = scratchpad
        self._logger = get_logger(self.__class__.__name__)

        base_dir = template_dir or Path(__file__).resolve().parent / "prompt_templates"
        self._system_prompt = (base_dir / "system_prompt.md").read_text(encoding="utf-8")
        self._react_prompt_template = (base_dir / "react_prompt.md").read_text(encoding="utf-8")

    def run(self, goal: str) -> ExecutionContext:
        context = ExecutionContext(goal=goal)
        self._scratchpad.clear()
        self._scratchpad.add(f"goal established: {goal}")
        self._update_plan(context, reason="initial plan required")

        while context.remaining_steps():
            step = self._pick_next_step(context)
            if step is None:
                break

            self._safety_guard.check()
            step.mark_in_progress()
            attempts = self._increment_attempt(context, step.id)
            self._logger.info("Executing step %s (attempt %s)", step.id, attempts)
            self._scratchpad.add(f"executing step #{step.id}: {step.description}")

            self._safety_guard.note_step()
            result = self._step_executor.execute(step, context, attempts)
            self._handle_step_result(context, step, result)

        return context

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_plan(self, context: ExecutionContext, reason: Optional[str] = None) -> None:
        available_tools = self._tool_manager.list()
        prompt = self._build_plan_prompt(context.goal, available_tools, context, reason)
        response = self._brain.generate_text(prompt)
        steps = self._parse_plan_response(response)
        if not steps:
            raise EngineError("LLM이 빈 계획을 반환했습니다.")

        context.plan_steps = steps
        context.metadata["attempts"] = {}
        context.current_step_index = 0
        context.record_event(PlanUpdatedEvent(plan_steps=steps, reason=reason))
        self._scratchpad.add("plan updated:\n" + context.as_plan_checklist())

    def _build_plan_prompt(
        self,
        goal: str,
        tools: Dict[str, Dict[str, object]],
        context: ExecutionContext,
        reason: Optional[str],
    ) -> str:
        tool_lines = []
        for name, info in tools.items():
            description = info.get("description", "")
            tool_lines.append(f"- {name}: {description}")
        tools_block = "\n".join(tool_lines) if tool_lines else "(등록된 도구 없음)"

        reason_block = f"이전에 실패한 이유: {reason}\n" if reason else ""
        return (
            f"{self._system_prompt}\n\n"
            f"사용자 목표: {goal}\n"
            f"사용 가능한 도구 목록:\n{tools_block}\n\n"
            f"현재 계획 체크리스트:\n{context.as_plan_checklist() or '(계획 없음)'}\n\n"
            f"최근 실패 로그:\n{context.fail_log_summary()}\n\n"
            f"{reason_block}"
            "JSON 배열 형식의 새로운 계획을 생성하세요.\n"
            "각 항목은 {\"id\": number, \"description\": string, \"tool\": string | null, \"parameters\": object, \"status\": string} 구조여야 합니다.\n"
            "status는 todo/in_progress/done 중 하나입니다."
        )

    def _parse_plan_response(self, response: str) -> List[PlanStep]:
        try:
            data = json.loads(response)
        except json.JSONDecodeError as exc:
            raise EngineError("계획 응답이 JSON 형식을 따르지 않습니다.") from exc

        if not isinstance(data, list):
            raise EngineError("계획 응답은 JSON 배열이어야 합니다.")

        steps: List[PlanStep] = []
        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise EngineError("계획 항목은 JSON 객체여야 합니다.")
            description = item.get("description")
            if not isinstance(description, str) or not description.strip():
                raise EngineError("각 계획 항목은 description 문자열을 가져야 합니다.")
            step_id = item.get("id")
            if not isinstance(step_id, int):
                step_id = index
            status_raw = (item.get("status") or "todo").lower()
            try:
                status = PlanStepStatus(status_raw)
            except ValueError:
                status = PlanStepStatus.TODO
            tool_name = item.get("tool")
            if tool_name is not None and not isinstance(tool_name, str):
                tool_name = None
            params = item.get("parameters") or {}
            if not isinstance(params, dict):
                params = {}
            steps.append(
                PlanStep(
                    id=step_id,
                    description=description.strip(),
                    tool_name=tool_name.strip() if isinstance(tool_name, str) else None,
                    parameters=params,
                    status=status,
                )
            )
        return steps

    def _pick_next_step(self, context: ExecutionContext) -> Optional[PlanStep]:
        for idx, step in enumerate(context.plan_steps):
            if step.status != PlanStepStatus.DONE:
                context.current_step_index = idx
                return step
        context.current_step_index = None
        return None

    def _increment_attempt(self, context: ExecutionContext, step_id: int) -> int:
        attempts: Dict[int, int] = context.metadata.setdefault("attempts", {})
        attempts[step_id] = attempts.get(step_id, 0) + 1
        return attempts[step_id]

    def _handle_step_result(self, context: ExecutionContext, step: PlanStep, result: StepResult) -> None:
        if result.outcome == StepOutcome.SUCCESS:
            step.mark_done()
            context.record_event(StepCompletedEvent(step_id=step.id, outcome=result.outcome, data=result.data))
            context.append_scratch(f"step #{step.id} 완료")
            return

        failure_entry = FailureLogEntry(
            step_id=step.id,
            command=json.dumps({"tool": step.tool_name, "parameters": step.parameters}, ensure_ascii=False),
            error_message=result.error_reason or "알 수 없는 오류",
            attempt=result.attempt,
        )
        context.add_failure(failure_entry)
        context.append_scratch(f"step #{step.id} 실패: {failure_entry.error_message}")

        if result.outcome == StepOutcome.RETRY:
            max_attempts = self._safety_guard.max_attempts_per_step
            if result.should_retry(max_attempts):
                step.status = PlanStepStatus.TODO
                return
            self._logger.warning(
                "Step %s 최대 시도 횟수 초과(%s). 계획 재생성 시도.",
                step.id,
                max_attempts,
            )
            self._update_plan(context, reason=f"step {step.id} failed repeatedly")
            return

        raise EngineError(
            f"Step {step.id} 실행 중 복구 불가능한 오류가 발생했습니다: {result.error_reason}"
        )

    # Future: integrate thinking loop with react prompt
    def render_react_prompt(self, context: ExecutionContext) -> str:
        checklist = context.as_plan_checklist()
        current = context.current_step()
        current_text = current.to_prompt_fragment() if current else "(no active step)"
        return (
            self._react_prompt_template
            .replace("{{goal}}", context.goal)
            .replace("{{plan_checklist}}", checklist or "(empty)")
            .replace("{{fail_log}}", context.fail_log_summary())
            .replace("{{current_step}}", current_text)
            .replace("{{scratchpad}}", self._scratchpad.dump(limit=10) or "(empty)")
        )
