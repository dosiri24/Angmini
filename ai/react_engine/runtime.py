"""Runtime helpers for wiring the ReAct engine into interfaces."""

from __future__ import annotations

from ai.ai_brain import AIBrain
from ai.core.config import Config
from ai.core.exceptions import EngineError
from mcp.tool_manager import ToolManager

from .agent_scratchpad import AgentScratchpad
from .goal_executor import GoalExecutor
from .loop_detector import LoopDetector
from .planning_engine import PlanningEngine
from .safety_guard import SafetyGuard
from .step_executor import StepExecutor


class GoalExecutorFactory:
    """Build fresh ``GoalExecutor`` instances while reusing shared services."""

    def __init__(self, config: Config, tool_manager: ToolManager) -> None:
        self._tool_manager = tool_manager
        self._brain = self._initialise_brain(config)

    def _initialise_brain(self, config: Config) -> AIBrain:
        try:
            return AIBrain(config)
        except EngineError:
            # Bubble up engine errors so interfaces can translate them to user-friendly messages.
            raise

    def create(self) -> GoalExecutor:
        """Return a goal executor with fresh per-run state (safety, scratchpad)."""
        safety_guard = SafetyGuard()
        scratchpad = AgentScratchpad()
        step_executor = StepExecutor(self._tool_manager, brain=self._brain)
        loop_detector = LoopDetector()
        planning_engine = PlanningEngine(safety_guard)
        return GoalExecutor(
            brain=self._brain,
            tool_manager=self._tool_manager,
            step_executor=step_executor,
            safety_guard=safety_guard,
            scratchpad=scratchpad,
            loop_detector=loop_detector,
            planning_engine=planning_engine,
        )


__all__ = ["GoalExecutorFactory"]
