"""
mcp/crewai_adapters/file_crewai_tool.py
기존 FileTool을 CrewAI BaseTool로 래핑
"""
from crewai.tools import BaseTool
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from mcp.tools.file_tool import FileTool, ToolResult


class FileToolInput(BaseModel):
    """FileTool 입력 스키마"""
    operation: str = Field(..., description="Operation to perform: read_file, write_file, list_directory, search_files")
    path: str = Field(default=".", description="File or directory path")
    content: Optional[str] = Field(default=None, description="Content to write (for write_file operation)")
    pattern: Optional[str] = Field(default=None, description="Search pattern (for search_files operation)")


class FileCrewAITool(BaseTool):
    name: str = "파일 시스템 도구"
    description: str = "파일 읽기/쓰기, 디렉토리 목록, 파일 검색을 수행합니다."
    args_schema: Type[BaseModel] = FileToolInput

    def __init__(self):
        super().__init__()
        self._file_tool = FileTool()

    def _run(
        self,
        operation: str,
        path: str = ".",
        content: Optional[str] = None,
        pattern: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """도구 실행"""
        # FileTool 호출
        params = {"operation": operation, "path": path}
        if content is not None:
            params["content"] = content
        if pattern is not None:
            params["pattern"] = pattern

        try:
            result: ToolResult = self._file_tool(**params)

            # 결과를 문자열로 변환
            if result.success:
                # data가 딕셔너리인 경우 포맷팅
                if isinstance(result.data, dict):
                    if "files" in result.data:
                        files = result.data["files"]
                        return f"✅ 찾은 파일 {len(files)}개:\n" + "\n".join(f"  - {f}" for f in files)
                    elif "content" in result.data:
                        return f"✅ 파일 내용:\n{result.data['content']}"
                    else:
                        import json
                        return f"✅ 성공:\n{json.dumps(result.data, indent=2, ensure_ascii=False)}"
                else:
                    return f"✅ 성공: {result.data}"
            else:
                return f"❌ 실패: {result.error}"
        except Exception as e:
            return f"❌ 도구 실행 오류: {str(e)}"