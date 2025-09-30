"""Unit tests for NotionTool behaviour."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from ai.core.exceptions import ToolError
from mcp.tools.notion_tool import NotionTool


class StubNotionClient:
    """Simple stand-in for the official Notion client."""

    def __init__(
        self,
        query_response: Optional[Dict[str, Any]] = None,
        page_lookup: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.captured_pages: list[Dict[str, Any]] = []
        self.captured_updates: list[Dict[str, Any]] = []
        self.captured_queries: list[Dict[str, Any]] = []
        self.query_response = query_response or {"results": [], "has_more": False, "next_cursor": None}
        self.page_lookup = page_lookup or {}
        self.pages = self.Pages(self)
        self.databases = self.Databases(self)

    class Pages:
        def __init__(self, outer: "StubNotionClient") -> None:
            self._outer = outer

        def create(self, *, parent: Dict[str, Any], properties: Dict[str, Any]) -> Dict[str, Any]:
            self._outer.captured_pages.append({"parent": parent, "properties": properties})
            return {"id": "page-123", "url": "https://notion.so/page-123"}

        def retrieve(self, page_id: str) -> Dict[str, Any]:
            return self._outer.page_lookup.get(page_id, {"properties": {}})

        def update(self, *, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
            self._outer.captured_updates.append({"page_id": page_id, "properties": properties})
            return {"id": page_id, "url": f"https://notion.so/{page_id}"}

    class Databases:
        def __init__(self, outer: "StubNotionClient") -> None:
            self._outer = outer

        def query(self, **kwargs: Any) -> Dict[str, Any]:
            self._outer.captured_queries.append(kwargs)
            return self._outer.query_response


def test_notion_tool_create_task_populates_standard_fields() -> None:
    client = StubNotionClient()
    tool = NotionTool(client=client, default_todo_database_id="todo-db")

    result = tool(
        operation="create_task",
        title="회의 준비",
        due_date="2025-03-01",
        status="대기",
        notes="안건 정리",
    )
    payload = result.unwrap()

    assert payload["operation"] == "create_task"
    assert client.captured_pages
    recorded = client.captured_pages[0]
    assert recorded["parent"] == {"database_id": "todo-db"}
    properties = recorded["properties"]
    assert properties["Name"]["title"][0]["text"]["content"] == "회의 준비"
    assert properties["Due"]["date"]["start"] == "2025-03-01"
    assert properties["Status"]["status"]["name"] == "대기"
    assert properties["Notes"]["rich_text"][0]["text"]["content"] == "안건 정리"


def test_notion_tool_respects_custom_task_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(NotionTool.ENV_TASK_TITLE_PROPERTY, raising=False)
    client = StubNotionClient()
    tool = NotionTool(
        client=client,
        default_todo_database_id="todo-db",
        task_properties={
            "title": "작업명",
            "status": "작업상태",
            "due": "마감일",
            "notes": "설명",
            "relation": "경험/프로젝트",
        },
    )

    result = tool(
        operation="create_task",
        title="보고서 작성",
        due_date="2025-04-01",
        status="진행 중",
        notes="초안 버전",
        relations=["project-123", "project-456"],
    )
    payload = result.unwrap()

    assert payload["operation"] == "create_task"
    recorded = client.captured_pages[0]
    properties = recorded["properties"]
    assert "Name" not in properties
    assert properties["작업명"]["title"][0]["text"]["content"] == "보고서 작성"
    assert properties["마감일"]["date"]["start"] == "2025-04-01"
    assert properties["작업상태"]["status"]["name"] == "진행 중"
    assert properties["설명"]["rich_text"][0]["text"]["content"] == "초안 버전"
    assert properties["경험/프로젝트"]["relation"] == [{"id": "project-123"}, {"id": "project-456"}]


def test_notion_tool_accepts_string_relation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(NotionTool.ENV_TASK_RELATION_PROPERTY, "경험/프로젝트")
    client = StubNotionClient()
    tool = NotionTool(client=client, default_todo_database_id="todo-db")

    tool(
        operation="create_task",
        title="단일 relation",
        relations="project-789",
    )

    recorded = client.captured_pages[0]
    assert recorded["properties"]["경험/프로젝트"] == {"relation": [{"id": "project-789"}]}


def test_notion_tool_auto_links_project_when_relation_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(NotionTool.ENV_PROJECT_DATABASE, "project-db")
    client = StubNotionClient(
        query_response={
            "results": [
                {
                    "id": "proj-42",
                    "properties": {
                        "프로젝트 이름": {
                            "type": "title",
                            "title": [{"plain_text": "학회 기자단", "text": {"content": "학회 기자단"}}],
                        }
                    },
                }
            ],
            "has_more": False,
            "next_cursor": None,
        }
    )

    tool = NotionTool(
        client=client,
        default_todo_database_id="todo-db",
        default_project_database_id="project-db",
        task_properties={
            "title": "작업명",
            "relation": "경험/프로젝트",
        },
        project_properties={
            "title": "프로젝트 이름",
        },
    )

    result = tool(operation="create_task", title="학회 기자단 활동으로 사과 기사 쓰기")
    payload = result.unwrap()

    recorded = client.captured_pages[0]
    assert recorded["properties"]["경험/프로젝트"]["relation"] == [{"id": "proj-42"}]
    assert payload["relations"] == [{"id": "proj-42"}]


def test_notion_tool_creates_task_without_relation_when_no_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(NotionTool.ENV_PROJECT_DATABASE, "project-db")
    client = StubNotionClient(
        query_response={
            "results": [
                {
                    "id": "proj-1",
                    "properties": {
                        "프로젝트 이름": {
                            "type": "title",
                            "title": [{"plain_text": "기술 세미나", "text": {"content": "기술 세미나"}}],
                        }
                    },
                },
                {
                    "id": "proj-2",
                    "properties": {
                        "프로젝트 이름": {
                            "type": "title",
                            "title": [{"plain_text": "여행 기록", "text": {"content": "여행 기록"}}],
                        }
                    },
                },
            ],
            "has_more": False,
            "next_cursor": None,
        }
    )

    tool = NotionTool(
        client=client,
        default_todo_database_id="todo-db",
        default_project_database_id="project-db",
        task_properties={
            "title": "작업명",
            "relation": "경험/프로젝트",
        },
        project_properties={
            "title": "프로젝트 이름",
        },
    )

    result = tool(operation="create_task", title="사과 5개 사오기")
    payload = result.unwrap()

    recorded = client.captured_pages[0]
    assert "경험/프로젝트" not in recorded["properties"]
    assert "relations" not in payload


def test_notion_tool_update_task_applies_explicit_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(NotionTool.ENV_TASK_RELATION_PROPERTY, "경험/프로젝트")
    client = StubNotionClient(page_lookup={"task-1": {"properties": {}}})
    tool = NotionTool(client=client, default_todo_database_id="todo-db")

    result = tool(
        operation="update_task",
        page_id="task-1",
        title="수정된 제목",
        status="완료",
        notes="정리 완료",
        due_date="2025-10-01T09:00:00",
        relations=["proj-1"],
    )
    payload = result.unwrap()

    assert payload["operation"] == "update_task"
    assert client.captured_updates
    update = client.captured_updates[0]
    assert update["page_id"] == "task-1"
    properties = update["properties"]
    assert properties["Name"]["title"][0]["text"]["content"] == "수정된 제목"
    assert properties["Status"]["status"]["name"] == "완료"
    assert properties["Notes"]["rich_text"][0]["text"]["content"] == "정리 완료"
    assert properties["Due"]["date"]["start"] == "2025-10-01T09:00:00+09:00"
    assert properties["경험/프로젝트"]["relation"] == [{"id": "proj-1"}]


def test_notion_tool_update_task_auto_links_when_relations_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(NotionTool.ENV_TASK_RELATION_PROPERTY, "경험/프로젝트")
    monkeypatch.setenv(NotionTool.ENV_PROJECT_DATABASE, "project-db")
    client = StubNotionClient(
        query_response={
            "results": [
                {
                    "id": "proj-900",
                    "properties": {
                        "제목": {
                            "type": "title",
                            "title": [
                                {"plain_text": "온라인 스시모", "text": {"content": "온라인 스시모"}}
                            ],
                        }
                    },
                }
            ],
            "has_more": False,
            "next_cursor": None,
        },
        page_lookup={
            "task-2": {
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"plain_text": "온라인 스시모 듣기", "text": {"content": "온라인 스시모 듣기"}}],
                    }
                }
            }
        },
    )

    tool = NotionTool(
        client=client,
        default_todo_database_id="todo-db",
        default_project_database_id="project-db",
        task_properties={
            "title": "Name",
            "relation": "경험/프로젝트",
        },
        project_properties={
            "title": "제목",
        },
    )

    result = tool(operation="update_task", page_id="task-2")
    payload = result.unwrap()

    assert client.captured_updates
    properties = client.captured_updates[0]["properties"]
    assert properties["경험/프로젝트"]["relation"] == [{"id": "proj-900"}]
    assert payload["relations"] == [{"id": "proj-900"}]


def test_notion_tool_keeps_title_with_project_relation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(NotionTool.ENV_PROJECT_DATABASE, "project-db")
    client = StubNotionClient(
        query_response={"results": [], "has_more": False, "next_cursor": None},
        page_lookup={
            "proj-42": {
                "properties": {
                    "프로젝트 이름": {
                        "type": "title",
                        "title": [
                            {
                                "plain_text": "도시설계학회 기자단",
                                "text": {"content": "도시설계학회 기자단"},
                            }
                        ],
                    }
                }
            }
        },
    )

    tool = NotionTool(
        client=client,
        default_todo_database_id="todo-db",
        task_properties={
            "title": "작업명",
            "relation": "경험/프로젝트",
        },
        project_properties={
            "title": "프로젝트 이름",
        },
    )

    result = tool(
        operation="create_task",
        title="도시설계학회 기자단 활동으로 부산도시답사 기사 작성하기",
        relations=["proj-42"],
    )
    payload = result.unwrap()

    recorded = client.captured_pages[0]
    title_payload = recorded["properties"]["작업명"]["title"][0]["text"]["content"]
    # Title is kept as provided; LLM is responsible for deduping any
    # overlapping project mentions before calling the tool.
    assert title_payload == "도시설계학회 기자단 활동으로 부산도시답사 기사 작성하기"
    assert payload["relations"] == [{"id": "proj-42"}]


def test_notion_tool_list_projects_returns_summaries(monkeypatch: pytest.MonkeyPatch) -> None:
    project_page = {
        "id": "proj-1",
        "url": "https://notion.so/proj-1",
        "properties": {
            "프로젝트 이름": {
                "type": "title",
                "title": [
                    {
                        "plain_text": "AI 리서치",
                        "text": {"content": "AI 리서치"},
                    }
                ],
            },
            "상태": {
                "type": "status",
                "status": {"name": "진행"},
            },
            "비고": {
                "type": "rich_text",
                "rich_text": [
                    {
                        "plain_text": "핵심 프로젝트",
                        "text": {"content": "핵심 프로젝트"},
                    }
                ],
            },
            "작업": {
                "type": "relation",
                "relation": [{"id": "todo-1"}, {"id": "todo-2"}],
                "has_more": False,
            },
        },
    }

    client = StubNotionClient(query_response={"results": [project_page], "has_more": False, "next_cursor": None})
    tool = NotionTool(
        client=client,
        default_project_database_id="project-db",
        project_properties={
            "title": "프로젝트 이름",
            "status": "상태",
            "notes": "비고",
            "relation": "작업",
        },
    )

    result = tool(operation="list_projects", page_size=5)
    payload = result.unwrap()

    assert payload["database_id"] == "project-db"
    assert payload["has_more"] is False
    assert payload["items"] == [
        {
            "id": "proj-1",
            "url": "https://notion.so/proj-1",
            "title": "AI 리서치",
            "status": "진행",
            "notes": "핵심 프로젝트",
            "relations": {"작업": ["todo-1", "todo-2"]},
        }
    ]
    captured = client.captured_queries[0]
    assert captured["database_id"] == "project-db"
    assert captured["page_size"] == 5


def test_notion_tool_list_projects_uses_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(NotionTool.ENV_PROJECT_DATABASE, "env-project-db")
    client = StubNotionClient()

    tool = NotionTool(client=client)

    result = tool(operation="list_projects")
    payload = result.unwrap()

    assert payload["database_id"] == "env-project-db"
    assert client.captured_queries[0]["database_id"] == "env-project-db"


def test_notion_tool_find_project_lists_candidates_without_scores() -> None:
    project_page_one = {
        "id": "proj-1",
        "url": "https://notion.so/proj-1",
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "AI Research", "text": {"content": "AI Research"}}],
            }
        },
    }
    project_page_two = {
        "id": "proj-2",
        "url": "https://notion.so/proj-2",
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "Marketing Launch", "text": {"content": "Marketing Launch"}}],
            }
        },
    }

    client = StubNotionClient(
        query_response={
            "results": [project_page_one, project_page_two],
            "has_more": False,
            "next_cursor": None,
        }
    )
    tool = NotionTool(client=client, default_project_database_id="project-db")

    result = tool(operation="find_project", query="AI", limit=1)
    payload = result.unwrap()

    assert payload["query"] == "AI"
    assert payload["database_id"] == "project-db"
    assert "best_match" not in payload
    assert payload["items"][0]["title"] == "AI Research"
    # No automatic scoring now; LLM will decide based on the list
    assert "match_score" not in payload["items"][0]
    assert client.captured_queries[0]["page_size"] == 1


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
            "경험/프로젝트": {
                "type": "relation",
                "relation": [{"id": "project-123"}],
                "has_more": False,
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
            "relations": {"경험/프로젝트": ["project-123"]},
        }
    ]
    assert client.captured_queries[0]["database_id"] == "todo-db"
    assert client.captured_queries[0]["page_size"] == 10


def test_notion_tool_requires_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(NotionTool.ENV_TODO_DATABASE, raising=False)
    monkeypatch.delenv(NotionTool.LEGACY_ENV_TASKS_DATABASE, raising=False)
    tool = NotionTool(client=StubNotionClient(), default_todo_database_id=None)

    with pytest.raises(ToolError):
        tool(operation="list_tasks")


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
