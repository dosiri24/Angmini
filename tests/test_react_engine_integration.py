"""Integration test covering GoalExecutor + FileTool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ai.core.logger import setup_logging
from ai.react_engine import AgentScratchpad, GoalExecutor, LoopDetector, SafetyGuard, StepExecutor
from mcp import create_default_tool_manager


class DummyBrain:
    """LLM stub that returns a predefined JSON plan."""

    def __init__(self, plan_json: str) -> None:
        self._plan_json = plan_json

    def generate_text(self, prompt: str) -> str:  # pragma: no cover - simple stub
        return self._plan_json


@pytest.mark.parametrize("operation", ["list", "read", "write"])
def test_goal_executor_with_file_tool(tmp_path: Path, operation: str) -> None:
    setup_logging("WARNING")

    target_dir = tmp_path / "workspace"
    target_dir.mkdir()
    sample_file = target_dir / "sample.txt"
    sample_file.write_text("hello", encoding="utf-8")

    if operation == "list":
        parameters: dict[str, Any] = {"operation": "list", "path": str(target_dir)}
    elif operation == "read":
        parameters = {"operation": "read", "path": str(sample_file)}
    else:  # write
        parameters = {
            "operation": "write",
            "path": str(target_dir / "written.txt"),
            "content": "integration-test",
        }

    plan_json = (
        "[{"
        "\"id\": 1,"
        "\"description\": \"use file tool\","
        "\"tool\": \"file\","
        "\"parameters\": "
        + json_dumps(parameters)
        + ","
        "\"status\": \"todo\"}]"
    )

    brain = DummyBrain(plan_json)
    tool_manager = create_default_tool_manager()
    step_executor = StepExecutor(tool_manager)
    safety_guard = SafetyGuard()
    scratchpad = AgentScratchpad()
    goal_executor = GoalExecutor(
        brain=brain,
        tool_manager=tool_manager,
        step_executor=step_executor,
        safety_guard=safety_guard,
        scratchpad=scratchpad,
        loop_detector=LoopDetector(repeat_threshold=2),
    )

    context = goal_executor.run("File tool integration test")

    assert all(step.status.value == "done" for step in context.plan_steps)
    assert not context.fail_log

    if operation == "write":
        written_file = target_dir / "written.txt"
        assert written_file.exists()
        assert written_file.read_text(encoding="utf-8") == "integration-test"
    elif operation == "read":
        last_event = context.events[-1]
        assert getattr(last_event, "data", None) is not None
    else:
        last_event = context.events[-1]
        assert getattr(last_event, "data", None) is not None


def json_dumps(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False)
