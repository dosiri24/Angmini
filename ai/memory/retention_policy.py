"""Retention policy for deciding when to persist memory records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Set

from ai.shared.models import ExecutionContext

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

        final_message = (context.metadata.get("final_message") or "").strip()

        if self._contains_errors(source):
            if final_message:
                return MemoryRetentionDecision(
                    should_store=True,
                    reason="오류를 해결한 성공 사례를 저장합니다.",
                )
            return MemoryRetentionDecision(
                should_store=False,
                reason="해결되지 않은 오류 기록이므로 저장하지 않습니다.",
            )

        if self._new_tool_usage(context, source):
            return MemoryRetentionDecision(
                should_store=True,
                reason="새로운 도구 사용 기록을 저장합니다.",
            )

        if self._is_low_information_response(source):
            return MemoryRetentionDecision(
                should_store=False,
                reason="최종 응답이 '모른다' 등 유의미한 정보가 없어 저장하지 않습니다.",
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

    def _is_low_information_response(self, source: MemorySourceData) -> bool:
        response = (source.final_response_draft or "").strip().lower()
        if not response:
            return False

        response_tokens = self._tokenize_text(response)
        if not response_tokens:
            return True

        has_tool_activity = any(entry.get("tool") for entry in source.tool_invocations)
        if has_tool_activity or self._contains_errors(source):
            return False

        user_tokens = self._tokenize_text(source.user_request)
        novel_tokens = response_tokens.difference(user_tokens)

        novelty_ratio = (
            len(novel_tokens) / len(response_tokens)
            if response_tokens
            else 0.0
        )

        # Treat extremely short answers with almost no new vocabulary as low-information responses.
        if len(response) <= 25 and len(novel_tokens) <= 2:
            return True

        # When most tokens overlap with the user's request and the response itself is tiny,
        # we assume the assistant admitted a lack of knowledge rather than conveying new facts.
        if novelty_ratio < 0.25 and len(response_tokens) <= 6:
            return True

        return False

    @staticmethod
    def _tokenize_text(text: str) -> Set[str]:
        normalized = "".join(ch if ch.isalnum() else " " for ch in text.lower())
        return {token for token in normalized.split() if token}
