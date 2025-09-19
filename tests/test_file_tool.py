"""Unit tests for the FileTool helper operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp.tools.file_tool import FileTool


def test_file_tool_move_operation(tmp_path: Path) -> None:
    tool = FileTool()

    source = tmp_path / "source.txt"
    source.write_text("content", encoding="utf-8")

    destination_dir = tmp_path / "dest"
    destination = destination_dir / "moved.txt"

    result = tool(operation="move", path=str(source), destination=str(destination))

    moved_info = result.unwrap()
    assert moved_info["source"].endswith("source.txt")
    assert Path(moved_info["destination"]).exists()
    assert not source.exists()
    assert destination.read_text(encoding="utf-8") == "content"


def test_file_tool_trash_operation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tool = FileTool()

    target = tmp_path / "trash_me.txt"
    target.write_text("trash", encoding="utf-8")

    trashed_paths: list[str] = []

    def fake_send2trash(path: str) -> None:
        trashed_paths.append(path)
        Path(path).unlink()

    monkeypatch.setattr("mcp.tools.file_tool.send2trash", fake_send2trash)

    result = tool(operation="trash", path=str(target))

    trashed_info = result.unwrap()
    assert trashed_info == {"path": str(target), "action": "trashed"}
    assert trashed_paths == [str(target)]
    assert not target.exists()

