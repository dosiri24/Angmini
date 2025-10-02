"""Adaptive ReAct executor that plans dynamically based on observations."""

from __future__ import annotations

from typing import Optional
from ai.core.logger import get_logger
from .models import ExecutionContext, PlanStep, PlanStepStatus, StepCompletedEvent
from .step_executor import StepExecutor
from .goal_executor import GoalExecutor


class AdaptiveReActExecutor:
    """
    Executes goals using adaptive planning:
    1. Plan next single step based on current context
    2. Execute step
    3. Observe result
    4. Repeat until goal achieved or max iterations reached
    """

    MAX_STEPS = 15

    def __init__(
        self,
        goal_executor: GoalExecutor,
        step_executor: StepExecutor,
    ):
        self._goal_exec = goal_executor
        self._step_exec = step_executor
        self._logger = get_logger(self.__class__.__name__)

    def run(self, goal: str) -> str:
        """Execute goal adaptively with dynamic planning."""
        context = ExecutionContext(goal=goal)

        for iteration in range(1, self.MAX_STEPS + 1):
            self._logger.info(f"🔄 Adaptive iteration {iteration}/{self.MAX_STEPS}")

            # 1. Ask LLM: What's the next single step?
            next_step = self._plan_next_step(context)

            if next_step is None:
                # LLM says goal is complete
                break

            # 2. Execute step
            result = self._step_exec.execute(next_step, context, attempt=1)

            # 3. Handle result (success or failure)
            self._goal_exec._handle_step_result(context, next_step, result)

            # 4. Check if goal achieved
            if self._is_goal_complete(context):
                break

        # Generate final response
        return self._step_exec.compose_final_message(context) or "Goal completed."

    def _plan_next_step(self, context: ExecutionContext) -> Optional[PlanStep]:
        """Ask LLM for next single step based on current state."""
        prompt = self._build_adaptive_prompt(context)
        response = self._goal_exec._brain.generate_text(prompt)
        context.record_token_usage(response.metadata, "thinking")

        # Parse single-step plan
        plan = self._goal_exec._parse_plan_response(response.text)

        if not plan:
            return None  # LLM says done

        if len(plan) > 1:
            self._logger.warning("LLM returned multi-step plan, using only first step")

        return plan[0]

    def _build_adaptive_prompt(self, context: ExecutionContext) -> str:
        """Build prompt asking for next single step."""
        observations = self._goal_exec._format_all_observations(context)

        return (
            f"{self._goal_exec._system_prompt}\n\n"
            f"User Goal: {context.goal}\n\n"
            f"Progress So Far:\n{observations}\n\n"
            f"Recent Failures:\n{context.fail_log_summary()}\n\n"
            f"🎯 What is the NEXT SINGLE STEP to achieve the goal?\n"
            f"Return JSON array with ONE step, or empty array [] if goal is complete.\n"
            f"CRITICAL: Use only concrete values from observations above."
        )

    def _is_goal_complete(self, context: ExecutionContext) -> bool:
        """Ask LLM if goal is achieved."""
        observations = self._goal_exec._format_all_observations(context)

        prompt = (
            f"User Goal: {context.goal}\n\n"
            f"Actions Completed:\n{observations}\n\n"
            f"Is the goal fully achieved? Answer 'YES' or 'NO' with brief reason."
        )

        response = self._goal_exec._brain.generate_text(prompt, temperature=0.3)
        answer = response.text.strip().upper()

        return answer.startswith("YES")