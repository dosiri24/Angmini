# ReAct Planning Examples

## Scenario 1: Notion - Fill Empty Relations

### User Goal
"현재 노션에 경험/프로젝트 란이 비어있는 것들이 있어. 이것들 작업명 참고해서 알아서 채워넣어줘"

### ❌ WRONG APPROACH (causes infinite loop)
```json
[
  {
    "id": 1,
    "tool": "notion",
    "parameters": {"operation": "list_tasks"}
  },
  {
    "id": 2,
    "tool": "notion",
    "parameters": {
      "operation": "update_task",
      "page_id": "<step 1 result>",  // ❌ INVALID
      "relations": ["<project ID>"]   // ❌ INVALID
    }
  }
]
```

### ✅ CORRECT APPROACH (step-by-step with data gathering)

**Step 1**: List tasks with empty relations
```json
[
  {
    "id": 1,
    "description": "경험/프로젝트가 비어있는 작업 조회",
    "tool": "notion",
    "parameters": {
      "operation": "list_tasks",
      "filter": {
        "property": "경험/프로젝트",
        "relation": {"is_empty": true}
      }
    }
  }
]
```

**After Step 1 completes**, the system shows observation data with task IDs. Plan Step 2:

**Step 2**: List all available projects
```json
[
  {
    "id": 2,
    "description": "사용 가능한 프로젝트 목록 조회",
    "tool": "notion",
    "parameters": {"operation": "list_projects"}
  }
]
```

⚠️ **IMPORTANT**: Do NOT use `find_project` operation. Use `list_projects` instead, then match in your reasoning.

**After Step 2 completes**, you can now see both tasks and projects. Match them and plan Step 3:

**Step 3**: Update task with matched project
```json
[
  {
    "id": 3,
    "description": "'GPS개론 과제3' 작업을 'GPS개론' 프로젝트에 연결",
    "tool": "notion",
    "parameters": {
      "operation": "update_task",
      "page_id": "22eddd5c74a08077940df80c70d1648d",  // ✅ From Step 1 observation
      "relations": ["111aaa11-1111-1111-1111-111111111111"]  // ✅ From Step 2 observation
    }
  }
]
```

**Matching Logic**:
- Task: "GPS개론 과제3 9999문의" → Extract keyword: "GPS개론"
- Projects: ["GPS개론", "해운물류 실습", "대학 2025-2"]
- Best match: "GPS개론" (exact keyword match)
- Use IDs from observations to create update_task step

## Scenario 2: File Search

### User Goal
"config.json 파일 찾아서 API 키 설정 확인해줘"

### ❌ WRONG: Trying to read before finding
```json
[
  {
    "id": 1,
    "tool": "file",
    "parameters": {
      "operation": "read",
      "path": "config.json"  // ❌ Don't know full path yet
    }
  }
]
```

### ✅ CORRECT: Search first, then read
```json
[
  {
    "id": 1,
    "description": "config.json 파일 위치 찾기",
    "tool": "file",
    "parameters": {
      "operation": "list",
      "path": ".",
      "recursive": true
    }
  }
]
```

After finding file at `/app/settings/config.json`:

```json
[
  {
    "id": 2,
    "description": "config.json 파일 읽기",
    "tool": "file",
    "parameters": {
      "operation": "read",
      "path": "/app/settings/config.json"  // ✅ Full path from observation
    }
  }
]
```

## Scenario 3: Simple Conversation

### User Goal
"안녕하세요!"

### ✅ CORRECT: No tools needed
```json
[
  {
    "id": 1,
    "description": "안녕하세요! 무엇을 도와드릴까요?",
    "tool": null,
    "parameters": {}
  }
]
```

## Chain-of-Thought Template

Before planning, always think:
1. What information do I have? (Check observations)
2. What information do I need? (Identify gaps)
3. Can I complete this in one step with current information?
   - YES → Create action step with concrete values
   - NO → Create information gathering step

## Common Patterns

### Pattern: Update with Relation
```
1. List items without relation
2. List available relations
3. Match items to relations
4. Update each item with appropriate relation
```

### Pattern: Find and Modify
```
1. Search for target
2. Read/examine target
3. Modify target
```

### Pattern: Create with Context
```
1. Gather context (existing items, categories)
2. Create new item with proper categorization
```