"""Executes individual plan steps by invoking registered tools."""

from __future__ import annotations

import json
from pathlib import Path

from ai.ai_brain import AIBrain
from ai.core.exceptions import EngineError, ToolError
from ai.core.logger import get_logger
from mcp.tool_manager import ToolManager

from .conversation_memory import ConversationMemory
from .models import ExecutionContext, PlanStep, StepCompletedEvent, StepOutcome, StepResult


class StepExecutor:
    """Handles execution of a single `PlanStep`."""

    def __init__(
        self,
        tool_manager: ToolManager,
        brain: AIBrain | None = None,
        *,
        dialogue_template: str | None = None,
        conversation_memory: ConversationMemory | None = None,
    ) -> None:
        self._tool_manager = tool_manager
        self._brain = brain
        self._logger = get_logger(self.__class__.__name__)
        self._dialogue_template = dialogue_template or self._load_default_template()
        self._conversation_memory = conversation_memory

    def execute(self, step: PlanStep, context: ExecutionContext, attempt: int) -> StepResult:
        if not step.tool_name:
            return self._handle_dialogue_step(step, context, attempt)

        try:
            tool_result = self._tool_manager.execute(step.tool_name, **step.parameters)
            data = tool_result.unwrap()
            self._logger.info("Step %s 성공", step.id)
            return StepResult(
                step_id=step.id,
                outcome=StepOutcome.SUCCESS,
                data=data,
                attempt=attempt,
            )
        except ToolError as exc:
            message = str(exc)
            outcome, category = self._classify_tool_error(message)
            log_action = "재시도" if outcome == StepOutcome.RETRY else "재계획"
            self._logger.warning("Step %s 실패(%s 필요): %s", step.id, log_action, message)
            return StepResult(
                step_id=step.id,
                outcome=outcome,
                data={"error_category": category} if category else None,
                error_reason=message,
                attempt=attempt,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _handle_dialogue_step(
        self,
        step: PlanStep,
        context: ExecutionContext,
        attempt: int,
    ) -> StepResult:
        if self._brain is None:
            error = "Plan step에 사용할 도구가 지정되지 않았습니다."
            self._logger.error("%s (no fallback brain available)", error)
            return StepResult(
                step_id=step.id,
                outcome=StepOutcome.FAILED,
                error_reason=error,
                attempt=attempt,
            )

        latest_data = self._latest_observation_text(context)
        memory_text = (
            self._conversation_memory.formatted(limit=10)
            if self._conversation_memory
            else "(최근 대화 기록 없음)"
        )
        self._logger.debug("Dialogue step memory snapshot:\n%s", memory_text)
        prompt = self._build_dialogue_prompt(
            step.description,
            context,
            latest_data=latest_data,
            memory=memory_text,
        )
        self._logger.debug("Generating direct response for step %s", step.id)
        try:
            message = self._brain.generate_text(prompt, temperature=0.6)
        except EngineError as exc:
            self._logger.warning("대화 응답 생성 실패: %s", exc)
            return StepResult(
                step_id=step.id,
                outcome=StepOutcome.RETRY,
                error_reason=str(exc),
                attempt=attempt,
            )

        self._logger.info("Step %s 대화 응답 완료", step.id)
        return StepResult(
            step_id=step.id,
            outcome=StepOutcome.SUCCESS,
            data={
                "type": "direct_response",
                "message": message,
            },
            attempt=attempt,
        )

    def _build_dialogue_prompt(
        self,
        step_description: str,
        context: ExecutionContext,
        *,
        latest_data: str,
        memory: str,
    ) -> str:
        plan = context.as_plan_checklist() or "(plan unavailable)"
        notes = "\n".join(context.scratchpad[-5:]) if context.scratchpad else "(없음)"
        fail_log = context.fail_log_summary()
        prompt = (
            self._dialogue_template
            .replace("{{goal}}", context.goal)
            .replace("{{step_description}}", step_description)
            .replace("{{plan_checklist}}", plan)
            .replace("{{fail_log}}", fail_log)
            .replace("{{notes}}", notes)
            .replace("{{latest_data}}", latest_data or "(없음)")
            .replace("{{conversation_history}}", memory or "(최근 대화 기록 없음)")
        )
        return prompt

    def _load_default_template(self) -> str:
        template_path = Path(__file__).resolve().parent / "prompt_templates" / "final_response_prompt.md"
        if template_path.exists():
            return template_path.read_text(encoding="utf-8").strip()

        # Fallback template
        return (
            "당신은 사용자의 목표를 도와주는 친절한 비서입니다.\n"
            "사용자에게 자연스럽고 짧게 응답하세요.\n\n"
            "사용자 목표: {{goal}}\n"
            "현재 단계 설명: {{step_description}}\n"
            "현재 계획 체크리스트:\n{{plan_checklist}}\n\n"
            "최근 실패 로그:\n{{fail_log}}\n\n"
            "추가 메모:\n{{notes}}\n\n"
            "최근 대화 기록:\n{{conversation_history}}\n\n"
            "최근 관찰 데이터:\n{{latest_data}}"
        )

    def compose_final_message(self, context: ExecutionContext) -> str | None:
        if self._brain is None:
            return None

        last_event = self._latest_event(context)
        latest_data, step_description = self._summarise_event(last_event, context)
        memory_text = (
            self._conversation_memory.formatted(limit=10)
            if self._conversation_memory
            else "(최근 대화 기록 없음)"
        )
        self._logger.debug("Final response memory snapshot:\n%s", memory_text)
        prompt = self._build_dialogue_prompt(
            step_description,
            context,
            latest_data=latest_data,
            memory=memory_text,
        )
        self._logger.debug("Generating final response summary")
        try:
            return self._brain.generate_text(prompt, temperature=0.6)
        except EngineError as exc:
            self._logger.warning("최종 응답 생성 실패: %s", exc)
            return None

    def _latest_event(self, context: ExecutionContext) -> StepCompletedEvent | None:
        for event in reversed(context.events):
            if isinstance(event, StepCompletedEvent):
                return event
        return None

    def _latest_observation_text(self, context: ExecutionContext) -> str:
        event = self._latest_event(context)
        if event is None:
            return "(없음)"

        description = None
        for step in context.plan_steps:
            if step.id == event.step_id:
                description = step.description
                break

        data_text = "(데이터 없음)"
        if event.data is not None:
            try:
                data_text = json.dumps(event.data, ensure_ascii=False, indent=2)
            except TypeError:
                data_text = str(event.data)

        if description:
            return f"최근 완료된 단계: #{event.step_id} {description}\n{data_text}"
        return data_text

    def _summarise_event(
        self,
        event: StepCompletedEvent | None,
        context: ExecutionContext,
    ) -> tuple[str, str]:
        if event is None:
            return "(최근 수행 데이터가 없습니다)", "마지막 단계 정보를 찾을 수 없습니다"

        data_text = "(데이터 없음)"
        if event.data is not None:
            try:
                data_text = json.dumps(event.data, ensure_ascii=False, indent=2)
            except TypeError:
                data_text = str(event.data)

        description = "최근 완료된 단계"
        for step in context.plan_steps:
            if step.id == event.step_id:
                description = step.description
                break

        return data_text, description

    def _classify_tool_error(self, message: str) -> tuple[StepOutcome, str]:
        lowered = message.lower()
        transient_keywords = (
            "timeout",
            "time out",
            "temporarily",
            "temporary",
            "rate limit",
            "429",
            "service unavailable",
            "connection reset",
            "network",
            "tls",
        )
        for keyword in transient_keywords:
            if keyword in lowered:
                return StepOutcome.RETRY, "transient"

        if "could not find" in lowered or "does not exist" in lowered:
            return StepOutcome.FAILED, "missing_resource"
        if "invalid" in lowered and "property" in lowered:
            return StepOutcome.FAILED, "invalid_property"
        if "not a property" in lowered:
            return StepOutcome.FAILED, "invalid_property"
        if "unauthorized" in lowered or "permission" in lowered or "forbidden" in lowered:
            return StepOutcome.FAILED, "permission"
        if "api 키" in message or "api key" in lowered:
            return StepOutcome.FAILED, "authentication"

        return StepOutcome.FAILED, "tool_error"
