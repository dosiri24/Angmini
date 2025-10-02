"""Utilities for producing concise summaries of tool execution results."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .models import PlanStep


def summarize_step_result(step: PlanStep | None, data: Any, *, max_length: int = 220) -> str:
    """Generate a short, human-readable description of a tool result."""
    summary = _summarize_data_payload(data, max_length=max_length)
    if summary:
        return summary
    if step is not None and step.description:
        return f"{step.description} 완료"
    return "작업이 성공적으로 완료되었습니다."


def summarize_data_snapshot(data: Any, *, max_length: int = 220) -> str:
    """Summarize arbitrary data for inclusion in prompts/debug output."""
    summary = _summarize_data_payload(data, max_length=max_length)
    if summary:
        return summary
    return "(결과 요약 불가)"


def _summarize_data_payload(data: Any, *, max_length: int) -> str:
    if data is None:
        return "(결과 없음)"

    if isinstance(data, str):
        return _truncate(data, max_length)

    if isinstance(data, Mapping):
        summary = _summarize_mapping(data, max_length=max_length)
        if summary:
            return summary

    if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        if not data:
            return "빈 목록을 반환했습니다."
        leading = ", ".join(_truncate(str(item), 40) for item in list(data)[:3])
        extra = len(data) - 3
        if extra > 0:
            return _truncate(f"목록 {len(data)}개 항목 (예: {leading}, 외 {extra}개)", max_length)
        return _truncate(f"목록 {len(data)}개 항목 (예: {leading})", max_length)

    try:
        serialised = json.dumps(data, ensure_ascii=False, default=str)
    except TypeError:
        serialised = str(data)
    return _truncate(serialised, max_length)


def _summarize_mapping(payload: Mapping[str, Any], *, max_length: int) -> str:
    # Notion page updates
    notion_page = payload.get("object")
    if notion_page == "page":
        title = _extract_notion_title(payload)
        props = payload.get("properties")
        relation_hints = _relation_hints(props)
        status_hint = _status_hint(props)
        summary_parts: list[str] = ["Notion 페이지"]
        if title:
            summary_parts.append(f"'{title}'")
        summary_parts.append("업데이트 완료")
        details: list[str] = []
        if relation_hints:
            details.append(f"관계: {relation_hints}")
        if status_hint:
            details.append(f"상태: {status_hint}")
        if details:
            summary_parts.append(f"({'; '.join(details)})")
        return _truncate(" ".join(summary_parts), max_length)

    # Generic list style response
    if "items" in payload and isinstance(payload["items"], Sequence):
        items = payload["items"]  # type: ignore[assignment]
        count = len(items)
        preview = _preview_titles(items)
        text = f"목록 {count}개 항목 로드"
        if preview:
            text += f" (예: {preview})"
        return _truncate(text, max_length)

    if "results" in payload and isinstance(payload["results"], Sequence):
        results = payload["results"]  # type: ignore[assignment]
        count = len(results)
        preview = _preview_titles(results)
        text = f"목록 {count}개 항목 로드"
        if preview:
            text += f" (예: {preview})"
        return _truncate(text, max_length)

    if "id" in payload and "url" in payload:
        title = payload.get("title") or payload.get("name")
        if isinstance(title, str) and title:
            return _truncate(f"'{title}' 엔트리를 업데이트했습니다.", max_length)

    return ""


def _extract_notion_title(payload: Mapping[str, Any]) -> str | None:
    title = payload.get("title") or payload.get("name")
    if isinstance(title, str) and title.strip():
        return title.strip()

    properties = payload.get("properties")
    if isinstance(properties, Mapping):
        for value in properties.values():
            if not isinstance(value, Mapping):
                continue
            prop_type = value.get("type")
            if prop_type == "title":
                title_value = value.get("title")
                plain = _extract_plain_text(title_value)
                if plain:
                    return plain
            if prop_type == "rich_text":
                text_value = value.get("rich_text")
                plain = _extract_plain_text(text_value)
                if plain:
                    return plain
    return None


def _relation_hints(properties: Any) -> str | None:
    if not isinstance(properties, Mapping):
        return None
    hints: list[str] = []
    for name, value in properties.items():
        if not isinstance(value, Mapping):
            continue
        if value.get("type") == "relation":
            relation_items = value.get("relation")
            if isinstance(relation_items, Sequence):
                hints.append(f"{name} {len(relation_items)}개")
    if hints:
        return ", ".join(hints)
    return None


def _status_hint(properties: Any) -> str | None:
    if not isinstance(properties, Mapping):
        return None
    for value in properties.values():
        if not isinstance(value, Mapping):
            continue
        if value.get("type") == "status":
            status_value = value.get("status")
            if isinstance(status_value, Mapping):
                name = status_value.get("name")
                if isinstance(name, str) and name:
                    return name
    return None


def _preview_titles(items: Sequence[Any]) -> str:
    previews: list[str] = []
    for item in items[:3]:
        if isinstance(item, Mapping):
            title = _extract_notion_title(item)
            if title:
                previews.append(_truncate(title, 40))
                continue
            name = item.get("name")
            if isinstance(name, str) and name:
                previews.append(_truncate(name, 40))
                continue
        previews.append(_truncate(str(item), 40))
    return ", ".join(previews)


def _extract_plain_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, Sequence):
        texts: list[str] = []
        for entry in value:
            if isinstance(entry, Mapping):
                text = entry.get("plain_text") or entry.get("text")
                if isinstance(text, Mapping):
                    content = text.get("content")
                    if isinstance(content, str) and content:
                        texts.append(content)
                        continue
                if isinstance(text, str) and text:
                    texts.append(text)
        if texts:
            return "".join(texts)
    return None


def _truncate(text: str, max_length: int) -> str:
    text = text.strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


__all__ = [
    "summarize_step_result",
    "summarize_data_snapshot",
]
