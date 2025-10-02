# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Angmini** is a personal AI assistant built on Google Gemini using the ReAct (Reasoning and Acting) pattern. It features a multi-interface system (CLI, Discord), extensible MCP tool ecosystem, and an intelligent long-term memory system with vector-based semantic search.

## Commands

### Development & Testing

```bash
# Run the application (uses DEFAULT_INTERFACE from .env)
python main.py

# Run with virtual environment
python -m pip install -r requirements.txt
python main.py

# Run tests (pytest must be installed)
pytest tests/
pytest tests/test_file_tool.py          # Single test file
pytest tests/ -v                        # Verbose output

# Quick Gemini API check
python scripts/gemini_quickcheck.py
```

### Memory System

```bash
# Memory data is stored in:
# - data/memory/memories.db (SQLite metadata)
# - data/memory/memory.index (FAISS vector index)
# - data/memory/memory.ids (ID mappings)

# Memory embedding logs
tail -f memory_embedding.log
```

## Core Development Rules

The following rules must be followed when working on this project:

### 1. Design-First Development (Rule 0)
- **Guideline:** Before any coding, always consult `PLAN_for_AI_Agent.md`. All actions must align with the documented design.
- **Prohibition:** Never alter the architecture or design without explicit user approval.

### 2. Design for Extensibility (Rule 1)
- **Guideline:** Design the system to minimize code modifications when adding new components like Tools or LLM models. Actively use extension points such as `ToolRegistry`.

### 3. Explicit Failure Handling (Rule 2)
- **Guideline:** When a failure occurs (e.g., API connection error), do not mask it with mock data or fallback logic. Instead, raise an explicit `Error`.
- **Objective:** To enable immediate identification and resolution of the root cause.

### 4. Root Cause Resolution (Rule 3)
- **Guideline:** Do not implement temporary workarounds for specific examples provided by the user (e.g., patching a prompt to fix a single notification issue).
- **Objective:** Implement robust, structural solutions that prevent the recurrence of similar problems.

### 5. Clear and Detailed Comments (Rule 4)
- **Guideline:** Write comments that focus on the **"why"** behind the code, not just the "what." Document complex logic and key design decisions.
- **Objective:** To ensure the code's intent is immediately understandable to future developers (including yourself).

### 6. User-Friendly Communication (Rule 5)
- **Guideline:** Minimize technical jargon. Use analogies and simple terms to explain progress and technical concepts.
- **Objective:** To help the user understand the development process intuitively, regardless of their technical background.

## Architecture & Design Principles

### Core Execution Flow

1. **Entry Point** (`main.py`): Loads config, dispatches to interface based on `DEFAULT_INTERFACE` env var
2. **Interface Layer** (`interface/`): CLI or Discord bot receives user input
3. **GoalExecutor** (`ai/react_engine/goal_executor.py`):
   - Orchestrates ReAct loop
   - Calls `_update_plan()` to generate JSON plan via LLM
   - Executes steps via `StepExecutor`
   - Handles failures via `PlanningEngine` and `LoopDetector`
4. **ToolManager** (`mcp/tool_manager.py`): Routes tool calls to registered implementations
5. **Memory System**: Captures execution context, stores via `MemoryService`, retrieves via `CascadedRetriever`

### ReAct Engine Pattern

The ReAct engine in `ai/react_engine/` follows a structured planning-execution cycle:

- **Planning Phase**: LLM generates JSON array of `PlanStep` objects with `{id, description, tool, parameters, status}`
- **Execution Phase**: `StepExecutor` calls tools via `ToolManager`, records results in `ExecutionContext`
- **Failure Recovery**:
  - `LoopDetector` identifies repetitive failures
  - `PlanningEngine` decides between retry/replan
  - Failures logged to `ExecutionContext.fail_log` for next planning iteration
- **Safety**: `SafetyGuard` enforces step/retry limits

**Key Invariant**: Plan steps must progress toward goal completion. If all steps are read-only operations (e.g., `list_tasks`), `GoalExecutor._should_request_follow_up_plan()` triggers automatic replanning (max 3 times) to add state-changing actions.

### Memory System Design

Located in `ai/memory/`:

