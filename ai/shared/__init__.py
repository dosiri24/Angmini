"""
Shared components used across multiple systems (CrewAI, Memory, etc.)

This module contains core data models and utilities that are not specific
to any particular execution engine but are shared across the application.
"""

from ai.shared.models import (
    ExecutionContext,
    PlanStep,
    PlanStepStatus,
    StepCompletedEvent,
)
from ai.shared.loop_detector import LoopDetector

__all__ = [
    "ExecutionContext",
    "PlanStep",
    "PlanStepStatus",
    "StepCompletedEvent",
    "LoopDetector",
]
