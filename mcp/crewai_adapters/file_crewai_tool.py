"""
mcp/crewai_adapters/file_crewai_tool.py
기존 FileTool을 CrewAI BaseTool로 래핑
"""
from crewai.tools import BaseTool
from typing import Type, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from mcp.tools.file_tool import FileTool, ToolResult
from ai.core.logger import get_logger


# 프로그램 루트 경로 (절대 경로)
PROGRAM_ROOT = Path(__file__).parent.parent.parent.resolve()


class FileToolInput(BaseModel):
    """FileTool 입력 스키마"""
    operation: str = Field(..., description="Operation to perform: read_file, write_file, list_directory, move_file, trash_file")
    path: str = Field(default=".", description="File or directory path (absolute path recommended)")
    content: Optional[str] = Field(default=None, description="Content to write (for write_file operation)")
    destination: Optional[str] = Field(default=None, description="Destination path (for move_file operation)")
    recursive: Optional[bool] = Field(default=False, description="Include subdirectories (for list_directory)")
    include_hidden: Optional[bool] = Field(default=False, description="Include hidden files (for list_directory)")


class FileCrewAITool(BaseTool):
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
        """도구 실행

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
            return f"❌ 지원하지 않는 작업: {operation}. 사용 가능한 작업: {', '.join(operation_mapping.keys())}"

        # 입력 파라미터 상세 로깅
        params_log = f"operation={operation} (→ {mapped_operation}), path={path}"
        if content:
            params_log += f", content={content[:50]}..." if len(content) > 50 else f", content={content}"
        if destination:
            params_log += f", destination={destination}"
        if recursive:
            params_log += f", recursive={recursive}"
        if include_hidden:
            params_log += f", include_hidden={include_hidden}"
        self._logger.info(f"🔧 [FileTool] 실행 - {params_log}")

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

        try:
            result: ToolResult = self._file_tool(**params)
            if result.success:
                self._logger.info(f"✅ [FileTool] 성공")
            else:
                self._logger.warning(f"❌ [FileTool] 실패: {result.error}")

            # 결과를 문자열로 변환
            if result.success:
                import json
                # data가 딕셔너리인 경우 포맷팅
                if isinstance(result.data, dict):
                    if "entries" in result.data:
                        # list_directory 결과
                        entries = result.data["entries"]
                        output = f"✅ 디렉토리 목록 ({len(entries)}개 항목):\n"
                        output += f"📁 경로: {result.data.get('path', path)}\n\n"
                        for entry in entries:
                            icon = "📁" if entry["type"] == "directory" else "📄"
                            output += f"{icon} {entry['name']} ({entry['path']})\n"
                        return output
                    elif "content" in result.data:
                        # read_file 결과
                        content_preview = result.data['content'][:200]
                        if len(result.data['content']) > 200:
                            content_preview += "..."
                        return f"✅ 파일 읽기 성공:\n📄 경로: {result.data.get('path', path)}\n\n내용:\n{content_preview}"
                    elif "action" in result.data and result.data["action"] == "trashed":
                        # trash_file 결과
                        return f"✅ 휴지통으로 이동 완료:\n📄 {result.data.get('path', path)}"
                    elif "source" in result.data and "destination" in result.data:
                        # move_file 결과
                        return f"✅ 파일 이동 완료:\n📄 {result.data['source']} → {result.data['destination']}"
                    else:
                        return f"✅ 성공:\n{json.dumps(result.data, indent=2, ensure_ascii=False)}"
                else:
                    return f"✅ 성공: {result.data}"
            else:
                return f"❌ 실패: {result.error}"
        except Exception as e:
            self._logger.error(f"도구 실행 오류: {str(e)}", exc_info=True)
            return f"❌ 도구 실행 오류: {str(e)}"