- **Storage**: SQLite (`storage/sqlite_store.py`) + FAISS (`storage/vector_index.py`) + Qwen3 embeddings
- **Capture Pipeline** (`pipeline.py`): `ExecutionContext` → `MemoryCurator` (LLM-based summarization) → `Deduplicator` → Storage
- **Retrieval**:
  - Simple: `MemoryRepository.search(query, top_k=3)` (direct embedding similarity)
  - Advanced: `CascadedRetriever` (iterative LLM-filtered search with follow-up queries)
- **Integration**: `GoalExecutor._prefetch_relevant_memories()` injects top matches into planning prompt

**Memory Records** (`memory_records.py`): Each record includes `summary`, `goal`, `user_intent`, `outcome`, `tools_used`, `tags`, `category`, embeddings.

### Tool System (MCP)

Tools inherit from `ToolBlueprint` (`mcp/tool_blueprint.py`):

```python
class ToolBlueprint(ABC):
    @abstractmethod
    def tool_name(self) -> str: ...

    @abstractmethod
    def schema(self) -> Dict[str, Any]: ...

    @abstractmethod
    def __call__(self, **kwargs) -> ToolResult: ...
```

**Built-in Tools**:
- `FileTool` (`mcp/tools/file_tool.py`): File I/O, listing, search
- `NotionTool` (`mcp/tools/notion_tool.py`): Task/project CRUD via Notion API
- `MemoryTool` (`mcp/tools/memory_tool.py`): Search experiences, find solutions, analyze patterns
- `AppleTool` (`mcp/tools/apple_tool.py`): macOS integration (Notes, Reminders, Calendar, etc.) via Apple MCP subprocess

**Tool Registration**: Interface initialization calls `create_default_tool_manager()` from `mcp/__init__.py`, which registers all tools.

### Multi-Interface Architecture

- **CLI** (`interface/cli.py`): Interactive REPL, streams execution summary
- **Discord** (`interface/discord_bot.py`): Async message handler, responds in-channel
- **Switching**: Set `DEFAULT_INTERFACE=cli` or `DEFAULT_INTERFACE=discord` in `.env`

Both interfaces use `GoalExecutorFactory.create()` to obtain a fresh `GoalExecutor` instance per request.

### Token Usage Tracking

`ExecutionContext.record_token_usage(metadata, category)` accumulates:
- `thinking_tokens`: Planning/reasoning phases
- `response_tokens`: Final message generation
- Total displayed in `GoalExecutor._decorate_final_message()`

### Error Handling Strategy

1. **Tool Errors**: Wrapped in `ToolError`, logged to `ExecutionContext.fail_log`, fed to next planning iteration
2. **Step Failures**: `StepExecutor` returns `StepResult(outcome=FAILURE, error_reason=...)`
3. **Replanning Triggers**:
   - Retry limit exceeded (`PlanningEngine` checks `attempt_counts`)
   - Loop detected (`LoopDetector.evaluate()`)
   - Plan structurally insufficient (read-only operations only)
4. **Graceful Degradation**: Apple MCP failures log warnings but don't crash app (see `cli.py:_initialize_apple_mcp_server`)

## Important Files & Their Roles

### Configuration & Core
- `ai/core/config.py`: Environment variable loader (`Config.load()`), validates API keys
- `ai/core/logger.py`: Structured logging with timestamped session files (`logs/YYYYMMDD_HHMMSS.log`)
- `ai/core/exceptions.py`: Custom exceptions (`EngineError`, `ToolError`, `ConfigError`, `InterfaceError`)

### ReAct Engine
- `ai/react_engine/goal_executor.py`: Main orchestrator (776 lines, see line 97 for `run()` method)
- `ai/react_engine/step_executor.py`: Tool execution wrapper
- `ai/react_engine/planning_engine.py`: Retry/replan decision logic
- `ai/react_engine/models.py`: Data classes (`PlanStep`, `ExecutionContext`, `StepResult`, events)
- `ai/react_engine/prompt_templates/`: LLM prompt templates (Markdown files)

### Memory
- `ai/memory/service.py`: High-level API (`MemoryService.capture()`, `MemoryService.repository.search()`)
- `ai/memory/cascaded_retriever.py`: Iterative LLM-filtered retrieval
- `ai/memory/factory.py`: Initializes SQLite + FAISS + Qwen embeddings
- `ai/memory/storage/repository.py`: Unified interface over SQLite/FAISS

