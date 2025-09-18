"""File operations tool tailored for macOS environments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger

from ..tool_blueprint import ToolBlueprint, ToolResult


class FileTool(ToolBlueprint):
    """Provides read/write/list filesystem capabilities."""

    tool_name = "file"
    description = "파일 읽기/쓰기/목록 조회 도구"
    parameters: Dict[str, Any] = {
        "operation": {
            "type": "string",
            "enum": ["read", "write", "list"],
            "description": "수행할 작업 종류",
        },
        "path": {
            "type": "string",
            "description": "대상 파일 또는 디렉토리 경로",
        },
        "content": {
            "type": "string",
            "description": "쓰기 작업 시 사용할 콘텐츠",
        },
        "recursive": {
            "type": "boolean",
            "description": "목록 조회 시 하위 디렉토리까지 포함할지 여부",
        },
        "include_hidden": {
            "type": "boolean",
            "description": "숨김 파일을 포함할지 여부",
        },
    }

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)

    def run(self, **kwargs: Any) -> ToolResult:
        operation = kwargs.get("operation")
        if operation not in {"read", "write", "list"}:
            raise ToolError("operation 파라미터는 read/write/list 중 하나여야 합니다.")

        raw_path = kwargs.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ToolError("path 파라미터는 비어있지 않은 문자열이어야 합니다.")

        target_path = self._resolve_path(raw_path)

        try:
            if operation == "read":
                return self._read_file(target_path)
            if operation == "write":
                content = kwargs.get("content")
                if not isinstance(content, str):
                    raise ToolError("write 작업에는 content 문자열이 필요합니다.")
                return self._write_file(target_path, content)
            recursive = bool(kwargs.get("recursive", False))
            include_hidden = bool(kwargs.get("include_hidden", False))
            return self._list_directory(target_path, recursive, include_hidden)
        except ToolError:
            raise
        except Exception as exc:  # pragma: no cover - unexpected filesystem errors
            raise ToolError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, raw: str) -> Path:
        path = Path(raw).expanduser()
        try:
            resolved = path.resolve(strict=False)
        except FileNotFoundError:
            resolved = path.resolve(strict=False)
        self._logger.debug("Resolved path '%s' -> '%s'", raw, resolved)
        return resolved

    def _read_file(self, path: Path) -> ToolResult:
        if not path.exists() or not path.is_file():
            raise ToolError(f"파일을 찾을 수 없습니다: {path}")
        text = path.read_text(encoding="utf-8")
        return ToolResult(success=True, data={"path": str(path), "content": text})

    def _write_file(self, path: Path, content: str) -> ToolResult:
        if path.is_dir():
            raise ToolError("디렉토리 경로에는 파일을 쓸 수 없습니다.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(success=True, data={"path": str(path), "bytes_written": len(content.encode('utf-8'))})

    def _list_directory(self, path: Path, recursive: bool, include_hidden: bool) -> ToolResult:
        if not path.exists() or not path.is_dir():
            raise ToolError(f"디렉토리를 찾을 수 없습니다: {path}")

        entries: List[Dict[str, Any]] = []
        iterator = path.rglob("*") if recursive else path.iterdir()
        for entry in iterator:
            name = entry.name
            if not include_hidden and name.startswith("."):
                continue
            entries.append(
                {
                    "name": name,
                    "path": str(entry.resolve()),
                    "type": "directory" if entry.is_dir() else "file",
                }
            )
        return ToolResult(success=True, data={"path": str(path.resolve()), "entries": entries})
