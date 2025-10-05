"""LLM integration layer for the Personal AI Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

try:
    import google.generativeai as genai
except ImportError as exc:  # pragma: no cover - optional dependency
    genai = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from ai.core.config import Config
from ai.core.exceptions import EngineError
from ai.core.logger import get_logger


@dataclass(frozen=True)
class PromptMessage:
    """Container representing a single message exchanged with the LLM."""

    role: str
    content: str


@dataclass(frozen=True)
class LLMResponse:
    """LLM completion result that includes token usage metadata."""

    text: str
    metadata: Dict[str, Any]


class AIBrain:
    """Adapter responsible for communicating with the Gemini API."""

    def __init__(self, config: Config) -> None:
        if not config.gemini_api_key:
            raise EngineError("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

        if _IMPORT_ERROR is not None or genai is None:
            raise EngineError('google-generativeai 패키지가 설치되어 있지 않습니다. requirements.txt를 확인하세요.') from _IMPORT_ERROR

        self._logger = get_logger(self.__class__.__name__)
        self._model_name = config.gemini_model
        self._configure_client(config.gemini_api_key)
        masked_key = self._mask_key(config.gemini_api_key)
        self._logger.debug(
            "Gemini client configured (model=%s, api_key=%s)",
            self._model_name,
            masked_key,
        )
        self._model = genai.GenerativeModel(self._model_name)

    def generate_text(
        self,
        prompt: str,
        *,
        history: Optional[Sequence[PromptMessage]] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        max_retries: int = 3,
    ) -> LLMResponse:
        """Request a completion from Gemini using an optional conversation history.

        Args:
            max_retries: Gemini 500 에러 발생 시 재시도 횟수 (기본 3회)
        """
        from google.api_core.exceptions import InternalServerError
        import time

        contents = self._build_contents(prompt, history)
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self._model.generate_content(
                    contents,
                    generation_config={
                        "temperature": temperature,
                        **({"max_output_tokens": max_output_tokens} if max_output_tokens else {}),
                    },
                )
                # 성공하면 바로 응답 처리로 진행
                break

            except InternalServerError as exc:
                # Gemini 500 에러는 재시도 가능
                last_error = exc
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    self._logger.warning(
                        f"Gemini 500 에러 발생 (시도 {attempt + 1}/{max_retries}), {wait_time}초 후 재시도..."
                    )
                    time.sleep(wait_time)
                    continue
                # 마지막 재시도도 실패하면 에러 발생
                self._logger.error(f"Gemini API 요청 실패 ({max_retries}회 재시도): {exc}", exc_info=True)
                raise EngineError(f"Gemini API 요청이 실패했습니다 (500 Internal Server Error): {exc}") from exc

            except Exception as exc:  # pragma: no cover - API errors surface at runtime
                # 다른 에러는 즉시 발생
                self._logger.error("Gemini API 요청 실패: %s", exc, exc_info=True)
                raise EngineError(f"Gemini API 요청이 실패했습니다: {exc}") from exc

        response_metadata = self._extract_response_metadata(response)
        response_metadata.update(
            {
                "prompt_length": len(prompt),
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
            }
        )

        try:
            text = self._pick_primary_text(response)
        except ValueError as exc:  # pragma: no cover - surface diagnostics before re-raising
            self._logger.warning(
                "Gemini 응답에서 텍스트 추출에 실패했습니다 (metadata=%s)",
                response_metadata,
            )
            raise

        if not text:
            feedback = getattr(response, "prompt_feedback", None)
            safety = getattr(feedback, "safety_ratings", None) if feedback else None
            self._logger.warning(
                "Gemini 응답이 비어 있습니다 (metadata=%s, feedback=%s, safety=%s)",
                response_metadata,
                str(feedback) if feedback else None,
                str(safety) if safety else None,
            )
            raise EngineError("Gemini API가 비어있는 응답을 반환했습니다.")
        return LLMResponse(text=text, metadata=response_metadata)

    def _configure_client(self, api_key: str) -> None:
        genai.configure(api_key=api_key)
        self._logger.debug("Configured Gemini client for model %s", self._model_name)

    def _build_contents(
        self,
        prompt: str,
        history: Optional[Sequence[PromptMessage]],
    ) -> Iterable[Mapping[str, Any]]:
        messages: list[Mapping[str, Any]] = []
        if history:
            for message in history:
                messages.append({"role": message.role, "parts": [message.content]})
        messages.append({"role": "user", "parts": [prompt]})
        return messages

    def _pick_primary_text(self, response: Any) -> str:
        text_attr = getattr(response, "text", None)
        if isinstance(text_attr, str) and text_attr.strip():
            return text_attr.strip()

        try:
            candidates = response.candidates  # type: ignore[attr-defined]
        except AttributeError as exc:
            raise EngineError("Gemini 응답 포맷이 예상과 다릅니다.") from exc

        for candidate in candidates or []:
            parts = getattr(candidate, "content", None)
            if not parts:
                continue
            text_parts = getattr(parts, "parts", None)
            if isinstance(text_parts, list):
                accumulated_parts: list[str] = []
                for chunk in text_parts:
                    chunk_text = getattr(chunk, "text", None)
                    if isinstance(chunk_text, str) and chunk_text:
                        accumulated_parts.append(chunk_text)
                if accumulated_parts:
                    return "".join(accumulated_parts)
        return ""

    def _extract_response_metadata(self, response: Any) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}

        candidates = getattr(response, "candidates", None)
        if candidates:
            primary = candidates[0]
            finish_reason = getattr(primary, "finish_reason", None)
            if finish_reason is not None:
                metadata["finish_reason"] = str(finish_reason)
            safety = getattr(primary, "safety_ratings", None)
            if safety:
                metadata["safety_ratings"] = str(safety)
            usage = getattr(primary, "usage_metadata", None)
            if usage:
                metadata["usage_metadata"] = {
                    "prompt_token_count": getattr(usage, "prompt_token_count", None),
                    "candidates_token_count": getattr(usage, "candidates_token_count", None),
                    "total_token_count": getattr(usage, "total_token_count", None),
                }

        top_level_usage = getattr(response, "usage_metadata", None)
        if top_level_usage is not None:
            usage_dict = metadata.setdefault("usage_metadata", {})
            for key in ("prompt_token_count", "candidates_token_count", "total_token_count"):
                value = getattr(top_level_usage, key, None)
                if value is not None:
                    usage_dict[key] = value

        prompt_feedback = getattr(response, "prompt_feedback", None)
        if prompt_feedback:
            metadata["prompt_feedback"] = str(prompt_feedback)

        return metadata

    @staticmethod
    def _mask_key(key: str) -> str:
        if len(key) <= 8:
            return "*" * len(key)
        return f"{key[:4]}***{key[-4:]}"
