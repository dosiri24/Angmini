"""Data structures shared across the ReAct engine components."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PlanStepStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class StepOutcome(str, Enum):
    SUCCESS = "success"
    RETRY = "retry"
    FAILED = "failed"


@dataclass(slots=True)
class PlanStep:
    """Represents a single action that the agent must execute."""

    id: int
    description: str
    tool_name: Optional[str]
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: PlanStepStatus = PlanStepStatus.TODO

    def mark_in_progress(self) -> None:
        self.status = PlanStepStatus.IN_PROGRESS

    def mark_done(self) -> None:
        self.status = PlanStepStatus.DONE

    def to_prompt_fragment(self) -> str:
        status_symbol = {
            PlanStepStatus.TODO: "[ ]",
            PlanStepStatus.IN_PROGRESS: "[~]",
            PlanStepStatus.DONE: "[x]",
        }[self.status]
        tool_part = f" tool={self.tool_name}" if self.tool_name else ""
        return f"{status_symbol} #{self.id}{tool_part}: {self.description}"


@dataclass(slots=True)
class StepResult:
    """Outcome returned by the StepExecutor."""

    step_id: int
    outcome: StepOutcome
    data: Optional[Any] = None
    error_reason: Optional[str] = None
    attempt: int = 1

    def should_retry(self, max_attempts: int) -> bool:
        return self.outcome == StepOutcome.RETRY and self.attempt < max_attempts


@dataclass(slots=True)
class FailureLogEntry:
    """Captures a single failure attempt for later reflection."""

    step_id: int
    command: Optional[str]
    error_message: str
    attempt: int
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_prompt_fragment(self) -> str:
        command_part = f" command={self.command}" if self.command else ""
        return (
            f"step={self.step_id}, attempt={self.attempt}{command_part}, error={self.error_message}"
        )


@dataclass(slots=True)
class ExecutionContext:
    """Holds the mutable state of a single agent session."""

    goal: str
    plan_steps: List[PlanStep] = field(default_factory=list)
    current_step_index: Optional[int] = None
    fail_log: List[FailureLogEntry] = field(default_factory=list)
    scratchpad: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    events: List[PlanEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def record_event(self, event: PlanEvent) -> None:
        self.events.append(event)

    def current_step(self) -> Optional[PlanStep]:
        if self.current_step_index is None:
            return None
        if self.current_step_index < 0 or self.current_step_index >= len(self.plan_steps):
            return None
        return self.plan_steps[self.current_step_index]

    def remaining_steps(self) -> List[PlanStep]:
        return [step for step in self.plan_steps if step.status != PlanStepStatus.DONE]

    def as_plan_checklist(self) -> str:
        return "\n".join(step.to_prompt_fragment() for step in self.plan_steps)

    def add_failure(self, failure: FailureLogEntry) -> None:
        self.fail_log.append(failure)

    def fail_log_summary(self, limit: int = 5) -> str:
        entries = self.fail_log[-limit:]
        if not entries:
            return "(no failures yet)"
        return "\n".join(entry.to_prompt_fragment() for entry in entries)

    def append_scratch(self, note: str) -> None:
        self.scratchpad.append(note)


@dataclass(slots=True)
class PlanEvent:
    """Base class for events that describe plan changes."""

    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class PlanUpdatedEvent(PlanEvent):
    plan_steps: List[PlanStep] = field(default_factory=list)
    reason: Optional[str] = None


@dataclass(slots=True)
class StepCompletedEvent(PlanEvent):
    step_id: int = 0
    outcome: StepOutcome = StepOutcome.SUCCESS
    data: Optional[Any] = None
    error_reason: Optional[str] = None
