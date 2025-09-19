"""Tooling infrastructure for the Personal AI Assistant."""

from __future__ import annotations

from .tool_blueprint import ToolBlueprint, ToolResult  # noqa: F401
from .tool_manager import ToolManager  # noqa: F401
from .tools import FileTool, NotionTool  # noqa: F401

__all__ = [
    "FileTool",
    "NotionTool",
    "ToolBlueprint",
    "ToolResult",
    "ToolManager",
    "create_default_tool_manager",
]


def create_default_tool_manager() -> ToolManager:
    """Return a ToolManager pre-populated with built-in tools."""
    manager = ToolManager()
    manager.register(FileTool())
    manager.register(NotionTool())
    return manager
