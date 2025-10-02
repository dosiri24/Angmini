# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Angmini** is a personal AI assistant built on Google Gemini using the CrewAI multi-agent framework. It features specialized agents that collaborate through hierarchical processes, an extensible MCP tool ecosystem, and an intelligent long-term memory system with vector-based semantic search.

## Commands

### Quick CLI Testing (Recommended for AI)

The `bin/angmini` script allows direct testing without manual interaction:

```bash
# Show help and available options (instant)
bin/angmini --help

# Check version (instant)
bin/angmini --version

# Execute single command (3-5 seconds)
bin/angmini --no-stream "안녕"

# More complex commands (8-15 seconds) - ⚠️ May timeout in Claude Code
bin/angmini --no-stream "현재 디렉토리 파일 목록 보여줘"

# Debug mode (verbose CrewAI output)
bin/angmini --debug "테스트"

# Interactive mode (requires user input)
bin/angmini
```

**⚠️ Claude Code Timeout Warning:**
- Bash tool has 2-minute default timeout (max 10 minutes)
- Angmini initialization: 4-6 seconds
- Simple queries: 3-5 seconds (safe)
- Complex queries: 8-20 seconds (may timeout)
- **Solution**: Use `timeout=600000` parameter (10 minutes) when calling Bash tool
- **Alternative**: Test with simple commands only (`--version`, `--help`, `"안녕"`)

#### Understanding Test Results

**Successful Execution:**
```bash
$ bin/angmini --no-stream "안녕"
🍎 Apple MCP 서버가 준비되었습니다!

📝 최종 결과:
안녕하세요! 저는 작업 계획 및 조율 총괄 책임자 Angmini입니다. 무엇을 도와드릴까요?
```

**What to Look For:**
- ✅ `🍎 Apple MCP 서버가 준비되었습니다!` (macOS only) - AppleAppsAgent ready
- ✅ `📝 최종 결과:` followed by AI response - Task completed successfully
- ✅ Exit code 0 - No errors occurred
- ✅ Execution time typically 2-5 seconds for simple queries

**Common Issues:**
- ❌ `Configuration error: GEMINI_API_KEY is missing` - Check `.env` file
- ❌ `ModuleNotFoundError` - Activate virtual environment: `source .venv/bin/activate`
- ❌ Timeout (>60s) - Check network connection or API quota

#### Agent-Specific Testing

**FileAgent (파일 시스템 관리)**
```bash
bin/angmini --no-stream "현재 디렉토리의 Python 파일 목록 보여줘"
# Expected: List of .py files in current directory
```

**MemoryAgent (장기 기억)**
```bash
bin/angmini --no-stream "최근에 뭐 작업했어?"
# Expected: Summary of recent tasks from memory
```

**AppleAppsAgent (macOS 내장 앱 연동, macOS only)**
```bash
bin/angmini --no-stream "Mac의 Notes 앱에 있는 노트 목록 보여줘"
# Expected: List of notes from macOS Notes app
```

**NotionAgent (Notion 워크스페이스)**
```bash
bin/angmini --no-stream "Notion에서 오늘 할 일 목록 가져와줘"
# Expected: TODO items from Notion database
# Requires: NOTION_API_KEY in .env
```

#### Performance Benchmarking

```bash
# Measure execution time
time bin/angmini --no-stream "안녕"
# Typical: 2-5 seconds for simple queries

# Check token usage (in logs)
bin/angmini --no-stream "테스트" 2>&1 | grep "토큰:"
# Example: 토큰: 1745 (입력: 1579, 출력: 166)
```

#### Debug Mode Output

When testing with `--debug`, you'll see detailed CrewAI execution:
```bash
bin/angmini --debug "테스트"
```

**Key Debug Indicators:**
- Agent initialization: `Agent '작업 계획 및 조율 총괄 책임자' 생성 완료`
- Task execution: `Agent [Unknown] 작업 중`
- Completion: `CrewAI 완료 [2.7초] - 결과: 51자`
- Token usage: `토큰: 1745 (입력: 1579, 출력: 166)`
- Memory: `메모리 저장 완료`

See `TESTING.md` for comprehensive testing scenarios and troubleshooting.

### Development & Testing

