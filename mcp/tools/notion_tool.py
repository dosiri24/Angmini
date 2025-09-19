"""Notion scheduling and task management tool."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

try:
    from notion_client import Client  # type: ignore
    from notion_client.errors import APIResponseError  # type: ignore
except ImportError:  # pragma: no cover - dependency missing at runtime
    Client = None  # type: ignore

    class APIResponseError(Exception):
        """Fallback error when Notion SDK is unavailable."""

from ai.core.exceptions import ToolError

from ..tool_blueprint import ToolBlueprint, ToolResult


class NotionTool(ToolBlueprint):
    """Provides CRUD-style helpers for Notion calendars and task databases."""

    tool_name = "notion"
    description = "Notion 일정/할일 추가 및 조회 도구"
    parameters: Dict[str, Any] = {
        "operation": {
            "type": "string",
            "enum": [
                "create_event",
                "list_events",
                "create_task",
                "list_tasks",
                "create_todo",
                "list_todo",
                "list_todos",
                "todo_create",
                "todo_list",
            ],
            "description": "수행할 작업 종류 (todo/투두 별칭 포함)",
        },
        "title": {
            "type": "string",
            "description": "Notion 페이지 제목",
        },
        "date": {
            "type": "string",
            "description": "이벤트 시작 날짜 (ISO 8601)",
        },
        "due_date": {
            "type": "string",
            "description": "할일 마감일 (ISO 8601)",
        },
        "status": {
            "type": "string",
            "description": "할일 상태 필드에 기록할 값",
        },
        "notes": {
            "type": "string",
            "description": "추가 설명 또는 메모",
        },
        "database_id": {
            "type": "string",
            "description": "명시적으로 사용할 데이터베이스 ID",
        },
        "properties": {
            "type": "object",
            "description": "기본 속성 대신 사용할 Notion raw properties",
        },
        "page_size": {
            "type": "integer",
            "description": "조회 시 가져올 최대 페이지 수",
        },
        "start_cursor": {
            "type": "string",
            "description": "조회 이어서 가져올 때 사용할 cursor",
        },
        "filter": {
            "type": "object",
            "description": "Notion databases.query 필터",
        },
        "sorts": {
            "type": "array",
            "description": "Notion databases.query 정렬 옵션",
        },
    }

    ENV_PRIMARY_TOKEN = "NOTION_API_KEY"
    ENV_FALLBACK_TOKEN = "NOTION_INTEGRATION_TOKEN"
    ENV_EVENTS_DATABASE = "NOTION_EVENTS_DATABASE_ID"
    ENV_TODO_DATABASE = "NOTION_TODO_DATABASE_ID"
    LEGACY_ENV_TASKS_DATABASE = "NOTION_TASKS_DATABASE_ID"

    def __init__(
        self,
        client: Optional[Any] = None,
        *,
        integration_token: Optional[str] = None,
        default_event_database_id: Optional[str] = None,
        default_todo_database_id: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._client = client
        self._integration_token = integration_token
        self._default_event_database_id = default_event_database_id or os.getenv(self.ENV_EVENTS_DATABASE)
        self._default_todo_database_id = default_todo_database_id or self._resolve_todo_database_env()

    def run(self, **kwargs: Any) -> ToolResult:
        operation = self._canonical_operation(kwargs.get("operation"))

        client = self._ensure_client()

        try:
            if operation == "create_event":
                return self._create_event(client, **kwargs)
            if operation == "list_events":
                return self._list_entries(
                    client,
                    default_database=self._default_event_database_id,
                    env_fallback=self.ENV_EVENTS_DATABASE,
                    **kwargs,
                )
            if operation == "create_task":
                return self._create_task(client, **kwargs)
            return self._list_entries(
                client,
                default_database=self._default_todo_database_id,
                env_fallback=self.ENV_TODO_DATABASE,
                **kwargs,
            )
        except ToolError:
            raise
        except APIResponseError as exc:  # pragma: no cover - depends on live API responses
            raise ToolError(f"Notion API 오류: {exc}") from exc
        except Exception as exc:  # pragma: no cover - unexpected runtime failure
            raise ToolError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Creation helpers
    # ------------------------------------------------------------------

    def _create_event(self, client: Any, **kwargs: Any) -> ToolResult:
        database_id = self._resolve_database_id(kwargs.get("database_id"), self._default_event_database_id, self.ENV_EVENTS_DATABASE)
        title = self._require_non_empty(kwargs.get("title"), "title")
        notes = self._optional_str(kwargs.get("notes"))
        date_value = self._optional_str(kwargs.get("date"))

        properties = self._build_title_property(title)
        if date_value:
            properties["Date"] = {"date": {"start": date_value}}
        if notes:
            properties["Notes"] = {"rich_text": [{"text": {"content": notes[:2000]}}]}

        override_properties = self._validate_properties(kwargs.get("properties"))
        if override_properties:
            properties.update(override_properties)

        page = client.pages.create(parent={"database_id": database_id}, properties=properties)
        return ToolResult(success=True, data={"id": page.get("id"), "url": page.get("url"), "operation": "create_event"})

    def _create_task(self, client: Any, **kwargs: Any) -> ToolResult:
        database_id = self._resolve_database_id(
            kwargs.get("database_id"), self._default_todo_database_id, self.ENV_TODO_DATABASE
        )
        title = self._require_non_empty(kwargs.get("title"), "title")
        notes = self._optional_str(kwargs.get("notes"))
        due_date = self._optional_str(kwargs.get("due_date")) or self._optional_str(kwargs.get("date"))
        status_value = self._optional_str(kwargs.get("status"))

        properties = self._build_title_property(title)
        if due_date:
            properties["Due"] = {"date": {"start": due_date}}
        if status_value:
            properties["Status"] = {"status": {"name": status_value}}
        if notes:
            properties["Notes"] = {"rich_text": [{"text": {"content": notes[:2000]}}]}

        override_properties = self._validate_properties(kwargs.get("properties"))
        if override_properties:
            properties.update(override_properties)

        page = client.pages.create(parent={"database_id": database_id}, properties=properties)
        return ToolResult(success=True, data={"id": page.get("id"), "url": page.get("url"), "operation": "create_task"})

    # ------------------------------------------------------------------
    # Listing helpers
    # ------------------------------------------------------------------

    def _list_entries(
        self,
        client: Any,
        *,
        default_database: Optional[str],
        env_fallback: str,
        **kwargs: Any,
    ) -> ToolResult:
        database_id = self._resolve_database_id(
            kwargs.get("database_id"), default_database, env_fallback
        )

        payload: Dict[str, Any] = {}
        filter_payload = kwargs.get("filter")
        if filter_payload is not None:
            if not isinstance(filter_payload, dict):
                raise ToolError("filter 파라미터는 객체(dict)여야 합니다.")
            payload["filter"] = filter_payload

        sorts_payload = kwargs.get("sorts")
        if sorts_payload is not None:
            if not isinstance(sorts_payload, list):
                raise ToolError("sorts 파라미터는 배열(list)이여야 합니다.")
            payload["sorts"] = sorts_payload

        page_size = kwargs.get("page_size")
        if page_size is not None:
            if not isinstance(page_size, int) or page_size <= 0:
                raise ToolError("page_size 파라미터는 0보다 큰 정수여야 합니다.")
            payload["page_size"] = page_size

        start_cursor = kwargs.get("start_cursor")
        if start_cursor is not None:
            if not isinstance(start_cursor, str) or not start_cursor.strip():
                raise ToolError("start_cursor 파라미터는 비어있지 않은 문자열이어야 합니다.")
            payload["start_cursor"] = start_cursor

        response = client.databases.query(database_id=database_id, **payload)
        items = [self._summarise_page(page) for page in response.get("results", [])]

        return ToolResult(
            success=True,
            data={
                "items": items,
                "has_more": bool(response.get("has_more")),
                "next_cursor": response.get("next_cursor"),
                "database_id": database_id,
            },
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        token = self._resolve_token()
        if Client is None:  # pragma: no cover - triggered when dependency missing
            raise ToolError("notion-client 패키지가 설치되어 있지 않습니다. requirements.txt를 확인하세요.")
        try:
            self._client = Client(auth=token)
        except Exception as exc:  # pragma: no cover - depends on external library state
            raise ToolError(f"Notion 클라이언트 초기화에 실패했습니다: {exc}") from exc
        return self._client

    def _resolve_token(self) -> str:
        token = self._integration_token or os.getenv(self.ENV_PRIMARY_TOKEN) or os.getenv(self.ENV_FALLBACK_TOKEN)
        if not token:
            raise ToolError("Notion API 토큰이 설정되어 있지 않습니다. NOTION_API_KEY 환경변수를 확인하세요.")
        return token

    def _resolve_database_id(self, explicit_id: Optional[str], default_id: Optional[str], env_key: str) -> str:
        database_id = (
            self._optional_str(explicit_id)
            or default_id
            or os.getenv(env_key)
            or (os.getenv(self.LEGACY_ENV_TASKS_DATABASE) if env_key == self.ENV_TODO_DATABASE else None)
        )
        if not database_id:
            raise ToolError(
                "Notion 데이터베이스 ID가 비어있습니다. database_id 파라미터 또는 관련 환경변수를 설정하세요."
            )
        return database_id

    def _require_non_empty(self, value: Optional[Any], field_name: str) -> str:
        str_value = self._optional_str(value)
        if not str_value:
            raise ToolError(f"{field_name} 파라미터는 비어있지 않은 문자열이어야 합니다.")
        return str_value

    def _optional_str(self, value: Optional[Any]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ToolError("문자열 파라미터에는 문자열 값이 필요합니다.")
        stripped = value.strip()
        return stripped if stripped else None

    def _validate_properties(self, properties: Any) -> Optional[Dict[str, Any]]:
        if properties is None:
            return None
        if not isinstance(properties, dict):
            raise ToolError("properties 파라미터는 객체(dict)여야 합니다.")
        return properties

    def _build_title_property(self, title: str) -> Dict[str, Any]:
        return {"Name": {"title": [{"text": {"content": title[:2000]}}]}}

    def _summarise_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        properties = page.get("properties", {}) if isinstance(page, dict) else {}
        title = self._extract_property_text(properties, target_type="title")
        status = self._extract_property_text(properties, target_type="status")
        date = self._extract_property_date(properties)
        return {
            "id": page.get("id"),
            "url": page.get("url"),
            "title": title,
            "status": status,
            "date": date,
        }

    def _extract_property_text(self, properties: Dict[str, Any], target_type: str) -> Optional[str]:
        for value in properties.values():
            if not isinstance(value, dict):
                continue
            if value.get("type") != target_type:
                continue
            if target_type == "title":
                items = value.get("title", [])
            elif target_type == "status":
                status = value.get("status")
                if isinstance(status, dict):
                    name = status.get("name")
                    return name if isinstance(name, str) else None
                continue
            else:
                items = value.get(target_type, [])
            if isinstance(items, list) and items:
                first = items[0]
                plain = first.get("plain_text") if isinstance(first, dict) else None
                if isinstance(plain, str) and plain.strip():
                    return plain.strip()
                text = first.get("text") if isinstance(first, dict) else None
                if isinstance(text, dict):
                    content = text.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()
        return None

    def _extract_property_date(self, properties: Dict[str, Any]) -> Optional[str]:
        for value in properties.values():
            if not isinstance(value, dict):
                continue
            if value.get("type") != "date":
                continue
            date_info = value.get("date")
            if isinstance(date_info, dict):
                start = date_info.get("start")
                if isinstance(start, str):
                    return start
        return None

    def _resolve_todo_database_env(self) -> Optional[str]:
        todo_env = os.getenv(self.ENV_TODO_DATABASE)
        if todo_env:
            return todo_env
        return os.getenv(self.LEGACY_ENV_TASKS_DATABASE)

    def _canonical_operation(self, raw_operation: Any) -> str:
        if not isinstance(raw_operation, str):
            raise ToolError("operation 파라미터는 문자열이어야 합니다.")
        normalized = raw_operation.strip().lower()
        if not normalized:
            raise ToolError("operation 파라미터는 비어있지 않은 문자열이어야 합니다.")

        alias_map = {
            "create_event": "create_event",
            "list_events": "list_events",
            "create_task": "create_task",
            "list_tasks": "list_tasks",
            "create_todo": "create_task",
            "list_todo": "list_tasks",
            "list_todos": "list_tasks",
            "todo_create": "create_task",
            "todo_list": "list_tasks",
            "create_todos": "create_task",
            "add_todo": "create_task",
        }

        if normalized in alias_map:
            return alias_map[normalized]

        if "todo" in normalized:
            if "list" in normalized or "조회" in normalized:
                return "list_tasks"
            if "create" in normalized or "add" in normalized or "추가" in normalized:
                return "create_task"

        if "투두" in normalized:
            if "조회" in normalized or "list" in normalized:
                return "list_tasks"
            return "create_task"

        raise ToolError(
            "operation 파라미터는 create_event/list_events/create_task/list_tasks 또는 todo/투두 관련 별칭이어야 합니다."
        )
