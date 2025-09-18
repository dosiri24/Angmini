"""LLM integration layer for the Personal AI Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence

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
        self._model = genai.GenerativeModel(self._model_name)

    def generate_text(
        self,
        prompt: str,
        *,
        history: Optional[Sequence[PromptMessage]] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        """Request a completion from Gemini using an optional conversation history."""
        contents = self._build_contents(prompt, history)
        try:
            response = self._model.generate_content(
                contents,
                generation_config={
                    "temperature": temperature,
                    **({"max_output_tokens": max_output_tokens} if max_output_tokens else {}),
                },
            )
        except Exception as exc:  # pragma: no cover - API errors surface at runtime
            raise EngineError("Gemini API 요청이 실패했습니다.") from exc

        text = self._pick_primary_text(response)
        if not text:
            raise EngineError("Gemini API가 비어있는 응답을 반환했습니다.")
        return text

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
        try:
            candidates = response.candidates  # type: ignore[attr-defined]
        except AttributeError as exc:
            raise EngineError("Gemini 응답 포맷이 예상과 다릅니다.") from exc

        for candidate in candidates or []:
            parts = getattr(candidate, "content", None)
            if not parts:
                continue
            text = getattr(parts, "parts", None)
            if isinstance(text, list):
                accumulated = "".join(str(chunk.text) for chunk in text if getattr(chunk, "text", None))
                if accumulated:
                    return accumulated
        return ""
