"""
mcp/crewai_adapters/notion_crewai_tool.py
기존 NotionTool을 CrewAI BaseTool로 래핑
"""
from crewai.tools import BaseTool
from typing import Type, Any, Optional, List
from pydantic import BaseModel, Field
from mcp.tools.notion_tool import NotionTool, ToolResult


class NotionToolInput(BaseModel):
    """NotionTool 입력 스키마"""
    operation: str = Field(..., description="Operation: create_task, list_tasks, update_task, delete_task, search_project")
    title: Optional[str] = Field(default=None, description="Task title (for create/update)")
    content: Optional[str] = Field(default=None, description="Task content/description")
    task_id: Optional[str] = Field(default=None, description="Task ID (for update/delete)")
    status: Optional[str] = Field(default=None, description="Task status")
    due_date: Optional[str] = Field(default=None, description="Due date in YYYY-MM-DD format")
    project_title: Optional[str] = Field(default=None, description="Project title to link")
    tags: Optional[List[str]] = Field(default=None, description="Tags for the task")


class NotionCrewAITool(BaseTool):
    name: str = "Notion 도구"
    description: str = "Notion API를 통해 할일 생성, 조회, 업데이트, 삭제 및 프로젝트 관리를 수행합니다."
    args_schema: Type[BaseModel] = NotionToolInput

    def __init__(self):
        super().__init__()
        try:
            self._notion_tool = NotionTool()
            self._enabled = True
        except Exception as e:
            # Notion API 키가 없는 경우 등 초기화 실패 처리
            self._notion_tool = None
            self._enabled = False
            print(f"⚠️ NotionTool 초기화 실패: {e}")

    def _run(
        self,
        operation: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        task_id: Optional[str] = None,
        status: Optional[str] = None,
        due_date: Optional[str] = None,
        project_title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any
    ) -> str:
        """도구 실행"""
        if not self._enabled:
            return "❌ Notion 도구가 비활성화됨 (API 키 확인 필요)"

        # NotionTool 파라미터 구성
        params = {"operation": operation}
        if title:
            params["title"] = title
        if content:
            params["content"] = content
        if task_id:
            params["task_id"] = task_id
        if status:
            params["status"] = status
        if due_date:
            params["due_date"] = due_date
        if project_title:
            params["project_title"] = project_title
        if tags:
            params["tags"] = tags

        try:
            result: ToolResult = self._notion_tool(**params)

            # 결과를 문자열로 변환
            if result.success:
                data = result.data
                if isinstance(data, dict):
                    if "tasks" in data:
                        tasks = data["tasks"]
                        if not tasks:
                            return "✅ 할일이 없습니다."
                        output = f"✅ 할일 {len(tasks)}개 조회:\n"
                        for task in tasks:
                            output += f"  - [{task.get('status', '?')}] {task.get('title', '제목 없음')}"
                            if task.get('due_date'):
                                output += f" (마감: {task['due_date']})"
                            output += "\n"
                        return output
                    elif "id" in data:
                        return f"✅ 작업 완료 (ID: {data['id']})"
                    else:
                        import json
                        return f"✅ 성공:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
                else:
                    return f"✅ 성공: {data}"
            else:
                return f"❌ 실패: {result.error}"
        except Exception as e:
            return f"❌ 도구 실행 오류: {str(e)}"