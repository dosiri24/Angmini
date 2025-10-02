"""Registry and dispatcher for MCP tools."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger

from .tool_blueprint import ToolBlueprint, ToolResult


class ToolManager:
    """Maintain the catalogue of available tools and execute them on demand."""

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._tools: Dict[str, ToolBlueprint] = {}

    def register(self, tool: ToolBlueprint) -> None:
        """Register a tool instance, replacing an existing one with the same name."""
        name = tool.tool_name
        if name in self._tools:
            self._logger.warning("Tool '%s'이 이미 등록되어 있어 새 인스턴스로 교체합니다.", name)
        self._tools[name] = tool

    def unregister(self, name: str) -> None:
        if name not in self._tools:
            raise ToolError(f"등록되지 않은 도구 '{name}' 입니다.")
        del self._tools[name]
        self._logger.debug("Tool '%s' 등록 해제", name)

    def execute(self, name: str, **kwargs: Any) -> ToolResult:
        tool = self.get(name)
        return tool(**kwargs)

    def get(self, name: str) -> ToolBlueprint:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolError(f"도구 '{name}' 를 찾을 수 없습니다.") from exc

    def list(self) -> Mapping[str, Mapping[str, Any]]:
        return {name: tool.schema() for name, tool in self._tools.items()}

    def registered_names(self) -> Iterable[str]:
        return tuple(self._tools.keys())
