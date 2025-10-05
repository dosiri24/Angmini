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

        # 단순 대화도 저장하도록 조건 완화
        # 사용자가 정보를 제공한 경우 (예: "이번 학기에 자료구조 들어요")도 저장해야 함

        user_tokens = self._tokenize_text(source.user_request)
        novel_tokens = response_tokens.difference(user_tokens)

        novelty_ratio = (
            len(novel_tokens) / len(response_tokens)
            if response_tokens
            else 0.0
        )

        # 너무 짧고 거의 새로운 정보가 없는 응답만 필터링 (조건 완화)
        # 예: "네", "알겠습니다", "좋아요" 같은 극단적으로 짧은 응답만 제외
        if len(response) <= 15 and len(novel_tokens) <= 1:  # 기존: 25자, 2단어 → 15자, 1단어로 완화
            return True

        # 응답이 30자 이상이면 무조건 저장 (단순 대화라도 정보 가치가 있을 수 있음)
        if len(response) >= 30:
            return False

        # 극단적으로 짧고 새로운 정보가 거의 없는 경우만 필터링
        if novelty_ratio < 0.15 and len(response_tokens) <= 4:  # 기존: 0.25, 6단어 → 0.15, 4단어로 완화
            return True

        return False

    @staticmethod
    def _tokenize_text(text: str) -> Set[str]:
        normalized = "".join(ch if ch.isalnum() else " " for ch in text.lower())
        return {token for token in normalized.split() if token}
