"""File operations tool tailored for macOS environments."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Type, Optional

from send2trash import send2trash
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger

from ..tool_blueprint import ToolBlueprint, ToolResult

# 프로그램 루트 경로 (절대 경로)
PROGRAM_ROOT = Path(__file__).parent.parent.parent.resolve()


class FileTool(ToolBlueprint):
    """Provides read/write/list filesystem capabilities."""

    tool_name = "file"
    description = "파일 읽기/쓰기/목록 조회 도구"
    parameters: Dict[str, Any] = {
        "operation": {
            "type": "string",
            "enum": ["read", "write", "list", "move", "trash"],
            "description": "수행할 작업 종류",
        },
        "path": {
            "type": "string",
            "description": "대상 파일 또는 디렉토리 경로",
        },
        "destination": {
            "type": "string",
            "description": "move 작업 시 이동할 경로",
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
        if operation not in {"read", "write", "list", "move", "trash"}:
            raise ToolError("operation 파라미터는 read/write/list/move/trash 중 하나여야 합니다.")

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
            if operation == "move":
                destination_raw = kwargs.get("destination")
                if not isinstance(destination_raw, str) or not destination_raw.strip():
                    raise ToolError("move 작업에는 destination 문자열이 필요합니다.")
                destination_path = self._resolve_path(destination_raw)
                return self._move_path(target_path, destination_path)
            if operation == "trash":
                return self._move_to_trash(target_path)

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

    def _move_path(self, source: Path, destination: Path) -> ToolResult:
        if not source.exists():
            raise ToolError(f"이동할 경로를 찾을 수 없습니다: {source}")

        source_resolved = source.resolve()
        destination_resolved = destination.resolve(strict=False)
        if source_resolved == destination_resolved:
            raise ToolError("source와 destination이 동일합니다.")

        try:
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
            moved_to = Path(shutil.move(str(source), str(destination)))
        except Exception as exc:  # pragma: no cover - shutil errors depend on filesystem state
            raise ToolError(f"파일 이동에 실패했습니다: {exc}") from exc

        return ToolResult(
            success=True,
            data={"source": str(source_resolved), "destination": str(moved_to.resolve())},
        )

    def _move_to_trash(self, path: Path) -> ToolResult:
        if not path.exists():
            raise ToolError(f"휴지통으로 이동할 파일을 찾을 수 없습니다: {path}")

        try:
            send2trash(str(path))
        except Exception as exc:  # pragma: no cover - third-party failure
            raise ToolError(f"휴지통 이동에 실패했습니다: {exc}") from exc

        return ToolResult(success=True, data={"path": str(path), "action": "trashed"})

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


# ====================================================================
# CrewAI Adapter
# ====================================================================


class FileToolInput(BaseModel):
    """FileTool 입력 스키마"""
    operation: str = Field(..., description="Operation to perform: read_file, write_file, list_directory, move_file, trash_file")
    path: str = Field(default=".", description="File or directory path (absolute path recommended)")
    content: Optional[str] = Field(default=None, description="Content to write (for write_file operation)")
    destination: Optional[str] = Field(default=None, description="Destination path (for move_file operation)")
    recursive: Optional[bool] = Field(default=False, description="Include subdirectories (for list_directory)")
    include_hidden: Optional[bool] = Field(default=False, description="Include hidden files (for list_directory)")


class FileCrewAITool(BaseTool):
    """CrewAI adapter for FileTool"""
    name: str = "파일 시스템 도구"
    description: str = f"""파일 읽기/쓰기, 디렉토리 목록, 파일 이동/삭제를 수행합니다.

    **프로그램 루트 경로**: {PROGRAM_ROOT}
    **사용자 홈 디렉토리**: {Path.home()}
    **사용자 바탕화면**: {Path.home() / 'Desktop'}

    **중요**: 모든 경로는 절대 경로를 사용하세요. 상대 경로는 예상치 못한 결과를 초래할 수 있습니다.
    """
    args_schema: Type[BaseModel] = FileToolInput

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = get_logger(__name__)
        self._file_tool = FileTool()

    def _run(
        self,
        operation: str,
        path: str = ".",
        content: Optional[str] = None,
        destination: Optional[str] = None,
        recursive: Optional[bool] = False,
        include_hidden: Optional[bool] = False,
        **kwargs: Any
    ) -> str:
        """도구 실행 - FileTool의 run() 메서드를 호출하여 실제 작업 수행

        CrewAI operation → FileTool operation 매핑:
        - read_file → read
        - write_file → write
        - list_directory → list
        - move_file → move
        - trash_file → trash
        """
        # Operation 매핑
        operation_mapping = {
            "read_file": "read",
            "write_file": "write",
            "list_directory": "list",
            "move_file": "move",
            "trash_file": "trash",
            # 레거시 호환성
            "read": "read",
            "write": "write",
            "list": "list",
            "move": "move",
            "trash": "trash",
        }

        mapped_operation = operation_mapping.get(operation)
        if not mapped_operation:
            error_msg = f"❌ 지원하지 않는 작업: {operation}. 사용 가능한 작업: {', '.join(operation_mapping.keys())}"
            self._logger.error(f"[FileCrewAITool] {error_msg}")
            return error_msg

        # 전체 파라미터 상세 로깅
        import json
        all_params = {
            "operation": operation,
            "mapped_operation": mapped_operation,
            "path": path,
            "content": (content[:100] + "...") if content and len(content) > 100 else content,
            "destination": destination,
            "recursive": recursive,
            "include_hidden": include_hidden,
            **kwargs
        }
        # None 값 제거
        logged_params = {k: v for k, v in all_params.items() if v is not None}
        self._logger.info(f"🔧 [FileCrewAITool] 실행 시작 - 파라미터: {json.dumps(logged_params, ensure_ascii=False, default=str)}")

        # FileTool 호출용 파라미터 구성
        params = {"operation": mapped_operation, "path": path}

        if content is not None:
            params["content"] = content
        if destination is not None:
            params["destination"] = destination
        if recursive is not None:
            params["recursive"] = recursive
        if include_hidden is not None:
            params["include_hidden"] = include_hidden

        self._logger.debug(f"[FileCrewAITool] FileTool로 전달할 파라미터: {json.dumps({k: (v[:100] + '...' if isinstance(v, str) and len(v) > 100 else v) for k, v in params.items()}, ensure_ascii=False, default=str)}")

        try:
            # FileTool의 run() 메서드 호출
            self._logger.debug(f"[FileCrewAITool] FileTool.run() 호출 중...")
            result: ToolResult = self._file_tool(**params)

            # 결과 검증 및 상세 로깅
            if result.success:
                # 성공 시 데이터 검증
                if not result.data:
                    warning_msg = "⚠️ 성공했으나 결과 데이터가 비어있음"
                    self._logger.warning(f"[FileCrewAITool] {warning_msg}")
                    return f"✅ 작업 완료 (데이터 없음)"

                # 결과 데이터 상세 로깅 (200자 제한)
                data_str = json.dumps(result.data, ensure_ascii=False, default=str)
                data_preview = data_str[:200] + ("..." if len(data_str) > 200 else "")
                self._logger.info(f"✅ [FileCrewAITool] 성공 - 결과: {data_preview}")

                # 성공 메시지 포맷팅
                return self._format_success_response(result.data, mapped_operation, path)
            else:
                # 실패 시 에러 상세 로깅 (200자 제한)
                error_str = str(result.error) if result.error else "알 수 없는 에러"
                error_preview = error_str[:200] + ("..." if len(error_str) > 200 else "")
                self._logger.error(f"❌ [FileCrewAITool] 실패 - 에러: {error_preview}")
                return f"❌ 파일 작업 실패: {error_preview}"

        except ToolError as e:
            # ToolError는 FileTool에서 발생한 예상된 에러
            error_str = str(e)[:200]
            self._logger.error(f"❌ [FileCrewAITool] ToolError - {error_str}")
            return f"❌ 파일 도구 에러: {error_str}"
        except Exception as e:
            # 예상치 못한 에러
            error_str = str(e)[:200]
            self._logger.exception(f"❌ [FileCrewAITool] 예상치 못한 에러 - {error_str}")
            return f"❌ 도구 실행 중 예외 발생: {error_str}"

    def _format_success_response(self, data: Any, operation: str, path: str) -> str:
        """성공 응답을 사용자 친화적인 형식으로 변환"""
        import json

        if isinstance(data, dict):
            if "entries" in data:
                # list_directory 결과
                entries = data["entries"]
                output = f"✅ 디렉토리 목록 ({len(entries)}개 항목):\n"
                output += f"📁 경로: {data.get('path', path)}\n\n"
                for entry in entries:
                    icon = "📁" if entry["type"] == "directory" else "📄"
                    output += f"{icon} {entry['name']} ({entry['path']})\n"
                self._logger.info(f"[FileCrewAITool] 디렉토리 목록 조회 성공 - {len(entries)}개 항목")
                return output

            elif "content" in data:
                # read_file 결과
                content_preview = data['content'][:200]
                if len(data['content']) > 200:
                    content_preview += "..."
                self._logger.info(f"[FileCrewAITool] 파일 읽기 성공 - 경로: {data.get('path', path)}, 크기: {len(data['content'])}자")
                return f"✅ 파일 읽기 성공:\n📄 경로: {data.get('path', path)}\n\n내용:\n{content_preview}"

            elif "action" in data and data["action"] == "trashed":
                # trash_file 결과
                self._logger.info(f"[FileCrewAITool] 휴지통 이동 성공 - 경로: {data.get('path', path)}")
                return f"✅ 휴지통으로 이동 완료:\n📄 {data.get('path', path)}"

            elif "source" in data and "destination" in data:
                # move_file 결과
                self._logger.info(f"[FileCrewAITool] 파일 이동 성공 - {data['source']} → {data['destination']}")
                return f"✅ 파일 이동 완료:\n📄 {data['source']} → {data['destination']}"

            else:
                return f"✅ 성공:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
        else:
            return f"✅ 성공: {data}"