```bash
# Run the application (uses DEFAULT_INTERFACE from .env)
python main.py

# Run with DEBUG mode (shows CrewAI verbose output)
LOG_LEVEL=DEBUG python main.py

# Run with virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
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
- **Guideline:** Design the system to minimize code modifications when adding new components. Use extension points like `AgentFactory` and `ToolRegistry`.

### 3. Explicit Failure Handling (Rule 2)
- **Guideline:** When a failure occurs (e.g., API connection error), raise an explicit error instead of masking it.
- **Objective:** Enable immediate identification and resolution of the root cause.

### 4. Root Cause Resolution (Rule 3)
- **Guideline:** Implement robust, structural solutions that prevent problem recurrence, not temporary workarounds.

### 5. Clear and Detailed Comments (Rule 4)
- **Guideline:** Write comments that focus on the **"why"** behind the code, not just the "what."
- **Objective:** Ensure the code's intent is immediately understandable to future developers.

### 6. User-Friendly Communication (Rule 5)
- **Guideline:** Minimize technical jargon. Use analogies and simple terms to explain progress.

### 7. 100% LLM-Based Decision Making (Rule 6)
- **Guideline:** **STRICTLY PROHIBITED**: Keyword parsing or pattern matching for user intent analysis or agent selection.
- **Required Approach**: Use LLM's natural language understanding exclusively for all decision making.
- **Examples**:
  - ❌ **WRONG**: `if "파일" in user_request or "file" in user_request.lower(): select FileAgent`
  - ❌ **WRONG**: `action_words = ["조회", "목록", ...]; if any(word in request): return "task_request"`
  - ✅ **CORRECT**: Let PlannerAgent's LLM analyze user request naturally and delegate to appropriate worker
- **Rationale**: Keyword parsing is fragile, non-extensible, and contradicts the LLM-based architecture. CrewAI's hierarchical delegation with proper prompts provides superior flexibility and accuracy.

## Architecture & Design Principles

### Core Execution Flow (CrewAI v2.0)

1. **Entry Point** (`main.py`): Loads config, dispatches to interface based on `DEFAULT_INTERFACE` env var
2. **Interface Layer** (`interface/`): CLI or Discord bot receives user input
3. **AngminiCrew** (`crew/crew_config.py`):
   - Initializes PlannerAgent (Manager) and 4 worker agents
   - Creates Task objects via `TaskFactory`
   - Executes Crew with Hierarchical or Sequential process
4. **Agent System** (`agents/`):
   - **PlannerAgent**: Manager role, delegates tasks to specialists
   - **FileAgent**: File system operations
   - **NotionAgent**: Notion workspace management
   - **MemoryAgent**: Long-term memory retrieval
   - **AppleAppsAgent**: macOS native apps integration via Apple MCP
5. **Tool System** (`mcp/`): MCP tools adapted to CrewAI BaseTool via adapters
6. **Memory System**: Captures execution context after task completion

### CrewAI Multi-Agent Pattern

The system uses CrewAI's hierarchical process where agents collaborate:

- **Hierarchical Process**: PlannerAgent acts as Manager, delegates to specialized workers
- **Sequential Process**: Alternative mode where tasks execute sequentially
- **Agent Specialization**: Each agent has a specific domain and dedicated tools
- **Tool Integration**: MCP tools wrapped as CrewAI BaseTools via adapters in `mcp/crewai_adapters/`

**Key Flow**:
1. User input → `AngminiCrew.kickoff()`
2. `TaskFactory.create_tasks_from_input()` creates Task objects
3. Crew executes with Manager (Planner) delegating to workers
4. Workers use their specialized CrewAI-adapted tools
5. Results aggregated and returned to user
6. Execution context saved to memory (if `memory_service` enabled)

### Memory System Design

Located in `ai/memory/`:

- **Storage**: SQLite (`storage/sqlite_store.py`) + FAISS (`storage/vector_index.py`) + Qwen3 embeddings
- **Capture Pipeline** (`pipeline.py`): `ExecutionContext` → `MemoryCurator` (LLM-based summarization) → `Deduplicator` → Storage
- **Retrieval**:
  - Simple: `MemoryRepository.search(query, top_k=3)` (direct embedding similarity)
  - Advanced: `CascadedRetriever` (iterative LLM-filtered search with follow-up queries)
- **Integration**: MemoryAgent provides access to long-term memory during task execution

**Memory Records** (`memory_records.py`): Each record includes `summary`, `goal`, `user_intent`, `outcome`, `tools_used`, `tags`, `category`, embeddings.

### Tool System (MCP + CrewAI)

**MCP Tools** inherit from `ToolBlueprint` (`mcp/tool_blueprint.py`):

```python
class ToolBlueprint(ABC):
    @abstractmethod
    def tool_name(self) -> str: ...

    @abstractmethod
    def schema(self) -> Dict[str, Any]: ...

    @abstractmethod
    def __call__(self, **kwargs) -> ToolResult: ...
