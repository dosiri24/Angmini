"""Tooling infrastructure for the Personal AI Assistant."""

from __future__ import annotations

import platform

from .tool_blueprint import ToolBlueprint, ToolResult  # noqa: F401
from .tool_manager import ToolManager  # noqa: F401
from .tools import AppleTool, FileTool, NotionTool  # noqa: F401

__all__ = [
    "AppleTool",
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
    
    # Apple Tool은 macOS에서만 등록
    if platform.system() == "Darwin":
        try:
            manager.register(AppleTool())
        except Exception as exc:
            # Apple MCP 설정이 완료되지 않은 경우 무시 (로그는 AppleTool에서 처리)
            pass
    
    return manager
