"""Executes individual plan steps by invoking registered tools."""

from __future__ import annotations

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger
from mcp.tool_manager import ToolManager

from .models import ExecutionContext, PlanStep, StepOutcome, StepResult


class StepExecutor:
    """Handles execution of a single `PlanStep`."""

    def __init__(self, tool_manager: ToolManager) -> None:
        self._tool_manager = tool_manager
        self._logger = get_logger(self.__class__.__name__)

    def execute(self, step: PlanStep, context: ExecutionContext, attempt: int) -> StepResult:
        if not step.tool_name:
            error = "Plan step에 사용할 도구가 지정되지 않았습니다."
            self._logger.error(error)
            return StepResult(
                step_id=step.id,
                outcome=StepOutcome.FAILED,
                error_reason=error,
                attempt=attempt,
            )

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
            self._logger.warning("Step %s 실패: %s", step.id, message)
            return StepResult(
                step_id=step.id,
                outcome=StepOutcome.RETRY,
                error_reason=message,
                attempt=attempt,
            )
