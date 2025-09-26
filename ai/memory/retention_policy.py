"""Retention policy for deciding when to persist memory records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ai.react_engine.models import ExecutionContext

from .memory_records import MemorySourceData


@dataclass(slots=True)
class MemoryRetentionDecision:
    """Outcome returned by the retention policy."""

    should_store: bool
    reason: str


class MemoryRetentionPolicy:
    """Applies simple heuristics to determine whether to persist a memory."""

    def __init__(
        self,
        *,
        minimum_scratchpad_length: int = 10,
        require_final_response: bool = True,
    ) -> None:
        self._minimum_scratchpad_length = minimum_scratchpad_length
        self._require_final_response = require_final_response

    def evaluate(
        self,
        context: ExecutionContext,
        source: MemorySourceData,
    ) -> MemoryRetentionDecision:
        if self._require_final_response and not source.final_response_draft:
            return MemoryRetentionDecision(
                should_store=False,
                reason="최종 응답이 생성되지 않아 메모리를 저장하지 않습니다.",
            )

        if len(source.scratchpad_digest.strip()) < self._minimum_scratchpad_length:
            return MemoryRetentionDecision(
                should_store=False,
                reason="스크래치패드가 비어 있어 학습 가치가 낮습니다.",
            )

        if self._contains_errors(source):
            return MemoryRetentionDecision(
                should_store=True,
                reason="오류 해결 기록을 학습용으로 저장합니다.",
            )

        if self._new_tool_usage(context, source):
            return MemoryRetentionDecision(
                should_store=True,
                reason="새로운 도구 사용 기록을 저장합니다.",
            )

        return MemoryRetentionDecision(
            should_store=True,
            reason="일반 성공 사례로 저장합니다.",
        )

    def _contains_errors(self, source: MemorySourceData) -> bool:
        if source.failure_log and source.failure_log != "(no failures yet)":
            return True
        for entry in source.tool_invocations:
            error_reason = entry.get("error_reason")
            if isinstance(error_reason, str) and error_reason.strip():
                return True
        return False

    def _new_tool_usage(self, context: ExecutionContext, source: MemorySourceData) -> bool:
        known_tools: Iterable[str] = context.metadata.get("known_tools", [])
        seen = {entry.get("tool") for entry in source.tool_invocations if entry.get("tool")}
        return any(tool not in known_tools for tool in seen)