### Tools
- `mcp/__init__.py`: `create_default_tool_manager()` factory
- `mcp/tools/notion_tool.py`: Notion API client (task CRUD, project relations)
- `mcp/tools/apple_tool.py`: Subprocess wrapper for `external/apple-mcp/` (TypeScript/Node.js)

### External Dependencies
- `external/apple-mcp/`: Git submodule (TypeScript MCP server for macOS apps)
- `requirements.txt`: Python dependencies (torch, transformers, faiss-cpu, discord.py, notion-client, etc.)

## Environment Variables (`.env`)

**Required**:
- `GEMINI_API_KEY`: Google Gemini API key (mandatory)
- `DEFAULT_INTERFACE`: `cli` or `discord`

**Optional**:
- `GEMINI_MODEL`: Default `models/gemini-1.5-pro`
- `DISCORD_BOT_TOKEN`: Required if using Discord interface
- `NOTION_API_KEY`, `NOTION_TODO_DATABASE_ID`, `NOTION_PROJECT_DATABASE_ID`: For Notion integration
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default `INFO`)
- `STREAM_DELAY`: Streaming output delay in seconds (default `0.05`)

See `.env.example` for complete reference.

## Development Guidelines

### When Adding New Tools

1. Subclass `ToolBlueprint` in `mcp/tools/`
2. Implement `tool_name()`, `schema()`, `__call__()` returning `ToolResult`
3. Register in `create_default_tool_manager()` (`mcp/__init__.py`)
4. Document parameters with `type`, `description`, `enum` in schema (used by LLM planning)

### When Modifying ReAct Prompts

- Templates in `ai/react_engine/prompt_templates/` are injected into LLM calls
- `system_prompt.md`: Defines assistant personality and tool usage guidelines
- Planning prompt in `goal_executor.py:_build_plan_prompt()`: Includes tool schemas, memory insights, failure logs
- Changes here directly affect LLM plan quality

### When Extending Memory System

- Memory capture triggers on: tool usage, personal signals (keywords like "내", "좋아하는"), or non-trivial token usage
- `_should_capture_memory()` in `goal_executor.py` defines capture heuristics
- Retention policy in `ai/memory/retention_policy.py` (currently allows all)

### Testing Philosophy

- Tests in `tests/` use pytest (not currently installed by default)
- Integration tests (`test_react_engine_integration.py`) verify end-to-end flows
- Mock external APIs (Gemini, Notion) in unit tests
- Memory tests (`test_memory_repository.py`, `test_qwen3_embedding_vector_store.py`) validate embedding/search

## Common Pitfalls

1. **OpenMP Conflicts**: Memory system sets `KMP_DUPLICATE_LIB_OK=TRUE` to allow both PyTorch and FAISS (see `goal_executor.py:531`)
2. **Apple MCP Lifecycle**: Must call `_ensure_server_running()` before first use (handled in CLI/Discord init)
3. **Plan JSON Parsing**: LLM responses may include markdown fences; `_parse_plan_response()` strips them (line 246)
4. **Notion Relations**: `create_task` auto-matches projects by title if relation property is empty
5. **Memory Embedding Model**: Default loads `Qwen/Qwen3-Embedding-0.6B` from Hugging Face Hub; override with `QWEN3_EMBEDDING_PATH` for local model

## Debugging Tips

- Session logs: `logs/YYYYMMDD_HHMMSS.log` (timestamped per run)
- Memory embedding: `memory_embedding.log`
- Enable DEBUG logging: Set `LOG_LEVEL=DEBUG` in `.env`
- Trace ReAct loops: Look for `"Executing step X (attempt Y)"` in logs
- Check token usage: Final response includes `[tokens_total=X, thinking_tokens=Y, response_tokens=Z]`

## Project Status (from PLAN_for_AI_Agent.md)

- ✅ Phase 1-2: Core ReAct engine complete
- ✅ Phase 3: Tools (File, Notion, Apple MCP) implemented
- ✅ Phase 4-4.5: Memory system with cascaded retrieval complete
- ⏸️ Phase 5: Proactive notification system (planned, not started)
- 🚧 Testing coverage incomplete (pytest not in requirements.txt)

## Additional Resources

- Development plan: `PLAN_for_AI_Agent.md` (detailed roadmap with checkboxes)
- User guide: `docs/USAGE.md`
- Memory maintenance: `docs/memory_maintenance.md`
- Apple tool guide: `docs/APPLE_TOOL_GUIDE.md`