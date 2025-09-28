"""LLM-powered curator that transforms execution data into memory records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from ai.ai_brain import AIBrain
from ai.core.exceptions import EngineError
from ai.core.logger import get_logger

from .memory_records import MemoryCategory, MemoryRecord, MemorySourceData


CURATOR_MAX_OUTPUT_TOKENS = 4096


class MemoryCurator:
    """Use an LLM to summarise agent activity into a structured memory record."""

    def __init__(self, brain: AIBrain, *, template_path: Optional[Path] = None) -> None:
        self._brain = brain
        self._logger = get_logger(self.__class__.__name__)
        self._template = self._load_template(template_path)

    def curate(self, source: MemorySourceData) -> MemoryRecord:
        prompt = self._render_prompt(source)
        self._logger.debug("Invoking memory curator prompt")
        llm_response = self._brain.generate_text(
            prompt,
            temperature=0.2,
            max_output_tokens=CURATOR_MAX_OUTPUT_TOKENS,
        )
        payload = self._parse_response(llm_response.text)
        return self._build_record(payload, source)

    def _render_prompt(self, source: MemorySourceData) -> str:
        tool_history = json.dumps(source.tool_invocations, ensure_ascii=False, indent=2) or "[]"
        prompt = (
            self._template
            .replace("{{goal}}", source.goal)
            .replace("{{user_request}}", source.user_request)
            .replace("{{plan_checklist}}", source.plan_checklist or "(없음)")
            .replace("{{scratchpad}}", source.scratchpad_digest or "(없음)")
            .replace("{{tool_history}}", tool_history)
            .replace("{{failure_log}}", source.failure_log or "(없음)")
            .replace("{{final_response}}", source.final_response_draft or "(없음)")
        )
        return prompt

    def _parse_response(self, response: str) -> dict[str, object]:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
            self._logger.error("Memory curator 응답 파싱 실패", extra={"response": response})
            raise EngineError("Memory curator가 JSON 형식을 반환하지 않았습니다.") from exc

        if not isinstance(data, dict):
            raise EngineError("Memory curator 응답이 JSON 객체가 아닙니다.")
        return data

    def _build_record(self, payload: dict[str, object], source: MemorySourceData) -> MemoryRecord:
        category = self._resolve_category(payload.get("category"))
        summary = self._coerce_text(payload.get("summary"))
        if not summary:
            raise EngineError("Memory curator가 summary를 제공하지 않았습니다.")

        user_intent = self._coerce_text(payload.get("user_intent")) or source.user_request
        outcome = self._coerce_text(payload.get("outcome")) or "unspecified"
        tools_used = self._coerce_list(payload.get("tools_used"))
        tags = self._coerce_list(payload.get("tags"))

        metadata = dict(source.metadata)
        curator_meta = metadata.get("curator")
        if not isinstance(curator_meta, dict):
            curator_meta = {}
        curator_meta.update({
            "category": category.value,
            "tags": tags,
        })
        metadata["curator"] = curator_meta

        return MemoryRecord(
            summary=summary,
            goal=source.goal,
            user_intent=user_intent,
            outcome=outcome,
            category=category,
            tools_used=tools_used,
            tags=tags,
            source_metadata=metadata,
        )

    def _resolve_category(self, raw: object) -> MemoryCategory:
        if isinstance(raw, str):
            try:
                return MemoryCategory(raw.strip())
            except ValueError:
                pass
        raise EngineError("유효하지 않은 memory category입니다.")

    def _coerce_text(self, value: object) -> str:
        if isinstance(value, str):
            return value.strip()
        return ""

    def _coerce_list(self, value: object) -> List[str]:
        if not isinstance(value, list):
            return []
        items: List[str] = []
        for item in value:
            if isinstance(item, str):
                trimmed = item.strip()
                if trimmed:
                    items.append(trimmed)
        return items

    def _load_template(self, template_path: Optional[Path]) -> str:
        path = template_path or Path(__file__).resolve().parent / "prompts" / "memory_curator_prompt.md"
        if not path.exists():  # pragma: no cover - defensive guard
            raise EngineError(f"Memory curator 템플릿을 찾을 수 없습니다: {path}")
        return path.read_text(encoding="utf-8")
