"""Notion task and project management tool."""

from __future__ import annotations

import os
from difflib import SequenceMatcher
from typing import Any, Dict, Optional, Type, List
from zoneinfo import ZoneInfo

try:
    from notion_client import Client  # type: ignore
    from notion_client.errors import APIResponseError  # type: ignore
except ImportError:  # pragma: no cover - dependency missing at runtime
    Client = None  # type: ignore

    class APIResponseError(Exception):
        """Fallback error when Notion SDK is unavailable."""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger

from ..tool_blueprint import ToolBlueprint, ToolResult


class NotionTool(ToolBlueprint):
    """Provides helpers for Notion todo databases and related project metadata."""

    tool_name = "notion"
    description = "Notion 할일 데이터베이스 관리 도구"
    parameters: Dict[str, Any] = {
        "operation": {
            "type": "string",
            "enum": [
                "create_task",
                "list_tasks",
                "list_projects",
                "find_project",
                "update_task",
                "create_todo",
                "list_todo",
                "list_todos",
                "todo_create",
                "todo_list",
                "update_todo",
                "todo_update",
            ],
            "description": "수행할 작업 종류 (todo/투두 별칭 포함)",
        },
        "title": {
            "type": "string",
            "description": "Notion 페이지 제목",
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
        "page_id": {
            "type": "string",
            "description": "업데이트할 페이지(할일)의 ID",
        },
        "relations": {
            "type": "array",
            "description": "연결할 relation 대상 페이지 ID 목록",
        },
        "relation_ids": {
            "type": "array",
            "description": "relations 별칭 (동일한 의미)",
        },
        "query": {
            "type": "string",
            "description": "프로젝트 검색 시 사용할 키워드",
        },
        "limit": {
            "type": "integer",
            "description": "find_project 결과에서 반환할 최대 매치 수",
        },
        "project_database_id": {
            "type": "string",
            "description": "프로젝트/경험 데이터베이스 ID",
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

    examples = [
        {
            "description": "List tasks with empty project relations",
            "parameters": {
                "operation": "list_tasks",
                "filter": {
                    "property": "경험/프로젝트",
                    "relation": {"is_empty": True}
                }
            }
        },
        {
            "description": "List all available projects",
            "parameters": {
                "operation": "list_projects"
            }
        },
        {
            "description": "Update task with project relation",
            "parameters": {
                "operation": "update_task",
                "page_id": "abc123de-f456-7890-abcd-ef1234567890",
                "relations": ["22eddd5c-74a0-8077-940d-f80c70d1648d"]
            }
        },
        {
            "description": "Create new task with due date",
            "parameters": {
                "operation": "create_task",
                "title": "Complete project report",
                "due_date": "2025-10-15T23:59:59",
                "status": "Not started"
            }
        }
    ]

    pitfalls = [
        "❌ Do NOT use find_project - it's deprecated and fails with 'Name' property error",
        "❌ Do NOT use placeholder values like '<step 1 result>' - use actual UUIDs from observations",
        "❌ Do NOT create multi-step plans with forward references - plan one step at a time",
        "✅ ALWAYS use list_projects instead of find_project, then match by title in your reasoning",
        "✅ ALWAYS copy exact UUIDs from observation data (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)",
        "✅ Relations must be an array of UUID strings, not a single string"
    ]

    ENV_PRIMARY_TOKEN = "NOTION_API_KEY"
    ENV_FALLBACK_TOKEN = "NOTION_INTEGRATION_TOKEN"
    ENV_TODO_DATABASE = "NOTION_TODO_DATABASE_ID"
    LEGACY_ENV_TASKS_DATABASE = "NOTION_TASKS_DATABASE_ID"
    ENV_PROJECT_DATABASE = "NOTION_PROJECT_DATABASE_ID"

    ENV_TASK_TITLE_PROPERTY = "NOTION_TASK_TITLE_PROPERTY"
    ENV_TASK_STATUS_PROPERTY = "NOTION_TASK_STATUS_PROPERTY"
    ENV_TASK_DUE_PROPERTY = "NOTION_TASK_DUE_PROPERTY"
    ENV_TASK_NOTES_PROPERTY = "NOTION_TASK_NOTES_PROPERTY"
    ENV_TASK_RELATION_PROPERTY = "NOTION_TASK_RELATION_PROPERTY"

    ENV_PROJECT_TITLE_PROPERTY = "NOTION_PROJECT_TITLE_PROPERTY"
    ENV_PROJECT_STATUS_PROPERTY = "NOTION_PROJECT_STATUS_PROPERTY"
    ENV_PROJECT_NOTES_PROPERTY = "NOTION_PROJECT_NOTES_PROPERTY"
    ENV_PROJECT_RELATION_PROPERTY = "NOTION_PROJECT_TASK_RELATION_PROPERTY"

    DEFAULT_TASK_PROPERTIES = {
        "title": "Name",
        "status": "Status",
        "due": "Due",
        "notes": "Notes",
        "relation": None,
    }

    DEFAULT_PROJECT_PROPERTIES = {
        "title": "Name",
        "status": None,
        "notes": None,
        "relation": None,
    }

    AUTO_PROJECT_FETCH_LIMIT = 100
    AUTO_MATCH_MIN_SCORE = 0.72
    AUTO_MATCH_SECONDARY_GAP = 0.08

    def __init__(
        self,
        client: Optional[Any] = None,
        *,
        integration_token: Optional[str] = None,
        default_todo_database_id: Optional[str] = None,
        default_project_database_id: Optional[str] = None,
        task_properties: Optional[Dict[str, str]] = None,
        project_properties: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__()
        self._client = client
        self._integration_token = integration_token
        self._default_todo_database_id = default_todo_database_id or self._resolve_todo_database_env()
        self._default_project_database_id = default_project_database_id or os.getenv(self.ENV_PROJECT_DATABASE)
        self._task_properties = self._resolve_property_names(
            overrides=task_properties,
            defaults=self.DEFAULT_TASK_PROPERTIES,
            env_keys={
                "title": self.ENV_TASK_TITLE_PROPERTY,
                "status": self.ENV_TASK_STATUS_PROPERTY,
                "due": self.ENV_TASK_DUE_PROPERTY,
                "notes": self.ENV_TASK_NOTES_PROPERTY,
                "relation": self.ENV_TASK_RELATION_PROPERTY,
            },
            optional_keys={"relation"},
        )
        self._project_properties = self._resolve_property_names(
            overrides=project_properties,
            defaults=self.DEFAULT_PROJECT_PROPERTIES,
            env_keys={
                "title": self.ENV_PROJECT_TITLE_PROPERTY,
                "status": self.ENV_PROJECT_STATUS_PROPERTY,
                "notes": self.ENV_PROJECT_NOTES_PROPERTY,
                "relation": self.ENV_PROJECT_RELATION_PROPERTY,
            },
            optional_keys={"status", "notes", "relation"},
        )

    def validate_parameters(self, **kwargs: Any) -> tuple[bool, Optional[str]]:
        """Validate parameters before execution with helpful hints."""
        import re

        operation = kwargs.get("operation", "").strip().lower()

        # Block deprecated find_project
        if operation == "find_project":
            return (
                False,
                "❌ Operation 'find_project' is deprecated due to property errors.\n"
                "💡 Use 'list_projects' instead, then match by title in your reasoning.\n"
                "Example: list_projects → filter results → use matched project ID"
            )

        # Validate UUID format for page_id
        if "page_id" in kwargs:
            page_id = kwargs["page_id"]
            if not self._is_valid_uuid(str(page_id)):
                return (
                    False,
                    f"❌ Invalid page_id format: '{page_id}'\n"
                    f"💡 Must be a valid UUID (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)\n"
                    f"💡 Copy exact UUID from observation data, do NOT use placeholders"
                )

        # Validate UUID format for relations
        if "relations" in kwargs:
            relations = kwargs["relations"]
            if not isinstance(relations, list):
                return (
                    False,
                    f"❌ 'relations' must be an array, not {type(relations).__name__}\n"
                    f"💡 Use: \"relations\": [\"uuid1\", \"uuid2\"]"
                )

            for idx, rel_id in enumerate(relations):
                if not self._is_valid_uuid(str(rel_id)):
                    return (
                        False,
                        f"❌ Invalid UUID in relations[{idx}]: '{rel_id}'\n"
                        f"💡 Must be valid UUIDs (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)\n"
                        f"💡 Copy exact UUIDs from observation data"
                    )

        return (True, None)

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        """Check if string is a valid UUID format."""
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        # Also accept compact format (no hyphens)
        compact_pattern = re.compile(r'^[0-9a-f]{32}$', re.IGNORECASE)
        return bool(uuid_pattern.match(value) or compact_pattern.match(value))

    def run(self, **kwargs: Any) -> ToolResult:
        operation = self._canonical_operation(kwargs.get("operation"))

        client = self._ensure_client()

        try:
            if operation == "create_task":
                return self._create_task(client, **kwargs)
            if operation == "list_projects":
                return self._list_projects(client, **kwargs)
            if operation == "find_project":
                return self._find_project(client, **kwargs)
            if operation == "update_task":
                return self._update_task(client, **kwargs)
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

    def _create_task(self, client: Any, **kwargs: Any) -> ToolResult:
        database_id = self._resolve_database_id(
            kwargs.get("database_id"), self._default_todo_database_id, self.ENV_TODO_DATABASE
        )
        title = self._require_non_empty(kwargs.get("title"), "title")
        notes = self._optional_str(kwargs.get("notes"))
        due_date = self._optional_str(kwargs.get("due_date"))
        status_value = self._optional_str(kwargs.get("status"))
        relations = self._normalise_relations(kwargs.get("relations") or kwargs.get("relation_ids"))

        title_property_name = self._task_properties["title"]
        properties = self._build_title_property(title, title_property_name)
        due_property = self._task_properties.get("due")
        if due_date and due_property:
            properties[due_property] = {"date": {"start": self._ensure_kst_timezone(due_date)}}
        status_property = self._task_properties.get("status")
        if status_value and status_property:
            properties[status_property] = {"status": {"name": status_value}}
        notes_property = self._task_properties.get("notes")
        if notes and notes_property:
            properties[notes_property] = {"rich_text": [{"text": {"content": notes[:2000]}}]}
        relation_property = self._task_properties.get("relation")
        project_database_hint = self._optional_str(kwargs.get("project_database_id"))
        if not relations and relation_property:
            relations = self._auto_select_project_relations(
                client,
                task_title=title,
                task_notes=notes,
                project_database_id=project_database_hint,
            )
        if relations and relation_property:
            properties[relation_property] = {"relation": relations}

        override_properties = self._validate_properties(kwargs.get("properties"))
        if override_properties:
            properties.update(override_properties)

        page = client.pages.create(parent={"database_id": database_id}, properties=properties)
        payload: Dict[str, Any] = {
            "id": page.get("id"),
            "url": page.get("url"),
            "operation": "create_task",
        }
        if relations:
            payload["relations"] = relations
        return ToolResult(success=True, data=payload)

    def _update_task(self, client: Any, **kwargs: Any) -> ToolResult:
        page_id = self._require_non_empty(kwargs.get("page_id"), "page_id")
        title = self._optional_str(kwargs.get("title"))
        notes = kwargs.get("notes")
        due_date = self._optional_str(kwargs.get("due_date"))
        status_value = self._optional_str(kwargs.get("status"))
        raw_relations = kwargs.get("relations") if "relations" in kwargs else kwargs.get("relation_ids")
        project_database_hint = self._optional_str(kwargs.get("project_database_id"))

        title_property_name = self._task_properties["title"]
        properties: Dict[str, Any] = {}

        if title is not None:
            properties.update(self._build_title_property(title, title_property_name))

        notes_property = self._task_properties.get("notes")
        normalized_notes: Optional[str]
        if notes is None:
            normalized_notes = None
        else:
            normalized_notes = self._optional_str(notes)
        if notes_property:
            if normalized_notes is not None:
                properties[notes_property] = {"rich_text": [{"text": {"content": normalized_notes[:2000]}}]}
            elif "notes" in kwargs:
                properties[notes_property] = {"rich_text": []}

        due_property = self._task_properties.get("due")
        if due_property:
            if due_date:
                properties[due_property] = {"date": {"start": self._ensure_kst_timezone(due_date)}}
            elif "due_date" in kwargs:
                # Clear the due date when explicit null-equivalent provided
                properties[due_property] = {"date": None}

        status_property = self._task_properties.get("status")
        if status_property:
            if status_value:
                properties[status_property] = {"status": {"name": status_value}}
            elif "status" in kwargs:
                properties[status_property] = {"status": None}

        relation_property = self._task_properties.get("relation")
        relations = self._normalise_relations(raw_relations)

        if relation_property:
            if relations is None and "relations" not in kwargs and "relation_ids" not in kwargs:
                existing_context = self._retrieve_task_context(client, page_id)
                fallback_title = title if title is not None else existing_context.get("title")
                fallback_notes = normalized_notes if normalized_notes is not None else existing_context.get("notes")
                relations = self._auto_select_project_relations(
                    client,
                    task_title=fallback_title or "",
                    task_notes=fallback_notes,
                    project_database_id=project_database_hint,
                )
            if relations is not None:
                properties[relation_property] = {"relation": relations}

        override_properties = self._validate_properties(kwargs.get("properties"))
        if override_properties:
            properties.update(override_properties)

        if not properties:
            raise ToolError("업데이트할 속성을 하나 이상 지정하세요.")

        page = client.pages.update(page_id=page_id, properties=properties)
        payload: Dict[str, Any] = {
            "id": page.get("id") or page_id,
            "url": page.get("url"),
            "operation": "update_task",
        }
        if relation_property and relation_property in properties:
            payload["relations"] = properties[relation_property]["relation"]
        return ToolResult(success=True, data=payload)

    def _ensure_kst_timezone(self, raw: str) -> str:
        """Ensure datetime strings with time include KST(+09:00) offset.

        별도 지시가 없는 한 모든 시간은 한국 시간(GMT+9, Asia/Seoul)으로 처리합니다.

        - If the input is a date only (YYYY-MM-DD), return as-is.
        - If time part exists and a timezone designator (Z or ±HH:MM) is missing,
          append "+09:00" so Notion does not treat it as UTC.
        - If timezone is already present, return as-is.

        Examples:
            "2025-10-03" → "2025-10-03" (날짜만 있는 경우 그대로 유지)
            "2025-10-03T15:00:00" → "2025-10-03T15:00:00+09:00" (시간 있으면 KST 추가)
            "2025-10-03T15:00:00+09:00" → "2025-10-03T15:00:00+09:00" (이미 타임존 있으면 유지)
            "2025-10-03T15:00:00Z" → "2025-10-03T15:00:00Z" (UTC 명시된 경우 유지)
        """
        text = (raw or "").strip()
        if not text:
            return raw
        if "T" not in text:
            # Date-only values should remain date-only
            return text
        # Time part exists; check for timezone designator
        time_part = text.split("T", 1)[1]
        if time_part.endswith("Z") or time_part.endswith("z"):
            # UTC로 명시된 경우 그대로 유지 (Notion이 UTC로 처리)
            return text
        if "+" in time_part:
            # 이미 양수 offset 있음 (예: +09:00, +00:00)
            return text
        # Detect negative offset like -09:00 in time part
        # The time format is HH:MM(:SS[.fff]) optionally followed by offset
        # A '-' in time_part (beyond the hour/minute section) indicates an offset
        if "-" in time_part[2:]:
            # 음수 offset 있음 (예: -05:00)
            return text
        # No timezone info → append KST offset (+09:00)
        # 이것이 기본 동작: 타임존 정보가 없으면 한국 시간(GMT+9)으로 간주
        return f"{text}+09:00"

    def _retrieve_task_context(self, client: Any, page_id: str) -> Dict[str, Optional[str]]:
        """Fetch current task metadata used for auto-matching or fallbacks."""

        try:
            page = client.pages.retrieve(page_id=page_id)
        except APIResponseError as exc:  # pragma: no cover - depends on live API responses
            raise ToolError(f"Notion 페이지 조회에 실패했습니다: {exc}") from exc
        except Exception as exc:  # pragma: no cover - unexpected runtime failure
            raise ToolError(f"Notion 페이지 정보를 가져오지 못했습니다: {exc}") from exc

        properties = page.get("properties", {}) if isinstance(page, dict) else {}
        title = self._extract_title_by_name(properties, self._task_properties.get("title"))
        notes = self._extract_rich_text_by_name(properties, self._task_properties.get("notes"))
        extras: Dict[str, Optional[str]] = {
            "title": title,
            "notes": notes,
        }

        relation_property = self._task_properties.get("relation")
        if relation_property:
            existing_relations = self._extract_relations(properties) or {}
            extras["relations_property_name"] = relation_property
            extras["existing_relations"] = ",".join(existing_relations.get(relation_property, [])) or None

        return extras

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

        payload = self._build_query_payload(kwargs)
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

    def _list_projects(self, client: Any, **kwargs: Any) -> ToolResult:
        database_id = self._resolve_database_id(
            kwargs.get("project_database_id") or kwargs.get("database_id"),
            self._default_project_database_id,
            self.ENV_PROJECT_DATABASE,
        )

        payload = self._build_query_payload(kwargs)
        response = client.databases.query(database_id=database_id, **payload)
        items = [self._summarise_project(page) for page in response.get("results", [])]

        return ToolResult(
            success=True,
            data={
                "items": items,
                "has_more": bool(response.get("has_more")),
                "next_cursor": response.get("next_cursor"),
                "database_id": database_id,
            },
        )

    def _find_project(self, client: Any, **kwargs: Any) -> ToolResult:
        query = self._require_non_empty(kwargs.get("query"), "query")

        list_params = dict(kwargs)
        list_params.pop("query", None)
        limit = list_params.pop("limit", None)
        if isinstance(limit, int) and limit > 0:
            list_params["page_size"] = limit
        list_params.pop("operation", None)

        # Prefer narrowing by title contains to surface more relevant candidates.
        # If a filter is not already provided, create a title-contains filter
        # using the configured project title property.
        if "filter" not in list_params or not isinstance(list_params.get("filter"), dict):
            title_prop = self._project_properties.get("title") or "Name"
            list_params["filter"] = {
                "property": title_prop,
                "title": {"contains": query},
            }

        try:
            base_result = self._list_projects(client, **list_params)
            data = base_result.unwrap()
        except ToolError as exc:
            message = str(exc)
            if "Could not find property" in message or "not a property" in message:
                # Retry without filter when the assumed title property is invalid
                list_params.pop("filter", None)
                base_result = self._list_projects(client, **list_params)
                data = base_result.unwrap()
            else:
                raise
        items = data.get("items") or []

        # Return items without automatic scoring; the LLM will decide the best match
        # based on the full list and the user's request context.
        scored_items: list[Dict[str, Any]] = []
        for item in items:
            enriched = dict(item) if isinstance(item, dict) else {"value": item}
            # deliberately no match_score field
            scored_items.append(enriched)

        return ToolResult(
            success=True,
            data={
                "query": query,
                "database_id": data.get("database_id"),
                "has_more": data.get("has_more"),
                "next_cursor": data.get("next_cursor"),
                "items": scored_items,
                "note": "이 목록을 검토하여 사용자 요청과 가장 잘 맞는 프로젝트를 선택하세요.",
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

    def _build_title_property(self, title: str, property_name: str) -> Dict[str, Any]:
        return {
            property_name: {
                "title": [
                    {
                        "text": {
                            "content": title[:2000],
                        }
                    }
                ]
            }
        }

    def _summarise_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        properties = page.get("properties", {}) if isinstance(page, dict) else {}
        title = self._extract_property_text(properties, target_type="title")
        status = self._extract_property_text(properties, target_type="status")
        date = self._extract_property_date(properties)
        summary = {
            "id": page.get("id"),
            "url": page.get("url"),
            "title": title,
            "status": status,
            "date": date,
        }

        relations = self._extract_relations(properties)
        if relations:
            summary["relations"] = relations
        return summary

    def _summarise_project(self, page: Dict[str, Any]) -> Dict[str, Any]:
        properties = page.get("properties", {}) if isinstance(page, dict) else {}
        title = self._extract_title_by_name(properties, self._project_properties.get("title"))
        status = self._extract_status_by_name(properties, self._project_properties.get("status"))
        notes = self._extract_rich_text_by_name(properties, self._project_properties.get("notes"))

        summary = {
            "id": page.get("id"),
            "url": page.get("url"),
            "title": title,
            "status": status,
            "notes": notes,
        }

        relations = self._extract_relations(properties)
        if relations:
            summary["relations"] = relations
        return summary

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

    def _extract_relations(self, properties: Dict[str, Any]) -> Optional[Dict[str, list[str]]]:
        summary: Dict[str, list[str]] = {}
        for name, value in properties.items():
            if not isinstance(value, dict):
                continue
            if value.get("type") != "relation":
                continue
            relation_entries = value.get("relation")
            if not isinstance(relation_entries, list):
                continue
            ids: list[str] = []
            for entry in relation_entries:
                if not isinstance(entry, dict):
                    continue
                relation_id = entry.get("id")
                if isinstance(relation_id, str) and relation_id.strip():
                    ids.append(relation_id)
            if ids:
                summary[name] = ids
        return summary or None

    def _resolve_todo_database_env(self) -> Optional[str]:
        todo_env = os.getenv(self.ENV_TODO_DATABASE)
        if todo_env:
            return todo_env
        return os.getenv(self.LEGACY_ENV_TASKS_DATABASE)

    def _auto_select_project_relations(
        self,
        client: Any,
        *,
        task_title: str,
        task_notes: Optional[str],
        project_database_id: Optional[str],
    ) -> Optional[list[Dict[str, str]]]:
        """Return best matching project relation or ``None`` when no clear match exists."""

        target_segments = [task_title.strip()] if task_title else []
        if task_notes:
            stripped_notes = task_notes.strip()
            if stripped_notes:
                target_segments.append(stripped_notes)
        target_text = " ".join(seg for seg in target_segments if seg)
        if not target_text:
            return None
        target_text_lower = target_text.lower()

        try:
            database_id = self._resolve_database_id(
                project_database_id,
                self._default_project_database_id,
                self.ENV_PROJECT_DATABASE,
            )
        except ToolError:
            return None

        try:
            snapshot = self._list_projects(
                client,
                project_database_id=database_id,
                page_size=self.AUTO_PROJECT_FETCH_LIMIT,
            ).unwrap()
        except ToolError:
            return None
        except Exception:  # pragma: no cover - defensive guard for unexpected data
            return None

        if not isinstance(snapshot, dict):
            return None
        items = snapshot.get("items")
        if not isinstance(items, list) or not items:
            return None

        best_candidate: Optional[Dict[str, str]] = None
        best_score = 0.0
        candidate_scores: list[float] = []

        for item in items:
            if not isinstance(item, dict):
                continue
            raw_id = item.get("id")
            candidate_id = raw_id.strip() if isinstance(raw_id, str) else None
            if not candidate_id:
                continue

            candidate_title = (item.get("title") or "").strip()
            candidate_notes = (item.get("notes") or "").strip()
            combined = f"{candidate_title} {candidate_notes}".strip()
            candidate_texts = [candidate_title, candidate_notes, combined]

            candidate_best = 0.0
            for text in candidate_texts:
                normalized = text.strip()
                if not normalized:
                    continue
                lowered = normalized.lower()
                if lowered and lowered in target_text_lower:
                    score = 1.0
                elif target_text_lower in lowered:
                    score = 0.95
                else:
                    score = SequenceMatcher(None, target_text_lower, lowered).ratio()
                if score > candidate_best:
                    candidate_best = score

            if candidate_best == 0.0:
                continue

            candidate_scores.append(candidate_best)
            if candidate_best > best_score:
                best_score = candidate_best
                best_candidate = {"id": candidate_id}

        if not best_candidate:
            return None

        sorted_scores = sorted(candidate_scores, reverse=True)
        second_best = sorted_scores[1] if len(sorted_scores) > 1 else 0.0

        if best_score < self.AUTO_MATCH_MIN_SCORE:
            return None
        if second_best >= self.AUTO_MATCH_MIN_SCORE and (best_score - second_best) < self.AUTO_MATCH_SECONDARY_GAP:
            return None

        return [best_candidate]

    def _extract_title_by_name(self, properties: Dict[str, Any], property_name: Optional[str]) -> Optional[str]:
        if property_name and property_name in properties:
            return self._extract_title_value(properties[property_name])
        return self._extract_property_text(properties, target_type="title")

    def _extract_status_by_name(self, properties: Dict[str, Any], property_name: Optional[str]) -> Optional[str]:
        if property_name and property_name in properties:
            return self._extract_status_value(properties[property_name])
        return self._extract_property_text(properties, target_type="status")

    def _extract_rich_text_by_name(
        self, properties: Dict[str, Any], property_name: Optional[str]
    ) -> Optional[str]:
        if property_name and property_name in properties:
            return self._extract_rich_text_value(properties[property_name])
        return None

    def _extract_title_value(self, value: Any) -> Optional[str]:
        if not isinstance(value, dict) or value.get("type") != "title":
            return None
        items = value.get("title", [])
        return self._first_rich_text(items)

    def _extract_status_value(self, value: Any) -> Optional[str]:
        if not isinstance(value, dict) or value.get("type") != "status":
            return None
        status = value.get("status")
        if isinstance(status, dict):
            name = status.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        return None

    def _extract_rich_text_value(self, value: Any) -> Optional[str]:
        if not isinstance(value, dict) or value.get("type") != "rich_text":
            return None
        items = value.get("rich_text", [])
        return self._first_rich_text(items)

    def _first_rich_text(self, items: Any) -> Optional[str]:
        if not isinstance(items, list) or not items:
            return None
        first = items[0]
        if not isinstance(first, dict):
            return None
        plain = first.get("plain_text")
        if isinstance(plain, str) and plain.strip():
            return plain.strip()
        text = first.get("text")
        if isinstance(text, dict):
            content = text.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
        return None

    def _resolve_property_names(
        self,
        *,
        overrides: Optional[Dict[str, str]],
        defaults: Dict[str, str],
        env_keys: Dict[str, str],
        optional_keys: Optional[set[str]] = None,
    ) -> Dict[str, Optional[str]]:
        resolved: Dict[str, Optional[str]] = dict(defaults)

        for key, env_key in env_keys.items():
            env_value = os.getenv(env_key)
            if env_value and env_value.strip():
                resolved[key] = env_value.strip()

        if overrides:
            for key, value in overrides.items():
                if value is None:
                    if optional_keys and key in optional_keys:
                        resolved[key] = None
                        continue
                    continue
                if not isinstance(value, str) or not value.strip():
                    raise ToolError("property 이름은 비어있지 않은 문자열이어야 합니다.")
                resolved[key] = value.strip()

        return resolved

    def _build_query_payload(self, kwargs: Any) -> Dict[str, Any]:
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

        return payload

    def _normalise_relations(self, raw_relations: Any) -> Optional[list[Dict[str, str]]]:
        if raw_relations is None:
            return None
        if isinstance(raw_relations, str):
            relation_id = raw_relations.strip()
            if not relation_id:
                return None
            return [{"id": relation_id}]
        if isinstance(raw_relations, dict):
            # Accept already-normalised single entry like {"id": "..."}
            rid = raw_relations.get("id")
            if isinstance(rid, str) and rid.strip():
                return [{"id": rid.strip()}]
            raise ToolError("relations 객체에는 비어있지 않은 'id' 문자열이 필요합니다.")
        if isinstance(raw_relations, list):
            relation_entries: list[Dict[str, str]] = []
            for idx, item in enumerate(raw_relations):
                if isinstance(item, str):
                    stripped = item.strip()
                    if not stripped:
                        raise ToolError("relations 항목에는 비어있는 문자열을 사용할 수 없습니다.")
                    relation_entries.append({"id": stripped})
                elif isinstance(item, dict):
                    rid = item.get("id")
                    if not isinstance(rid, str) or not rid.strip():
                        raise ToolError("relations 객체 항목에는 비어있지 않은 'id' 문자열이 필요합니다.")
                    relation_entries.append({"id": rid.strip()})
                else:
                    raise ToolError("relations 항목은 문자열 또는 {'id': string} 형식이어야 합니다.")
            return relation_entries or None
        raise ToolError("relations 파라미터는 문자열 또는 문자열 목록이어야 합니다.")

    def _canonical_operation(self, raw_operation: Any) -> str:
        if not isinstance(raw_operation, str):
            raise ToolError("operation 파라미터는 문자열이어야 합니다.")
        normalized = raw_operation.strip().lower()
        if not normalized:
            raise ToolError("operation 파라미터는 비어있지 않은 문자열이어야 합니다.")

        alias_map = {
            "create_task": "create_task",
            "list_tasks": "list_tasks",
            "list_projects": "list_projects",
            "project_list": "list_projects",
            "projects_list": "list_projects",
            "list_project": "list_projects",
            "find_project": "find_project",
            "project_find": "find_project",
            "match_project": "find_project",
            "create_todo": "create_task",
            "list_todo": "list_tasks",
            "list_todos": "list_tasks",
            "todo_create": "create_task",
            "todo_list": "list_tasks",
            "create_todos": "create_task",
            "add_todo": "create_task",
            "update_task": "update_task",
            "update_todo": "update_task",
            "todo_update": "update_task",
            "modify_task": "update_task",
            "modify_todo": "update_task",
        }

        if normalized in alias_map:
            return alias_map[normalized]

        if "todo" in normalized:
            if "list" in normalized or "조회" in normalized:
                return "list_tasks"
            if "create" in normalized or "add" in normalized or "추가" in normalized:
                return "create_task"
            if "update" in normalized or "modify" in normalized or "수정" in normalized:
                return "update_task"

        if "투두" in normalized:
            if "조회" in normalized or "list" in normalized:
                return "list_tasks"
            if "수정" in normalized or "update" in normalized or "변경" in normalized:
                return "update_task"
            return "create_task"

        raise ToolError(
            "operation 파라미터는 create_task/list_tasks/update_task/list_projects/find_project 또는 관련 별칭이어야 합니다."
        )


# ====================================================================
# CrewAI Adapter
# ====================================================================


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
    """CrewAI adapter for NotionTool"""
    name: str = "Notion 도구"
    description: str = "Notion API를 통해 할일 생성, 조회, 업데이트, 삭제 및 프로젝트 관리를 수행합니다."
    args_schema: Type[BaseModel] = NotionToolInput

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = get_logger(__name__)
        try:
            self._notion_tool = NotionTool()
            self._enabled = True
        except Exception as e:
            # Notion API 키가 없는 경우 등 초기화 실패 처리
            self._notion_tool = None
            self._enabled = False
            self._logger.warning(f"NotionTool 초기화 실패: {e}")

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
        """도구 실행 - NotionTool의 run() 메서드를 호출하여 실제 작업 수행"""
        # 전체 파라미터 상세 로깅
        import json
        all_params = {
            "operation": operation,
            "title": title,
            "content": content,
            "task_id": task_id,
            "status": status,
            "due_date": due_date,
            "project_title": project_title,
            "tags": tags,
            **kwargs
        }
        # None 값 제거
        logged_params = {k: v for k, v in all_params.items() if v is not None}
        self._logger.info(f"🔧 [NotionCrewAITool] 실행 시작 - 파라미터: {json.dumps(logged_params, ensure_ascii=False, default=str)}")

        if not self._enabled:
            error_msg = "❌ Notion 도구가 비활성화됨 (API 키 확인 필요)"
            self._logger.error(f"[NotionCrewAITool] {error_msg}")
            return error_msg

        # NotionTool의 실제 파라미터로 매핑 (content -> notes, task_id -> page_id)
        notion_params = {"operation": operation}
        if title:
            notion_params["title"] = title
        if content:
            notion_params["notes"] = content  # content -> notes 매핑
        if task_id:
            notion_params["page_id"] = task_id  # task_id -> page_id 매핑
        if status:
            notion_params["status"] = status
        if due_date:
            notion_params["due_date"] = due_date
        # project_title과 tags는 NotionTool에서 직접 지원하지 않음 (무시)

        self._logger.debug(f"[NotionCrewAITool] NotionTool로 전달할 파라미터: {json.dumps(notion_params, ensure_ascii=False, default=str)}")

        try:
            # NotionTool의 validate_parameters 호출하여 사전 검증
            is_valid, validation_error = self._notion_tool.validate_parameters(**notion_params)
            if not is_valid:
                error_msg = f"❌ 파라미터 검증 실패:\n{validation_error}"
                self._logger.error(f"[NotionCrewAITool] {error_msg}")
                return error_msg

            # NotionTool의 run() 메서드 호출
            self._logger.debug(f"[NotionCrewAITool] NotionTool.run() 호출 중...")
            result: ToolResult = self._notion_tool.run(**notion_params)

            # 결과 검증 및 상세 로깅
            if result.success:
                # 성공 시 데이터 검증
                if not result.data:
                    warning_msg = "⚠️ 성공했으나 결과 데이터가 비어있음"
                    self._logger.warning(f"[NotionCrewAITool] {warning_msg}")
                    return f"✅ 작업 완료 (데이터 없음)"

                # 결과 데이터 상세 로깅 (200자 제한)
                data_str = json.dumps(result.data, ensure_ascii=False, default=str)
                data_preview = data_str[:200] + ("..." if len(data_str) > 200 else "")
                self._logger.info(f"✅ [NotionCrewAITool] 성공 - 결과: {data_preview}")

                # 성공 메시지 포맷팅
                return self._format_success_response(result.data, operation)
            else:
                # 실패 시 에러 상세 로깅 (200자 제한)
                error_str = str(result.error) if result.error else "알 수 없는 에러"
                error_preview = error_str[:200] + ("..." if len(error_str) > 200 else "")
                self._logger.error(f"❌ [NotionCrewAITool] 실패 - 에러: {error_preview}")
                return f"❌ Notion 작업 실패: {error_preview}"

        except ToolError as e:
            # ToolError는 NotionTool에서 발생한 예상된 에러
            error_str = str(e)[:200]
            self._logger.error(f"❌ [NotionCrewAITool] ToolError - {error_str}")
            return f"❌ Notion 도구 에러: {error_str}"
        except Exception as e:
            # 예상치 못한 에러
            error_str = str(e)[:200]
            self._logger.exception(f"❌ [NotionCrewAITool] 예상치 못한 에러 - {error_str}")
            return f"❌ 도구 실행 중 예외 발생: {error_str}"

    def _format_success_response(self, data: Any, operation: str) -> str:
        """성공 응답을 사용자 친화적인 형식으로 변환"""
        import json

        if isinstance(data, dict):
            # list_tasks/list_todos 결과
            if "items" in data:
                items = data["items"]
                if not items:
                    return "✅ 할일이 없습니다."
                output = f"✅ 할일 {len(items)}개 조회:\n"
                for item in items:
                    output += f"  - [{item.get('status', '?')}] {item.get('title', '제목 없음')}"
                    if item.get('date'):
                        output += f" (마감: {item['date']})"
                    output += "\n"
                return output

            # create_task/update_task 결과
            elif "id" in data:
                task_id = data['id']
                url = data.get('url', '')
                op_display = {
                    "create_task": "할일 생성",
                    "update_task": "할일 업데이트",
                    "create_todo": "할일 생성",
                    "update_todo": "할일 업데이트",
                }.get(operation, "작업")

                result_msg = f"✅ {op_display} 완료\n"
                result_msg += f"  - ID: {task_id}\n"
                if url:
                    result_msg += f"  - URL: {url}\n"

                # relations가 있으면 표시
                if data.get('relations'):
                    result_msg += f"  - 연결된 프로젝트: {len(data['relations'])}개\n"

                self._logger.info(f"[NotionCrewAITool] {op_display} 성공 - ID: {task_id}")
                return result_msg

            # 기타 dict 응답
            else:
                return f"✅ 성공:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
        else:
            # dict가 아닌 응답
            return f"✅ 성공: {data}"
