"""Unit tests for NotionTool behaviour."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from ai.core.exceptions import ToolError
from mcp.tools.notion_tool import NotionTool


class StubNotionClient:
    """Simple stand-in for the official Notion client."""

    def __init__(self, query_response: Optional[Dict[str, Any]] = None) -> None:
        self.captured_pages: list[Dict[str, Any]] = []
        self.captured_queries: list[Dict[str, Any]] = []
        self.query_response = query_response or {"results": [], "has_more": False, "next_cursor": None}
        self.pages = self.Pages(self)
        self.databases = self.Databases(self)

    class Pages:
        def __init__(self, outer: "StubNotionClient") -> None:
            self._outer = outer

        def create(self, *, parent: Dict[str, Any], properties: Dict[str, Any]) -> Dict[str, Any]:
            self._outer.captured_pages.append({"parent": parent, "properties": properties})
            return {"id": "page-123", "url": "https://notion.so/page-123"}

    class Databases:
        def __init__(self, outer: "StubNotionClient") -> None:
            self._outer = outer

        def query(self, **kwargs: Any) -> Dict[str, Any]:
            self._outer.captured_queries.append(kwargs)
            return self._outer.query_response


def test_notion_tool_create_event_uses_default_database() -> None:
    client = StubNotionClient()
    tool = NotionTool(client=client, default_event_database_id="event-db")

    result = tool(operation="create_event", title="팀 미팅", date="2025-01-02")
    payload = result.unwrap()

    assert payload["operation"] == "create_event"
    assert client.captured_pages
    recorded = client.captured_pages[0]
    assert recorded["parent"] == {"database_id": "event-db"}
    properties = recorded["properties"]
    assert properties["Name"]["title"][0]["text"]["content"] == "팀 미팅"
    assert properties["Date"]["date"]["start"] == "2025-01-02"


def test_notion_tool_list_tasks_returns_summaries() -> None:
    notion_page = {
        "id": "page-1",
        "url": "https://notion.so/page-1",
        "properties": {
            "Name": {
                "type": "title",
                "title": [
                    {
                        "plain_text": "할일 1",
                        "text": {"content": "할일 1"},
                    }
                ],
            },
            "Status": {
                "type": "status",
                "status": {"name": "진행 중"},
            },
            "Due": {
                "type": "date",
                "date": {"start": "2025-01-03"},
            },
        },
    }
    client = StubNotionClient(query_response={"results": [notion_page], "has_more": False, "next_cursor": None})
    tool = NotionTool(client=client, default_todo_database_id="todo-db")

    result = tool(operation="list_tasks", page_size=10)
    payload = result.unwrap()

    assert payload["database_id"] == "todo-db"
    assert payload["has_more"] is False
    assert payload["items"] == [
        {
            "id": "page-1",
            "url": "https://notion.so/page-1",
            "title": "할일 1",
            "status": "진행 중",
            "date": "2025-01-03",
        }
    ]
    assert client.captured_queries[0]["database_id"] == "todo-db"
    assert client.captured_queries[0]["page_size"] == 10


def test_notion_tool_requires_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(NotionTool.ENV_EVENTS_DATABASE, raising=False)
    monkeypatch.delenv(NotionTool.ENV_TODO_DATABASE, raising=False)
    monkeypatch.delenv(NotionTool.LEGACY_ENV_TASKS_DATABASE, raising=False)
    tool = NotionTool(client=StubNotionClient(), default_event_database_id=None)

    with pytest.raises(ToolError):
        tool(operation="list_events")


def test_notion_tool_accepts_todo_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(NotionTool.ENV_TODO_DATABASE, "env-todo-db")
    tool = NotionTool(client=StubNotionClient())

    create_result = tool(operation="create_todo", title="투두 작성")
    assert create_result.unwrap()["operation"] == "create_task"

    list_result = tool(operation="list_todos")
    data = list_result.unwrap()
    assert data["database_id"] == "env-todo-db"


def test_notion_tool_uses_legacy_tasks_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(NotionTool.ENV_TODO_DATABASE, raising=False)
    monkeypatch.setenv(NotionTool.LEGACY_ENV_TASKS_DATABASE, "legacy-db")

    tool = NotionTool(client=StubNotionClient())

    result = tool(operation="todo_list")
    payload = result.unwrap()
    assert payload["database_id"] == "legacy-db"