```

**CrewAI Adaptation** (`mcp/crewai_adapters/`):
- MCP tools wrapped as CrewAI `BaseTool` via adapter classes
- Each agent receives its specialized tools during initialization
- Tools execute via original MCP implementations, results returned to CrewAI

**Built-in Tools**:
- `FileTool` (`mcp/tools/file_tool.py`): File I/O, listing, search
- `NotionTool` (`mcp/tools/notion_tool.py`): Task/project CRUD via Notion API
- `MemoryTool` (`mcp/tools/memory_tool.py`): Search experiences, find solutions, analyze patterns
- `AppleTool` (`mcp/tools/apple_tool.py`): macOS integration (Notes, Reminders, Calendar, etc.) via Apple MCP subprocess

**Tool-Agent Mapping**:
- FileAgent → FileTool adapter
- NotionAgent → NotionTool adapter
- MemoryAgent → MemoryTool adapter
- AppleAppsAgent → AppleTool adapter

### Multi-Interface Architecture

- **CLI** (`interface/cli.py`): Interactive REPL, streams execution summary
- **Discord** (`interface/discord_bot.py`): Async message handler, responds in-channel
- **Switching**: Set `DEFAULT_INTERFACE=cli` or `DEFAULT_INTERFACE=discord` in `.env`

Both interfaces create `AngminiCrew` instance and call `kickoff(user_input)` for execution.

### Error Handling Strategy

1. **CrewAI Errors**: Logged with execution time, re-raised to caller
2. **Tool Failures**: Wrapped in `ToolError`, returned to CrewAI for recovery
3. **Agent Failures**: CrewAI handles retry logic automatically
4. **Graceful Degradation**: Apple MCP failures log warnings but don't crash app (see `cli.py:_initialize_apple_mcp_server`)

## Important Files & Their Roles

### Configuration & Core
- `ai/core/config.py`: Environment variable loader (`Config.load()`), validates API keys
- `ai/core/logger.py`: Structured logging with timestamped session files (`logs/YYYYMMDD_HHMMSS.log`)
- `ai/core/exceptions.py`: Custom exceptions (`EngineError`, `ToolError`, `ConfigError`, `InterfaceError`)

### CrewAI System (New Architecture)
- `crew/crew_config.py`: `AngminiCrew` orchestrator (initializes agents, creates Crew, executes tasks)
- `crew/task_factory.py`: Converts user input to CrewAI Task objects
- `agents/__init__.py`: `AgentFactory` for creating all agent instances
- `agents/base_agent.py`: `BaseAngminiAgent` abstract class all agents inherit from
- `agents/planner_agent.py`: Manager agent for hierarchical process
- `agents/file_agent.py`, `notion_agent.py`, `memory_agent.py`, `apple_apps_agent.py`: Specialized worker agents

### MCP Tools
- `mcp/__init__.py`: `create_default_tool_manager()` factory
- `mcp/tools/notion_tool.py`: Notion API client (task CRUD, project relations)
- `mcp/tools/apple_tool.py`: Subprocess wrapper for `external/apple-mcp/` (TypeScript/Node.js)
- `mcp/crewai_adapters/`: Adapter classes wrapping MCP tools as CrewAI BaseTools

### Memory
- `ai/memory/service.py`: High-level API (`MemoryService.capture()`, `MemoryService.repository.search()`)
- `ai/memory/cascaded_retriever.py`: Iterative LLM-filtered retrieval
- `ai/memory/factory.py`: Initializes SQLite + FAISS + Qwen embeddings
- `ai/memory/storage/repository.py`: Unified interface over SQLite/FAISS

### Legacy (Preserved for Reference)
- `interface/cli_react_backup.py`: Original ReAct engine CLI implementation
- `interface/discord_bot_react_backup.py`: Original ReAct engine Discord bot
- `ai/react_engine/`: Complete ReAct engine implementation (preserved but not actively used)

### External Dependencies
- `external/apple-mcp/`: Git submodule (TypeScript MCP server for macOS apps)
- `requirements.txt`: Python dependencies (crewai, crewai-tools, torch, transformers, faiss-cpu, discord.py, notion-client, etc.)

## Environment Variables (`.env`)

**Required**:
- `GEMINI_API_KEY`: Google Gemini API key (mandatory)
- `DEFAULT_INTERFACE`: `cli` or `discord`

**Optional**:
- `GEMINI_MODEL`: Default `gemini-2.5-pro`
- `DISCORD_BOT_TOKEN`: Required if using Discord interface
- `NOTION_API_KEY`, `NOTION_TODO_DATABASE_ID`, `NOTION_PROJECT_DATABASE_ID`: For Notion integration
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default `INFO`)
- `STREAM_DELAY`: Streaming output delay in seconds (default `0.01`)
- `CREW_PROCESS_TYPE`: `hierarchical` or `sequential` (default `hierarchical`)
- `CREW_MEMORY_ENABLED`: `true` or `false` (enables CrewAI built-in memory)

See `.env.example` for complete reference.

## Development Guidelines

### When Adding New Agents

1. Subclass `BaseAngminiAgent` in `agents/`
2. Implement required methods: `role()`, `goal()`, `backstory()`, `tools()`
3. Create corresponding CrewAI tool adapter in `mcp/crewai_adapters/` if new tools are needed
4. Register in `AgentFactory.create_all_agents()` (`agents/__init__.py`)

### When Adding New Tools

1. Subclass `ToolBlueprint` in `mcp/tools/`
2. Implement `tool_name()`, `schema()`, `__call__()` returning `ToolResult`
3. Create CrewAI adapter in `mcp/crewai_adapters/` inheriting from `BaseTool`
4. Assign to appropriate agent in `agents/` via the `tools()` method

### When Modifying Agent Behavior

- Agent prompts defined in `role()`, `goal()`, `backstory()` methods
- Each agent's `build_agent()` method constructs the CrewAI Agent with LLM config
- Changes to agent personalities affect collaboration dynamics
- Test with both hierarchical and sequential process modes

### When Extending Memory System

- Memory capture triggers on task completion in `crew_config.py:kickoff()`
- `_should_capture_memory()` logic can be customized in `MemoryService`
- Retention policy in `ai/memory/retention_policy.py` (currently allows all)

### Testing Philosophy

- Tests in `tests/` use pytest (not currently installed by default)
- Integration tests should mock external APIs (Gemini, Notion)
- Memory tests (`test_memory_repository.py`, `test_qwen3_embedding_vector_store.py`) validate embedding/search
- CrewAI integration tests should verify agent collaboration and tool usage

## Common Pitfalls

1. **OpenMP Conflicts**: Memory system sets `KMP_DUPLICATE_LIB_OK=TRUE` to allow both PyTorch and FAISS (see `memory/factory.py`)
2. **Apple MCP Lifecycle**: Must initialize before first use (handled in CLI/Discord init)
3. **CrewAI Output Suppression**: Rich console output is captured to prevent noise (see `crew_config.py:kickoff`)
4. **Notion Relations**: `create_task` auto-matches projects by title if relation property is empty
5. **Memory Embedding Model**: Default loads `Qwen/Qwen3-Embedding-0.6B` from Hugging Face Hub; override with `QWEN3_EMBEDDING_PATH` for local model
6. **Agent Tool Access**: Each agent only has access to tools defined in its `tools()` method - don't expect agents to use tools they weren't assigned

## Debugging Tips

- Session logs: `logs/YYYYMMDD_HHMMSS.log` (timestamped per run)
- Memory embedding: `memory_embedding.log`
- Enable DEBUG logging: Set `LOG_LEVEL=DEBUG` in `.env` (shows CrewAI verbose output)
- Trace agent execution: Look for agent role/goal in logs during task delegation
- Check token usage: CrewAI provides usage metrics after execution
- Rich output suppression: If you need to see CrewAI's visual output, comment out stdout/stderr capture in `crew_config.py`

## Project Status

- ✅ **Phase 1-2**: Core CrewAI multi-agent system complete (v2.0.0 - Oct 2025)
- ✅ **Phase 3**: Tools (File, Notion, Apple MCP) implemented and adapted to CrewAI
- ✅ **Phase 4-4.5**: Memory system with cascaded retrieval complete
- ⏸️ **Phase 5**: Proactive notification system (planned, not started)
- 🚧 Testing coverage incomplete (pytest not in requirements.txt)

## Additional Resources

- Development plan: `PLAN_for_AI_Agent.md` (detailed roadmap with checkboxes)
- CrewAI migration: `docs/CREWAI_MIGRATION_PLAN.md`
- User guide: `docs/USAGE.md`
- Memory maintenance: `docs/memory_maintenance.md`
- Apple tool guide: `docs/APPLE_TOOL_GUIDE.md`

## Migration Notes (ReAct → CrewAI)

The project successfully migrated from custom ReAct engine to CrewAI multi-agent framework:

**What Changed**:
- Custom ReAct loop (GoalExecutor, StepExecutor) → CrewAI Hierarchical Process
- Single-agent planning → Multi-agent collaboration with specialized roles
- Tool execution via ToolManager → Tools adapted to CrewAI BaseTool
- Manual failure recovery → CrewAI automatic retry/delegation

**What Stayed**:
- MCP tool implementations (FileTool, NotionTool, etc.) remain unchanged
- Memory system (capture, storage, retrieval) unchanged
- Interface layer (CLI, Discord) preserved with minimal changes
- Configuration system (Config, Logger, exceptions) unchanged

**Legacy Code** (preserved in `interface/*_backup.py` and `ai/react_engine/`):
- Original ReAct engine remains for reference
- Can be studied for understanding custom agent implementation patterns
- Not actively maintained or used in production
