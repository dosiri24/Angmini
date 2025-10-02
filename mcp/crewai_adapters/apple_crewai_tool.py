"""
mcp/crewai_adapters/apple_crewai_tool.py
기존 AppleTool을 CrewAI BaseTool로 래핑
"""
from crewai.tools import BaseTool
from typing import Type, Any, Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict
from mcp.tools.apple_tool import AppleTool, ToolResult
from ai.core.logger import get_logger


class AppleToolInput(BaseModel):
    """AppleTool 입력 스키마"""
    operation: str = Field(..., description="Operation to perform (e.g., notes_create, reminders_list, calendar_list)")
    title: Optional[str] = Field(default=None, description="Title for the item")
    content: Optional[str] = Field(default=None, description="Content/body text")
    note_id: Optional[str] = Field(default=None, description="Note ID for update/delete")
    reminder_id: Optional[str] = Field(default=None, description="Reminder ID for complete/delete")
    list_name: Optional[str] = Field(default=None, description="List/folder name")
    due_date: Optional[str] = Field(default=None, description="Due date for reminders")
    priority: Optional[int] = Field(default=None, description="Priority level (1-9)")
    location: Optional[str] = Field(default=None, description="Location for events")
    start_time: Optional[str] = Field(default=None, description="Start time for events")
    end_time: Optional[str] = Field(default=None, description="End time for events")
    attendees: Optional[List[str]] = Field(default=None, description="Event attendees")


class AppleCrewAITool(BaseTool):
    name: str = "Apple 시스템 도구"
    description: str = "macOS 시스템 앱(Notes, Reminders, Calendar 등)과 상호작용합니다."
    args_schema: Type[BaseModel] = AppleToolInput

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = get_logger(__name__)
        try:
            self._apple_tool = AppleTool()
            # Apple MCP 서버 시작 시도
            try:
                from mcp.apple_mcp_manager import AppleMCPManager
                self._mcp_manager = AppleMCPManager()
                self._mcp_manager.start_server()
                self._enabled = True
            except:
                # MCP 서버 시작 실패시에도 도구는 초기화
                self._enabled = True
        except Exception as e:
            self._apple_tool = None
            self._enabled = False
            self._logger.warning(f"AppleTool 초기화 실패: {e}")

    def _run(
        self,
        operation: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        note_id: Optional[str] = None,
        reminder_id: Optional[str] = None,
        list_name: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: Optional[int] = None,
        location: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        **kwargs: Any
    ) -> str:
        """도구 실행"""
        # 입력 파라미터 상세 로깅
        params_log = f"operation={operation}"
        if title:
            params_log += f", title={title}"
        if list_name:
            params_log += f", list={list_name}"
        self._logger.info(f"🔧 [AppleTool] 실행 - {params_log}")

        if not self._enabled:
            self._logger.warning("❌ [AppleTool] 비활성화")
            return "❌ Apple 도구가 비활성화됨"

        # AppleTool 파라미터 구성
        params = {"operation": operation}
        if title:
            params["title"] = title
        if content:
            params["content"] = content
        if note_id:
            params["note_id"] = note_id
        if reminder_id:
            params["reminder_id"] = reminder_id
        if list_name:
            params["list_name"] = list_name
        if due_date:
            params["due_date"] = due_date
        if priority is not None:
            params["priority"] = priority
        if location:
            params["location"] = location
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if attendees:
            params["attendees"] = attendees

        try:
            result: ToolResult = self._apple_tool(**params)
            if result.success:
                self._logger.info(f"✅ [AppleTool] 성공")
            else:
                self._logger.warning(f"❌ [AppleTool] 실패: {result.error}")

            # 결과를 문자열로 변환
            if result.success:
                data = result.data
                if isinstance(data, dict):
                    if "notes" in data:
                        notes = data["notes"]
                        if not notes:
                            return "✅ 메모가 없습니다."
                        output = f"✅ 메모 {len(notes)}개:\n"
                        for note in notes:
                            output += f"  - {note.get('title', '제목 없음')}"
                            if note.get('folder'):
                                output += f" (폴더: {note['folder']})"
                            output += "\n"
                        return output
                    elif "reminders" in data:
                        reminders = data["reminders"]
                        if not reminders:
                            return "✅ 미리 알림이 없습니다."
                        output = f"✅ 미리 알림 {len(reminders)}개:\n"
                        for rem in reminders:
                            status = "✓" if rem.get('completed') else "○"
                            output += f"  {status} {rem.get('title', '제목 없음')}"
                            if rem.get('due_date'):
                                output += f" (마감: {rem['due_date']})"
                            output += "\n"
                        return output
                    elif "events" in data:
                        events = data["events"]
                        if not events:
                            return "✅ 일정이 없습니다."
                        output = f"✅ 일정 {len(events)}개:\n"
                        for event in events:
                            output += f"  - {event.get('title', '제목 없음')}"
                            if event.get('start_time'):
                                output += f" ({event['start_time']})"
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