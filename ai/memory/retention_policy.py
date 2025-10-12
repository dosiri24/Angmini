"""Retention policy for deciding when to persist memory records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, Optional, Set

from ai.shared.models import ExecutionContext

from .memory_records import MemorySourceData

if TYPE_CHECKING:
    from ai.ai_brain import AIBrain


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
        brain: Optional["AIBrain"] = None,
    ) -> None:
        self._minimum_scratchpad_length = minimum_scratchpad_length
        self._require_final_response = require_final_response
        self._brain = brain

    def evaluate(
        self,
        context: ExecutionContext,
        source: MemorySourceData,
    ) -> MemoryRetentionDecision:
        """
        메모리 저장 정책: 다음 세 가지 경우만 저장
        1. 사용자의 개인정보 또는 개인적 특징
        2. 도구 실패 후 최종적으로 성공한 경우
        3. 그 외는 모두 저장하지 않음
        """
        if self._require_final_response and not source.final_response_draft:
            return MemoryRetentionDecision(
                should_store=False,
                reason="최종 응답이 생성되지 않아 메모리를 저장하지 않습니다.",
            )

        # 조건 1: 사용자 개인정보 탐지
        if self._contains_personal_info(source):
            return MemoryRetentionDecision(
                should_store=True,
                reason="사용자 개인정보/특징을 포함하므로 저장합니다.",
            )

        # 조건 2: 도구 실패 후 성공한 경우
        final_message = (context.metadata.get("final_message") or "").strip()
        if self._contains_errors(source):
            if final_message:
                return MemoryRetentionDecision(
                    should_store=True,
                    reason="도구 실패 후 성공한 사례를 저장합니다.",
                )
            # 실패만 있고 성공 안 한 경우 저장 안 함
            return MemoryRetentionDecision(
                should_store=False,
                reason="해결되지 않은 실패이므로 저장하지 않습니다.",
            )

        # 그 외 모든 경우: 저장하지 않음
        return MemoryRetentionDecision(
            should_store=False,
            reason="개인정보나 실패 해결 사례가 아니므로 저장하지 않습니다.",
        )

    def _contains_personal_info(self, source: MemorySourceData) -> bool:
        """
        사용자 개인정보 포함 여부를 LLM으로 탐지

        다음을 포함하면 True:
        - 이름 (내 이름은, 나는 ~야/입니다)
        - 전공/학과 정보
        - 수강 과목
        - 취향/선호도
        - 일정/스케줄
        - 할당된 작업/과제

        개인정보 보호: 로컬 pre-filter로 명백한 패턴만 LLM 전송
        """
        if not self._brain:
            # AIBrain이 없으면 보수적으로 False 반환
            return False

        # 모든 텍스트 소스를 결합
        combined_text = "\n".join([
            f"사용자 요청: {source.user_request}",
            f"목표: {source.goal or '(없음)'}",
            f"스크래치패드: {source.scratchpad_digest or '(없음)'}",
            f"최종 응답: {source.final_response_draft or '(없음)'}",
        ])

        # 개인정보 보호: 로컬 pre-filter로 명백한 패턴 체크
        # 이메일, 전화번호 등 민감 정보는 LLM에 전송하지 않음
        import re
        text_lower = combined_text.lower()

        # 명백한 개인정보 패턴 (빠른 로컬 체크)
        obvious_patterns = [
            r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',  # 이메일
            r'\b\d{3}[-.]?\d{3,4}[-.]?\d{4}\b',  # 전화번호
            r'\b\d{6}[-]\d{7}\b',  # 주민등록번호 패턴
        ]

        for pattern in obvious_patterns:
            if re.search(pattern, combined_text):
                # 명백한 개인정보는 LLM 전송 없이 바로 True
                return True

        # 명백한 패턴이 없으면 안전한 키워드만 LLM으로 판단
        safe_keywords = ["이름", "전공", "학과", "수강", "과목", "취향", "일정", "스케줄", "과제", "프로젝트"]
        has_safe_keyword = any(keyword in text_lower for keyword in safe_keywords)

        if not has_safe_keyword:
            # 개인정보 관련 키워드 없으면 False
            return False

        # LLM 프롬프트 (민감 정보 제거된 컨텍스트만 전송)
        # 최대 500자로 제한하여 전송 데이터 최소화
        truncated_text = combined_text[:500]
        prompt = f"""다음 대화 내용에 사용자의 개인정보가 포함되어 있는지 판단하세요.

개인정보 기준:
- 사용자의 이름
- 전공, 학과, 수강 과목
- 개인적 취향이나 선호도
- 일정, 스케줄, 약속
- 할당된 작업, 과제, 프로젝트

대화 내용:
{truncated_text}

위 내용에 개인정보가 포함되어 있으면 "YES", 없으면 "NO"만 정확히 답변하세요."""

        try:
            response = self._brain.generate_text(
                prompt,
                temperature=0.1,  # 일관성 있는 판단을 위해 낮은 temperature
                max_output_tokens=10,
            )
            answer = response.text.strip().upper()
            # 프롬프트 인젝션 방지: 정확한 매칭만 허용
            return answer == "YES"
        except Exception:
            # LLM 호출 실패 시 보수적으로 False 반환
            return False

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
