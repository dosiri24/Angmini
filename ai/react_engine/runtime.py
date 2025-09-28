"""Runtime helpers for wiring the ReAct engine into interfaces."""

from __future__ import annotations

from ai.ai_brain import AIBrain
from ai.core.config import Config
from ai.core.exceptions import EngineError
from ai.core.logger import get_logger
from mcp.tool_manager import ToolManager

try:
    from ai.memory import MemoryService
except Exception:  # pragma: no cover - optional dependency guard
    MemoryService = None  # type: ignore[assignment]

from .agent_scratchpad import AgentScratchpad
from .conversation_memory import ConversationMemory
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
        self._memory = ConversationMemory()
        self._memory_service = self._initialise_memory_support()

    def _initialise_brain(self, config: Config) -> AIBrain:
        try:
            return AIBrain(config)
        except EngineError:
            # Bubble up engine errors so interfaces can translate them to user-friendly messages.
            raise

    def _initialise_memory_support(self):
        logger = get_logger(self.__class__.__name__)
        if MemoryService is None:
            logger.debug("Memory components unavailable; disabling automatic memory capture.")
            return None

        try:
            service = MemoryService.build(self._brain)  # type: ignore[call-arg]
            from mcp.tools.memory_tool import MemoryTool

            try:
                self._tool_manager.register(
                    MemoryTool(
                        repository=service.repository,
                        metrics=service.metrics,
                    )
                )
            except Exception as tool_exc:  # pragma: no cover - defensive guard
                logger.warning("MemoryTool registration failed: %s", tool_exc)
            return service
        except Exception as exc:  # pragma: no cover - optional dependency guard
            logger.warning("Memory support disabled: %s", exc)
            return None

    def create(self) -> GoalExecutor:
        """Return a goal executor with fresh per-run state (safety, scratchpad)."""
        safety_guard = SafetyGuard()
        scratchpad = AgentScratchpad()
        step_executor = StepExecutor(
            self._tool_manager,
            brain=self._brain,
            conversation_memory=self._memory,
        )
        loop_detector = LoopDetector()
        planning_engine = PlanningEngine(safety_guard)
        logger = get_logger(self.__class__.__name__)
        logger.debug(
            "Creating GoalExecutor with conversation memory id=%s (size=%d)",
            id(self._memory),
            len(self._memory),
        )
        memory_service = self._memory_service
        return GoalExecutor(
            brain=self._brain,
            tool_manager=self._tool_manager,
            step_executor=step_executor,
            safety_guard=safety_guard,
            scratchpad=scratchpad,
            loop_detector=loop_detector,
            planning_engine=planning_engine,
            conversation_memory=self._memory,
            memory_service=memory_service,
        )

    def record_turn(self, user_text: str, assistant_text: str | None) -> None:
        """Persist a completed user/assistant exchange into shared memory."""
        self._memory.add_turn(user_text, assistant_text)


__all__ = ["GoalExecutorFactory"]
