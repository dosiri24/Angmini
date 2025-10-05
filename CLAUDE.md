# CLAUDE.md

AI assistant guidance for working with the Angmini codebase.

## Project Overview

**Angmini**: CrewAI-based multi-agent system with Gemini LLM, specialized agents (Planner, File, Notion, Memory, AppleApps), MCP tool ecosystem, and vector-based long-term memory (SQLite + FAISS + Qwen3).

## Quick Reference

**Test Command**: `bin/angmini --no-stream "안녕"` (3-5s)
**Debug Mode**: `bin/angmini --debug "query"`
**Run App**: `python main.py` (uses `DEFAULT_INTERFACE` from `.env`)
**Logs**: `logs/YYYYMMDD_HHMMSS.log`, `memory_embedding.log`
**Memory Data**: `data/memory/` (memories.db, memory.index, memory.ids)

## Commands

### Testing
```bash
bin/angmini --no-stream "안녕"        # Quick test (3-5s)
bin/angmini --debug "query"          # Verbose CrewAI output
bin/angmini --version                # Version check
```

⚠️ **Timeout**: Complex queries (8-20s) may timeout. Use `timeout=600000` in Bash tool or test with simple commands.

**Success Indicators**: `🍎 Apple MCP 서버가 준비되었습니다!` (macOS), `📝 최종 결과:`, exit code 0

**Common Errors**: Missing `GEMINI_API_KEY` (check `.env`), `ModuleNotFoundError` (activate venv: `source .venv/bin/activate`)

### Development
```bash
python main.py                       # Run app
LOG_LEVEL=DEBUG python main.py       # Debug mode
pytest tests/                        # Run tests
python scripts/gemini_quickcheck.py  # API check
```

## Core Development Rules

