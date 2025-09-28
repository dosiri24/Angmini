"""Tests for the memory curation pipeline."""

from __future__ import annotations

from datetime import datetime

import pytest

from ai.memory.deduplicator import MemoryDeduplicator
from ai.memory.memory_curator import MemoryCurator
from ai.memory.pipeline import MemoryPipeline
from ai.memory.retention_policy import MemoryRetentionPolicy
from ai.memory.snapshot_extractor import SnapshotExtractor
from ai.memory.memory_records import MemoryCategory, MemoryRecord
from ai.react_engine.models import (
    ExecutionContext,
    FailureLogEntry,
    PlanStep,
    PlanStepStatus,
    StepCompletedEvent,
    StepOutcome,
)


class DummyBrain:
    def __init__(self, response: str) -> None:
        self.response = response

    def generate_text(self, prompt: str, **kwargs):  # noqa: ANN007 - match AIBrain
        return self.response


def _build_context() -> ExecutionContext:
    context = ExecutionContext(goal="사용자 일정 정리")
    step = PlanStep(
        id=1,
        description="노션에 일정 기록",
        tool_name="notion",
        parameters={"operation": "create_task"},
        status=PlanStepStatus.DONE,
    )
    context.plan_steps = [step]
    context.append_scratch("goal established: 사용자 일정 정리")
    context.append_scratch("executing step #1: 노션에 일정 기록")
    context.append_scratch("step #1 완료")
    context.record_event(
        StepCompletedEvent(
            step_id=1,
            outcome=StepOutcome.SUCCESS,
            data={"tool": "notion"},
        )
    )
    context.metadata["final_message"] = "일정을 노션에 정리했습니다."
    return context


def _build_pipeline(brain: DummyBrain) -> MemoryPipeline:
    curator = MemoryCurator(brain)
    policy = MemoryRetentionPolicy(minimum_scratchpad_length=5)
    snapshot = SnapshotExtractor()
    deduplicator = MemoryDeduplicator()
    return MemoryPipeline(snapshot, policy, curator, deduplicator=deduplicator)


def test_memory_pipeline_creates_record_when_retention_allows(tmp_path):
    response = (
        '{"summary": "사용자의 일정 요청을 정리하고 성공적으로 기록함",'
        ' "user_intent": "일정을 정리하고 공유",'
        ' "outcome": "성공",'
        ' "category": "full_experience",'
        ' "tools_used": ["notion"],'
        ' "tags": ["schedule", "success"]}'
    )
    pipeline = _build_pipeline(DummyBrain(response))
    context = _build_context()

    result = pipeline.run(context, user_request="오늘 일정을 정리해줘")

    assert result.retention.should_store is True
    assert result.record is not None
    record = result.record
    assert record.category == MemoryCategory.FULL_EXPERIENCE
    assert record.tools_used == ["notion"]
    assert record.user_intent == "일정을 정리하고 공유"
    assert result.duplicate_of is None


def test_memory_pipeline_merges_duplicates():
    response = (
        '{"summary": "사용자 일정 정리 경험을 기록",'
        ' "user_intent": "일정을 정리하고 공유",'
        ' "outcome": "성공",'
        ' "category": "full_experience",'
        ' "tools_used": ["notion"],'
        ' "tags": ["schedule"]}'
    )
    pipeline = _build_pipeline(DummyBrain(response))
    context = _build_context()

    existing = MemoryRecord(
        summary="사용자 일정 정리 경험 기록",
        goal=context.goal,
        user_intent="일정을 정리하고 공유",
        outcome="성공",
        category=MemoryCategory.FULL_EXPERIENCE,
        tools_used=["notion"],
        tags=["success"],
        created_at=datetime.utcnow(),
        source_metadata={"note": "manual"},
    )

    result = pipeline.run(
        context,
        user_request="오늘 일정을 정리해줘",
        existing_records=[existing],
    )

    assert result.record is not None
    assert result.duplicate_of is existing
    assert sorted(result.record.tags) == ["schedule", "success"]
    assert result.record.summary in {
        "사용자 일정 정리 경험 기록",
        "사용자 일정 정리 경험을 기록",
    }


def test_memory_retention_records_resolved_failures():
    response = (
        '{"summary": "오류 후 일정을 성공적으로 정리",'
        ' "user_intent": "일정을 정리",'
        ' "outcome": "성공",'
        ' "category": "full_experience",'
        ' "tools_used": ["notion"],'
        ' "tags": ["success"]}'
    )
    pipeline = _build_pipeline(DummyBrain(response))
    context = _build_context()
    context.add_failure(
        FailureLogEntry(
            step_id=1,
            command="{\"tool\": \"notion\"}",
            error_message="API 오류",
            attempt=1,
        )
    )

    result = pipeline.run(context, user_request="오늘 일정을 정리해줘")

    assert result.retention.should_store is True
    assert result.retention.reason == "오류를 해결한 성공 사례를 저장합니다."
