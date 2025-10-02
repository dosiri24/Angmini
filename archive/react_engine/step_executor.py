"""Executes individual plan steps by invoking registered tools."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

from ai.ai_brain import AIBrain
from ai.core.exceptions import EngineError, ToolError
from ai.core.logger import get_logger
from mcp.tool_manager import ToolManager

from .conversation_memory import ConversationMemory
from .models import ExecutionContext, PlanStep, StepCompletedEvent, StepOutcome, StepResult
from .result_formatter import summarize_step_result


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

        # Basic parameter validation (placeholders, basic UUID format)
        validation_error = self._validate_parameters(step.parameters)
        if validation_error:
            self._logger.error("[STEP-%s] Parameter validation failed: %s", step.id, validation_error)
            return StepResult(
                step_id=step.id,
                outcome=StepOutcome.FAILED,
                error_reason=f"❌ Invalid parameter detected: {validation_error}\n"
                            f"💡 Hint: Use actual values from previous step results, not placeholders.",
                attempt=attempt,
            )

        # Tool-specific validation (if tool implements validate_parameters)
        try:
            tool = self._tool_manager.get(step.tool_name)
            if hasattr(tool, 'validate_parameters'):
                is_valid, tool_error = tool.validate_parameters(**step.parameters)
                if not is_valid:
                    self._logger.error("[STEP-%s] Tool validation failed: %s", step.id, tool_error)
                    return StepResult(
                        step_id=step.id,
                        outcome=StepOutcome.FAILED,
                        error_reason=tool_error or "Tool-specific validation failed",
                        attempt=attempt,
                    )
        except ToolError:
            # Tool not found - will fail in execute() below
            pass

        # Log key parameters
        self._log_tool_parameters(step)

        try:
            tool_result = self._tool_manager.execute(step.tool_name, **step.parameters)
            data = tool_result.unwrap()

            # Log success with result summary
            operation = step.parameters.get("operation", "")
            result_summary = self._summarize_tool_result(step.tool_name, operation, data)
            if operation:
                self._logger.info("[STEP-%s] Success: %s.%s - %s", step.id, step.tool_name, operation, result_summary)
            else:
                self._logger.info("[STEP-%s] Success: %s - %s", step.id, step.tool_name, result_summary)
            return StepResult(
                step_id=step.id,
                outcome=StepOutcome.SUCCESS,
                data=data,
                attempt=attempt,
            )
        except ToolError as exc:
            message = str(exc)
            outcome, category = self._classify_tool_error(message)
            log_action = "retry" if outcome == StepOutcome.RETRY else "replan"
            self._logger.warning("[STEP-%s] Failed (%s): %s", step.id, log_action, message)
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
        prompt = self._build_dialogue_prompt(
            step.description,
            context,
            latest_data=latest_data,
            memory=memory_text,
        )
        self._logger.debug("[STEP-%s] Generating dialogue response", step.id)
        try:
            llm_response = self._brain.generate_text(prompt, temperature=0.6)
        except EngineError as exc:
            self._logger.warning("대화 응답 생성 실패: %s", exc)
            return StepResult(
                step_id=step.id,
                outcome=StepOutcome.RETRY,
                error_reason=str(exc),
                attempt=attempt,
            )

        context.record_token_usage(llm_response.metadata, category="final")
        message = llm_response.text

        self._logger.info("[STEP-%s] Dialogue response complete", step.id)
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
            .replace("{{plan_results}}", context.plan_results_digest())
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
        prompt = self._build_dialogue_prompt(
            step_description,
            context,
            latest_data=latest_data,
            memory=memory_text,
        )
        self._logger.debug("[RESULT] Generating final response")
        try:
            llm_response = self._brain.generate_text(prompt, temperature=0.6)
        except EngineError as exc:
            self._logger.warning("최종 응답 생성 실패: %s", exc)
            return None

        context.record_token_usage(llm_response.metadata, category="final")
        return llm_response.text

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
        matched_step: PlanStep | None = None
        for step in context.plan_steps:
            if step.id == event.step_id:
                description = step.description
                matched_step = step
                break

        summary = summarize_step_result(matched_step, event.data)

        if description:
            return f"최근 완료된 단계: #{event.step_id} {description}\n결과: {summary}"
        return summary

    def _summarise_event(
        self,
        event: StepCompletedEvent | None,
        context: ExecutionContext,
    ) -> tuple[str, str]:
        if event is None:
            return "(최근 수행 데이터가 없습니다)", "마지막 단계 정보를 찾을 수 없습니다"

        matched_step: PlanStep | None = None
        for step in context.plan_steps:
            if step.id == event.step_id:
                matched_step = step
                break

        description = matched_step.description if matched_step else "최근 완료된 단계"
        summary = summarize_step_result(matched_step, event.data)
        return summary, description

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

    def _validate_parameters(self, params: Dict[str, Any]) -> Optional[str]:
        """Detect placeholder patterns in parameters."""
        FORBIDDEN_PATTERNS = ["<", ">", "{{", "}}", "placeholder", "플레이스홀더", "동적으로", "결정"]

        for key, value in params.items():
            if isinstance(value, str):
                if any(pattern in value.lower() for pattern in FORBIDDEN_PATTERNS):
                    return f"Parameter '{key}' contains placeholder: '{value}'"
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str) and any(p in item.lower() for p in FORBIDDEN_PATTERNS):
                        return f"Parameter '{key}[{i}]' contains placeholder: '{item}'"

        # UUID validation for known fields
        if "page_id" in params:
            page_id = params["page_id"]
            if not self._is_valid_uuid(page_id):
                return f"page_id '{page_id}' is not a valid UUID"

        return None

    def _is_valid_uuid(self, value: str) -> bool:
        """Check if string is a valid UUID v4 or Notion page ID format."""
        import re
        # Notion IDs can be with or without hyphens, 32 hex chars
        NOTION_ID_PATTERN = r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$'
        # Also accept 32 hex chars without hyphens
        NOTION_ID_NO_HYPHEN = r'^[0-9a-f]{32}$'

        return bool(
            re.match(NOTION_ID_PATTERN, value, re.IGNORECASE) or
            re.match(NOTION_ID_NO_HYPHEN, value, re.IGNORECASE)
        )

    def _log_tool_parameters(self, step: PlanStep) -> None:
        """Log key parameters for the tool call."""
        import os

        # Key parameters to always log
        key_params = ["operation", "query", "title", "page_id", "filter", "limit", "app"]

        if os.getenv("LOG_TOOL_PARAMS") == "true":
            # Log all parameters
            self._logger.debug("[STEP-%s] Calling %s with params: %s", step.id, step.tool_name, step.parameters)
        else:
            # Log only key parameters
            filtered_params = {k: v for k, v in step.parameters.items() if k in key_params}
            if filtered_params:
                self._logger.debug("[STEP-%s] Calling %s with %s", step.id, step.tool_name, filtered_params)

    def _summarize_tool_result(self, tool_name: str, operation: str, data: Any) -> str:
        """Generate a concise summary of the tool execution result."""
        import os

        if os.getenv("LOG_TOOL_RESULTS") == "true":
            # Return full data (truncated)
            return str(data)[:200]

        if not isinstance(data, dict):
            return str(data)[:50]

        # Notion-specific summaries
        if tool_name == "notion":
            if operation in ["list_tasks", "list_projects", "list_todos"]:
                # Notion always uses "items" key for all list operations
                if "items" in data and isinstance(data["items"], list):
                    count = len(data["items"])
                    # Count items without relations
                    no_relation_count = sum(
                        1 for item in data["items"]
                        if not item.get("relations") or len(item.get("relations", [])) == 0
                    )
                    if no_relation_count > 0:
                        return f"Found {count} items ({no_relation_count} without relations)"
                    return f"Found {count} items"

            elif operation in ["create_task", "update_task", "create_todo", "update_todo"]:
                page_id = data.get("id", "unknown")
                title = data.get("title", "")
                return f"Modified '{title[:30]}...' (ID: {page_id[:8]}...)"

        # File tool summaries
        elif tool_name == "file":
            if operation == "list":
                if "files" in data and isinstance(data["files"], list):
                    return f"Found {len(data['files'])} files"
            elif operation == "read":
                content_len = len(data.get("content", ""))
                return f"Read {content_len} chars"

        # Apple tool summaries
        elif tool_name == "apple":
            if "count" in data:
                return f"Found {data['count']} items"
            elif "success" in data:
                return "Success"

        # Generic summary
        if "id" in data:
            return f"ID: {data['id'][:20]}"

        return "OK"
