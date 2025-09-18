"""Base classes and data structures for MCP tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Mapping, Optional

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger


@dataclass(slots=True)
class ToolResult:
    """Outcome returned by tool executions."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None

    def unwrap(self) -> Any:
        """Return the payload on success, otherwise raise a ``ToolError``."""
        if not self.success:
            raise ToolError(self.error or "Tool execution failed without additional context.")
        return self.data


class ToolBlueprint(ABC):
    """Abstract foundation for all tools usable by the agent."""

    tool_name: ClassVar[str]
    description: ClassVar[str] = ""
    parameters: ClassVar[Mapping[str, Any]] = {}

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._validate_metadata()

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool logic and return a ``ToolResult``."""

    def __call__(self, **kwargs: Any) -> ToolResult:
        try:
            result = self.run(**kwargs)
        except ToolError:
            raise
        except Exception as exc:  # pragma: no cover - runtime failures depend on concrete tool
            raise ToolError(f"Tool '{self.tool_name}' execution crashed: {exc}") from exc

        if not isinstance(result, ToolResult):
            raise ToolError(f"Tool '{self.tool_name}' must return ToolResult instances.")
        return result

    def schema(self) -> Dict[str, Any]:
        """Expose a schema-like description to help planning components."""
        return {
            "name": self.tool_name,
            "description": self.description,
            "parameters": dict(self.parameters),
        }

    def _validate_metadata(self) -> None:
        name = getattr(self, "tool_name", "").strip()
        if not name:
            raise ToolError("ToolBlueprint subclasses must define non-empty 'tool_name'.")
        if not isinstance(self.parameters, Mapping):
            raise ToolError("ToolBlueprint.parameters must be a mapping object.")
