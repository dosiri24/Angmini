"""Integration test covering GoalExecutor + FileTool."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

import pytest

from ai.core.logger import setup_logging
from ai.react_engine import AgentScratchpad, GoalExecutor, LoopDetector, SafetyGuard, StepExecutor
from mcp import create_default_tool_manager
from mcp.tool_manager import ToolManager
from mcp.tool_blueprint import ToolBlueprint, ToolResult
from ai.core.exceptions import ToolError


class DummyBrain:
    """LLM stub that returns a predefined JSON plan."""

    def __init__(self, plan_json: str) -> None:
        self._plan_json = plan_json

    def generate_text(self, prompt: str) -> str:  # pragma: no cover - simple stub
        return self._plan_json


class SequencedBrain:
    """LLM stub that cycles through predefined responses."""

    def __init__(self, responses: List[str], final_response: str = "완료") -> None:
        self._responses = responses
        self._final_response = final_response
        self._index = 0

    def generate_text(self, prompt: str, temperature: float | None = None) -> str:  # pragma: no cover
        if self._index < len(self._responses):
            response = self._responses[self._index]
        else:
            response = self._final_response
        self._index += 1
        return response


class DummyNotionTool(ToolBlueprint):
    tool_name = "notion"
    description = "dummy notion tool"
    parameters = {
        "operation": {"type": "string"},
        "page_id": {"type": "string"},
        "relations": {"type": "array"},
    }

    def __init__(self) -> None:
        super().__init__()
        self.list_calls = 0
        self.update_calls: List[dict[str, Any]] = []

    def run(self, **kwargs: Any) -> ToolResult:
        operation = kwargs.get("operation")
        if operation == "list_tasks":
            self.list_calls += 1
            return ToolResult(
                success=True,
                data={
                    "items": [
                        {
                            "id": "task-1",
                            "title": "온라인 스시모 듣기",
                        }
                    ]
                },
            )
        if operation == "update_task":
            self.update_calls.append(kwargs)
            return ToolResult(
                success=True,
                data={"operation": "update_task", "id": kwargs.get("page_id")},
            )
        raise ToolError(f"Unsupported operation: {operation}")


@pytest.mark.parametrize("operation", ["list", "read", "write", "move", "trash"])
def test_goal_executor_with_file_tool(
    tmp_path: Path, operation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup_logging("WARNING")

    target_dir = tmp_path / "workspace"
    target_dir.mkdir()
    sample_file = target_dir / "sample.txt"
    sample_file.write_text("hello", encoding="utf-8")

    move_destination: Optional[Path] = None
    trash_target: Optional[Path] = None
    trashed_paths: List[str] = []

    if operation == "list":
        parameters: dict[str, Any] = {"operation": "list", "path": str(target_dir)}
    elif operation == "read":
        parameters = {"operation": "read", "path": str(sample_file)}
    elif operation == "write":
        parameters = {
            "operation": "write",
            "path": str(target_dir / "written.txt"),
            "content": "integration-test",
        }
    elif operation == "move":
        move_destination = target_dir / "moved" / sample_file.name
        parameters = {
            "operation": "move",
            "path": str(sample_file),
            "destination": str(move_destination),
        }
    else:  # trash
        trash_target = target_dir / "trash.txt"
        trash_target.write_text("bye", encoding="utf-8")

        def fake_send2trash(path: str) -> None:
            trashed_paths.append(path)
            Path(path).unlink()

        monkeypatch.setattr("mcp.tools.file_tool.send2trash", fake_send2trash)

        parameters = {"operation": "trash", "path": str(trash_target)}

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
    elif operation == "move":
        assert move_destination is not None
        assert move_destination.exists()
        assert not sample_file.exists()
    elif operation == "trash":
        assert trash_target is not None
        assert trashed_paths == [str(trash_target)]
        assert not trash_target.exists()
    else:
        last_event = context.events[-1]
        assert getattr(last_event, "data", None) is not None


def test_goal_executor_requests_follow_up_after_read_only_plan() -> None:
    setup_logging("WARNING")

    tool_manager = ToolManager()
    notion_tool = DummyNotionTool()
    tool_manager.register(notion_tool)

    plan_read_only = (
        "[{"
        "\"id\": 1,"
        "\"description\": \"비어 있는 프로젝트 속성 확인\","
        "\"tool\": \"notion\","
        "\"parameters\": "
        + json_dumps({"operation": "list_tasks"})
        + ","
        "\"status\": \"todo\"}]"
    )

    plan_update = (
        "[{"
        "\"id\": 1,"
        "\"description\": \"조회한 할 일을 알맞은 프로젝트에 연결\","
        "\"tool\": \"notion\","
        "\"parameters\": "
        + json_dumps(
            {
                "operation": "update_task",
                "page_id": "task-1",
                "relations": ["proj-1"],
            }
        )
        + ","
        "\"status\": \"todo\"}]"
    )

    brain = SequencedBrain([plan_read_only, plan_update], final_response="프로젝트를 연결했습니다.")
    step_executor = StepExecutor(tool_manager, brain=brain)
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

    context = goal_executor.run("Notion 관계 채우기 테스트")

    assert notion_tool.list_calls == 1
    assert len(notion_tool.update_calls) == 1
    assert context.metadata.get("auto_followup_replans") == 1
    assert all(step.status.value == "done" for step in context.plan_steps)
    assert not context.fail_log


def json_dumps(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False)
