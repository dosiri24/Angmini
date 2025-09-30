"""Data contracts for the adaptive memory subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryCategory(str, Enum):
    """High-level grouping for stored experiences."""

    FULL_EXPERIENCE = "full_experience"
    ERROR_SOLUTION = "error_solution"
    TOOL_USAGE = "tool_usage"
    USER_PATTERN = "user_pattern"
    WORKFLOW_OPTIMISATION = "workflow_optimisation"


@dataclass(slots=True)
class MemorySourceData:
    """Raw ingredients gathered before running the memory curator."""

    goal: str
    user_request: str
    plan_checklist: str
    scratchpad_digest: str
    tool_invocations: List[Dict[str, Any]] = field(default_factory=list)
    failure_log: str = ""
    final_response_draft: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MemoryRecord:
    """Normalised representation saved to the long-term store."""

    summary: str
    goal: str
    user_intent: str
    outcome: str
    category: MemoryCategory
    tools_used: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    source_metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_document(self) -> Dict[str, Any]:
        """Flatten the record for JSON or database storage."""
        return {
            "summary": self.summary,
            "goal": self.goal,
            "user_intent": self.user_intent,
            "outcome": self.outcome,
            "category": self.category.value,
            "tools_used": list(self.tools_used),
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
            "source_metadata": dict(self.source_metadata),
            "embedding": list(self.embedding) if self.embedding is not None else None,
        }