1. **Design-First**: Consult `PLAN_for_AI_Agent.md` before coding. Never alter architecture without user approval.
2. **Extensibility**: Use `AgentFactory`, `ToolRegistry` patterns. Minimize code changes when adding components.
3. **Explicit Errors**: Raise clear exceptions (don't mask failures). Enable root cause identification.
4. **Root Cause Fixes**: Implement structural solutions, not workarounds.
5. **Why Comments**: Explain intent ("why"), not mechanics ("what").
6. **User-Friendly**: Minimize jargon, use simple terms.

### 🚨 CRITICAL: 100% LLM-Based Decision Making (Rule 7)

**STRICTLY PROHIBITED**: Keyword parsing or pattern matching for user intent/agent selection.

❌ **WRONG**:
```python
if "파일" in request or "file" in request.lower():
    select FileAgent
```

✅ **CORRECT**: Let PlannerAgent's LLM naturally analyze requests and delegate via CrewAI hierarchical process.

**Rationale**: Keyword parsing is fragile, non-extensible, contradicts LLM-based architecture. CrewAI delegation provides superior flexibility.

## Architecture

### Execution Flow
1. `main.py` → Interface (CLI/Discord) → `AngminiCrew.kickoff()`
2. `TaskFactory` creates Task objects from user input
3. CrewAI Hierarchical Process: PlannerAgent (Manager) delegates to workers
4. Workers (File/Notion/Memory/AppleApps) use specialized MCP tools
5. Results aggregated, execution context saved to memory

### Agents & Tools
- **PlannerAgent**: Manager, delegates via LLM
- **FileAgent**: FileTool (file I/O, search)
- **NotionAgent**: NotionTool (task/project CRUD)
- **MemoryAgent**: MemoryTool (vector search via SQLite+FAISS+Qwen3)
- **AppleAppsAgent**: AppleTool (macOS apps via Apple MCP subprocess)

MCP tools (`mcp/tools/`) inherit `ToolBlueprint`, adapted to CrewAI `BaseTool` via `mcp/crewai_adapters/`.

### Memory System
- **Storage**: `ai/memory/storage/` (SQLite metadata + FAISS vectors + Qwen3 embeddings)
- **Capture**: `ExecutionContext` → `MemoryCurator` (LLM summary) → `Deduplicator` → Storage
- **Retrieval**: `MemoryRepository.search()` (embedding similarity) or `CascadedRetriever` (iterative LLM-filtered)

### Interfaces
- **CLI** (`interface/cli.py`): Interactive REPL, streams output
- **Discord** (`interface/discord_bot.py`): Async message handler
- Switch via `DEFAULT_INTERFACE` in `.env`

## Key Files

**Core**
- `ai/core/`: config.py (env loader), logger.py (timestamped logs), exceptions.py (custom errors)

**CrewAI System**
- `crew/crew_config.py`: AngminiCrew orchestrator
- `crew/task_factory.py`: User input → Task objects
- `agents/`: AgentFactory, base_agent.py, planner/file/notion/memory/apple_apps agents

**MCP Tools**
- `mcp/tools/`: ToolBlueprint implementations (file_tool, notion_tool, memory_tool, apple_tool)
- `mcp/crewai_adapters/`: MCP→CrewAI BaseTool wrappers

**Memory**
- `ai/memory/service.py`: High-level API (capture, search)
- `ai/memory/storage/`: SQLite/FAISS repository, vector_index, embeddings

**External**
- `external/apple-mcp/`: Git submodule (TypeScript MCP for macOS apps)

## Environment Variables (`.env`)

**Required**: `GEMINI_API_KEY`, `DEFAULT_INTERFACE` (cli/discord)
**Optional**: `GEMINI_MODEL` (default: gemini-2.5-pro), `DISCORD_BOT_TOKEN`, `NOTION_API_KEY`, `NOTION_TODO_DATABASE_ID`, `NOTION_PROJECT_DATABASE_ID`, `LOG_LEVEL` (INFO), `CREW_PROCESS_TYPE` (hierarchical/sequential), `CREW_MEMORY_ENABLED`

See `.env.example` for details.

## Development Guidelines

### Adding Agents
1. Subclass `BaseAngminiAgent` in `agents/`
2. Implement `role()`, `goal()`, `backstory()`, `tools()`
3. Create tool adapter in `mcp/crewai_adapters/` if needed
4. Register in `AgentFactory.create_all_agents()`

### Adding Tools
1. Subclass `ToolBlueprint` in `mcp/tools/`
2. Implement `tool_name()`, `schema()`, `__call__()` → `ToolResult`
3. Create CrewAI adapter in `mcp/crewai_adapters/`
4. Assign to agent via `tools()` method

### Modifying Agents
- Prompts in `role()`, `goal()`, `backstory()` methods
- `build_agent()` constructs CrewAI Agent with LLM config
- Test with both hierarchical and sequential modes

### Extending Memory
- Capture triggers in `crew_config.py:kickoff()`
- Customize `_should_capture_memory()` in `MemoryService`
- Retention policy in `ai/memory/retention_policy.py`

## MCP Tools - ALWAYS USE WHEN APPLICABLE

### Available Tools
- **brave-search**: Real-time web search, news, images - USE for current info, research
- **playwright**: Browser automation, screenshots, web scraping - USE for UI testing, web interaction
- **context7**: Up-to-date library documentation - USE before implementing any library code
- **sequential-thinking**: Break complex tasks into steps - USE for multi-step workflows
- **memory**: Persistent context storage - USE to remember project decisions
- **codex**: Advanced code analysis - USE for refactoring, optimization
- **chrome-devtools**: Live browser debugging - USE for frontend issues

### Tool Usage Rules
- ALWAYS check context7 before writing library code
- ALWAYS use brave-search for latest API docs, package versions, best practices
- ALWAYS use playwright for visual regression testing
- ALWAYS use sequential-thinking for tasks with 3+ steps
- Prefer MCP tools over manual bash scripts when available

### Examples
- "Check context7 for latest Next.js 15 patterns before implementing"
- "Use playwright to screenshot the UI and compare with design"
- "Search brave-search for current TypeScript best practices"

### Code Review with Codex

**Dual-AI Review Workflow**: Two AI perspectives for enhanced quality and security.

#### Process

1. **Claude Code Implementation**
   - Write code, tests, documentation
   - Follow project patterns and conventions
   - *Why*: Initial implementation with project context

2. **Codex MCP Auto-Review**
   - Run: `/review-with-codex [files]` or `/codex review`
   - Codex analyzes from different AI perspective
   - *Why*: Catch issues Claude missed (security, edge cases, performance)

3. **Incorporate Feedback**
   - Review Codex suggestions systematically
   - Apply improvements for security/performance/best practices
   - Re-run tests to verify changes
   - *Why*: Multi-perspective analysis reduces bugs and technical debt

4. **Final Approval & Commit**
   - Get Codex sign-off: `/codex approve`
   - Commit message includes: `Reviewed by Codex`
   - *Why*: Quality assurance audit trail

#### Triggers

**Required**:
- Modified ≥2 files OR ≥50 lines
- New functions/classes/modules
- Security/API/interface changes

**Skip**: Trivial changes (typos, formatting, docs only)

**Quality Gates**: Tests pass → Codex review → Suggestions addressed → Codex approval → Commit

## Common Issues

1. **OpenMP Conflicts**: `KMP_DUPLICATE_LIB_OK=TRUE` set in `memory/factory.py` for PyTorch+FAISS
2. **Apple MCP**: Must initialize before use (handled in CLI/Discord init)
3. **CrewAI Output**: Rich console captured to prevent noise (`crew_config.py:kickoff`)
4. **Agent Tools**: Each agent only accesses tools in its `tools()` method

## Debugging

- **Logs**: `logs/YYYYMMDD_HHMMSS.log`, `memory_embedding.log`
- **Verbose**: `LOG_LEVEL=DEBUG` in `.env` (shows CrewAI output)
- **Trace**: Search logs for agent role/goal during delegation
- **Visual Output**: Comment out stdout/stderr capture in `crew_config.py`

## Resources

- **Roadmap**: `PLAN_for_AI_Agent.md`
- **Docs**: `docs/` (USAGE.md, CREWAI_MIGRATION_PLAN.md, memory_maintenance.md, APPLE_TOOL_GUIDE.md)

## Status

✅ Phases 1-4.5 complete (CrewAI multi-agent + tools + memory)
⏸️ Phase 5 planned (proactive notifications)
🚧 Testing coverage incomplete

**Legacy**: `interface/*_backup.py`, `ai/react_engine/` (ReAct engine preserved for reference, not actively used)
