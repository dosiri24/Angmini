"""Custom exception hierarchy for the Personal AI Assistant."""

from __future__ import annotations


class AIProjectError(Exception):
    """Base class for project-specific exceptions."""


class ConfigError(AIProjectError):
    """Raised when configuration loading or validation fails."""


class ToolError(AIProjectError):
    """Raised when a tool action fails or yields an invalid response."""


class EngineError(AIProjectError):
    """Raised when the ReAct engine encounters an unrecoverable issue."""


class InterfaceError(AIProjectError):
    """Raised when an interface cannot be resolved or executed."""


class PromptLoadError(AIProjectError):
    """Raised when an agent prompt markdown file cannot be loaded or parsed."""
