"""Coordinates planning and execution of user goals via the ReAct pattern."""

from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from ai.ai_brain import AIBrain
from ai.core.exceptions import EngineError
from ai.core.logger import get_logger
from ai.memory.cascaded_retriever import CascadedRetrievalResult, CascadedRetriever
from mcp.tool_manager import ToolManager

from .agent_scratchpad import AgentScratchpad
from .conversation_memory import ConversationMemory
from .loop_detector import LoopDetection, LoopDetector
from .models import (
    ExecutionContext,
    FailureLogEntry,
    PlanStep,
    PlanStepStatus,
    PlanUpdatedEvent,
    PlanningDecision,
    StepCompletedEvent,
    StepOutcome,
    StepResult,
)
from .planning_engine import PlanningEngine
from .result_formatter import summarize_step_result
from .safety_guard import SafetyGuard
from .step_executor import StepExecutor

if TYPE_CHECKING:
    from ai.memory.memory_records import MemoryRecord
    from ai.memory.service import MemoryService


class GoalExecutor:
    """High-level orchestrator for planning and executing a user goal."""

    READ_ONLY_OPERATIONS: Dict[str, Tuple[str, ...]] = {
        "notion": (
            "list_tasks",
            "list_projects",
            "find_project",
            "list_todo",
            "list_todos",
            "todo_list",
        ),
    }
    STATE_CHANGING_OPERATIONS: Dict[str, Tuple[str, ...]] = {
        "notion": (
            "create_task",
            "create_todo",
            "todo_create",
            "update_task",
            "update_todo",
            "todo_update",
        ),
    }
    MAX_AUTO_FOLLOW_UP_REPLANS = 3

    def __init__(
        self,
        brain: AIBrain,
        tool_manager: ToolManager,
        step_executor: StepExecutor,
        safety_guard: SafetyGuard,
        scratchpad: AgentScratchpad,
        *,
        loop_detector: LoopDetector | None = None,
        planning_engine: PlanningEngine | None = None,
        template_dir: Optional[Path] = None,
        conversation_memory: ConversationMemory | None = None,
        memory_service: "MemoryService | None" = None,
    ) -> None:
        self._brain = brain
        self._tool_manager = tool_manager
        self._step_executor = step_executor
        self._safety_guard = safety_guard
        self._scratchpad = scratchpad
        self._loop_detector = loop_detector or LoopDetector()
        self._planning_engine = planning_engine or PlanningEngine(safety_guard)
        self._logger = get_logger(self.__class__.__name__)
        self._conversation_memory = conversation_memory or ConversationMemory()
        self._memory_service = memory_service
        self._cascaded_retriever: CascadedRetriever | None = None

        base_dir = template_dir or Path(__file__).resolve().parent / "prompt_templates"
        self._system_prompt = (base_dir / "system_prompt.md").read_text(encoding="utf-8")
        self._react_prompt_template = (base_dir / "react_prompt.md").read_text(encoding="utf-8")
        examples_path = base_dir / "planning_examples.md"
        self._planning_examples = examples_path.read_text(encoding="utf-8") if examples_path.exists() else ""

    def run(self, goal: str) -> ExecutionContext:
        self._logger.info("[PLANNING] User request: %s", goal)
        context = ExecutionContext(goal=goal)
        self._scratchpad.clear()
        self._scratchpad.add(f"goal established: {goal}")
        self._prefetch_relevant_memories(context, goal)
        self._update_plan(context, reason="initial plan required")

        while context.remaining_steps():
            step = self._pick_next_step(context)
            if step is None:
                break

            self._safety_guard.check()
            step.mark_in_progress()
            context.note_step_started(step.id)
            attempt = context.increment_attempt(step.id)
            self._scratchpad.add(f"executing step #{step.id}: {step.description}")

            self._safety_guard.note_step()
            result = self._step_executor.execute(step, context, attempt)
            self._handle_step_result(context, step, result)

        final_message = self._extract_direct_message(context)
        if not final_message:
            final_message = self._step_executor.compose_final_message(context)
        if final_message:
            clean_message = final_message.strip()
            decorated = self._decorate_final_message(context, clean_message)
            context.metadata["final_message"] = decorated

        self._capture_memory(context, goal)

        return context

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_plan(self, context: ExecutionContext, reason: Optional[str] = None) -> None:
        available_tools = self._tool_manager.list()
        prompt = self._build_plan_prompt(context.goal, available_tools, context, reason)
        if os.getenv("LOG_PROMPTS") == "true":
            self._logger.debug("Plan prompt generated:\n%s", prompt)
        else:
            self._logger.debug("[PLANNING] Prompt generated (length=%d chars)", len(prompt))
        llm_response = self._brain.generate_text(prompt)
        context.record_token_usage(llm_response.metadata, category="thinking")
        if os.getenv("LOG_PROMPTS") == "true":
            self._logger.debug("Plan response raw: %s", llm_response.text)
        else:
            self._logger.debug("[PLANNING] Response received (length=%d chars)", len(llm_response.text))
        steps = self._parse_plan_response(llm_response.text)
        if not steps:
            raise EngineError("LLM이 빈 계획을 반환했습니다.")

        # Log plan summary
        self._log_plan_summary(steps)

        context.plan_steps = steps
        context.attempt_counts.clear()
        context.step_started_at.clear()
        context.current_step_index = 0
        context.step_outcomes.clear()
        context.record_event(PlanUpdatedEvent(plan_steps=steps, reason=reason))
        self._scratchpad.add("plan updated:\n" + context.as_plan_checklist())

    def _build_plan_prompt(
        self,
        goal: str,
        tools: Dict[str, Dict[str, object]],
        context: ExecutionContext,
        reason: Optional[str],
    ) -> str:
        tool_lines = []
        for name, info in tools.items():
            description = info.get("description", "") or "(설명 없음)"
            params = info.get("parameters") or {}
            lines = [f"- {name}: {description}"]
            if isinstance(params, dict) and params:
                lines.append("  사용 가능한 매개변수:")
                for param_name, spec in params.items():
                    if not isinstance(spec, dict):
                        spec = {}
                    type_hint = spec.get("type")
                    enum_hint = spec.get("enum")
                    details = []
                    if isinstance(type_hint, str):
                        details.append(f"type={type_hint}")
                    if isinstance(enum_hint, list) and enum_hint:
                        enum_text = "/".join(str(value) for value in enum_hint)
                        details.append(f"options={enum_text}")
                    detail_suffix = f" ({', '.join(details)})" if details else ""
                    description_hint = spec.get("description") or ""
                    lines.append(
                        f"    - {param_name}{detail_suffix}: {description_hint}".rstrip()
                    )
                example = self._format_tool_example(name, params)
                if example:
                    lines.append(f"  예시 호출: {example}")
            tool_lines.append("\n".join(lines))
        tools_block = "\n".join(tool_lines) if tool_lines else "(등록된 도구 없음)"

        memory_block = self._conversation_memory.formatted(limit=10)
        memory_notes_list = context.metadata.get("memory_search_notes")
        if isinstance(memory_notes_list, list) and memory_notes_list:
            memory_insights = "\n".join(str(note) for note in memory_notes_list[-3:])
        else:
            memory_insights = "(최근 메모리 검색 없음)"
        # Format all observations with structured data to help LLM use concrete IDs
        all_observations = self._format_all_observations(context)

        # Add actionability hint if we have enough data
        observations_count = sum(
            1 for event in context.events
            if isinstance(event, StepCompletedEvent) and event.data
        )

        if observations_count >= 2:
            actionability_hint = (
                f"\n{'='*80}\n"
                f"🚨 CRITICAL INSTRUCTION - READ CAREFULLY 🚨\n"
                f"{'='*80}\n"
                f"당신은 이미 {observations_count}개의 관찰 데이터를 수집했습니다.\n"
                f"더 이상 조회 작업을 생성하지 마세요!\n\n"
                f"✅ 반드시 해야 할 일:\n"
                f"  1. '완료된 단계의 관찰 데이터' 섹션을 확인하세요\n"
                f"  2. Tasks 섹션과 Projects 섹션에서 ID를 추출하세요\n"
                f"  3. 작업 제목과 프로젝트 제목을 매칭하세요 (키워드 기반)\n"
                f"  4. update_task 작업을 생성하세요 (구체적인 page_id와 relations 사용)\n\n"
                f"❌ 절대 하지 말아야 할 일:\n"
                f"  - list_tasks, list_projects 같은 조회 작업 생성 금지\n"
                f"  - 플레이스홀더(<...>, {{...}}) 사용 금지\n"
                f"  - '정보가 부족하다'는 평가 금지 (이미 충분한 데이터가 있음)\n"
                f"{'='*80}\n\n"
            )
        else:
            actionability_hint = ""

        # Attach request timestamp (Asia/Seoul) to guide due_date calculations
        now_seoul = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%dT%H:%M:%S")
        if memory_block and "(최근 대화 기록 없음)" not in memory_block:
            self._logger.debug("[PLANNING] Conversation memory: %d chars", len(memory_block))
        reason_block = f"이전에 실패한 이유: {reason}\n" if reason else ""
        return (
            f"{self._system_prompt}\n\n"
            f"사용자 목표: {goal}\n"
            f"요청 수신 시각(Asia/Seoul): {now_seoul}\n"
            f"사용 가능한 도구 목록:\n{tools_block}\n\n"
            f"최근 대화 기록:\n{memory_block}\n\n"
            f"최근 메모리 검색 요약:\n{memory_insights}\n\n"
            f"현재 계획 체크리스트:\n{context.as_plan_checklist() or '(계획 없음)'}\n\n"
            f"최근 실패 로그:\n{context.fail_log_summary()}\n\n"
            f"완료된 단계의 관찰 데이터:\n{all_observations}\n\n"
            f"{actionability_hint}"
            + (f"## Planning Examples\n{self._planning_examples}\n\n" if self._planning_examples else "")
            + "다음 단계 계획을 생성하세요:\n"
            "- 위 관찰 데이터에서 구체적인 ID/UUID를 사용하세요\n"
            "- 플레이스홀더(<...>, {{...}})는 절대 사용하지 마세요\n"
            "- 정보가 부족하면 조회를 위한 단일 단계만 생성하세요\n\n"
            f"{reason_block}"
            "JSON 배열 형식의 새로운 계획을 생성하세요.\n"
            "각 항목은 {\"id\": number, \"description\": string, \"tool\": string | null, \"parameters\": object, \"status\": string} 구조여야 합니다.\n"
            "status는 todo/in_progress/done 중 하나입니다."
        )

    def _parse_plan_response(self, response: str) -> List[PlanStep]:
        cleaned = response.strip()
        if "```" in cleaned:
            first_fence = cleaned.find("```")
            last_fence = cleaned.rfind("```")
            if first_fence != -1 and last_fence != -1 and first_fence != last_fence:
                fenced = cleaned[first_fence + 3 : last_fence].strip()
                if fenced.startswith("json"):
                    fenced = fenced[4:].lstrip()
                cleaned = fenced or cleaned

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines:
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        first_bracket_candidates = [idx for idx in (cleaned.find("["), cleaned.find("{")) if idx != -1]
        if first_bracket_candidates:
            first_bracket = min(first_bracket_candidates)
            if first_bracket > 0:
                cleaned = cleaned[first_bracket:]

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            self._logger.error("계획 응답 파싱 실패", extra={"response": response, "cleaned": cleaned})
            raise EngineError("계획 응답이 JSON 형식을 따르지 않습니다.") from exc

        if not isinstance(data, list):
            raise EngineError("계획 응답은 JSON 배열이어야 합니다.")

        steps: List[PlanStep] = []
        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise EngineError("계획 항목은 JSON 객체여야 합니다.")
            description = item.get("description")
            if not isinstance(description, str) or not description.strip():
                raise EngineError("각 계획 항목은 description 문자열을 가져야 합니다.")
            step_id = item.get("id")
            if not isinstance(step_id, int):
                step_id = index
            status_raw = (item.get("status") or "todo").lower()
            try:
                status = PlanStepStatus(status_raw)
            except ValueError:
                status = PlanStepStatus.TODO
            tool_name = item.get("tool")
            if tool_name is not None and not isinstance(tool_name, str):
                tool_name = None
            params = item.get("parameters") or {}
            if not isinstance(params, dict):
                params = {}
            action_value = params.get("action")
            if "operation" not in params and isinstance(action_value, str):
                params["operation"] = action_value
            params.pop("action", None)
            steps.append(
                PlanStep(
                    id=step_id,
                    description=description.strip(),
                    tool_name=tool_name.strip() if isinstance(tool_name, str) else None,
                    parameters=params,
                    status=status,
                )
            )
        return steps

    def _pick_next_step(self, context: ExecutionContext) -> Optional[PlanStep]:
        for idx, step in enumerate(context.plan_steps):
            if step.status != PlanStepStatus.DONE:
                context.current_step_index = idx
                return step
        context.current_step_index = None
        return None

    def _handle_step_result(self, context: ExecutionContext, step: PlanStep, result: StepResult) -> None:
        if result.outcome == StepOutcome.SUCCESS:
            self._record_step_execution(context, step)
            step.mark_done()
            context.reset_attempt(step.id)
            context.record_event(
                StepCompletedEvent(step_id=step.id, outcome=result.outcome, data=result.data)
            )
            context.append_scratch(f"step #{step.id} 완료")
            self._handle_memory_tool_success(context, step, result)

            summary = summarize_step_result(step, result.data)
            context.record_step_outcome(step.id, summary)

            # Log progress
            progress = context.calculate_progress()
            self._logger.info("[EXECUTION] Progress: %d%%", int(progress * 100))

            if self._should_request_follow_up_plan(context, step):
                auto_replans = int(context.metadata.get("auto_followup_replans", 0))
                if auto_replans >= self.MAX_AUTO_FOLLOW_UP_REPLANS:
                    raise EngineError(
                        "조회 단계만 반복되어 목표를 달성하지 못했습니다. 새 요청 또는 추가 정보가 필요합니다."
                    )
                context.metadata["auto_followup_replans"] = auto_replans + 1
                context.append_scratch("triggering follow-up plan after read-only step")

                # Build more explicit reason based on what we have
                observations_with_data = sum(
                    1 for event in context.events
                    if isinstance(event, StepCompletedEvent) and event.data
                )

                reason = (
                    f"⚠️ 중요: 이미 {observations_with_data}개의 관찰 데이터를 수집했습니다.\n"
                    f"더 이상 조회 작업(list_tasks, list_projects)을 생성하지 마세요.\n"
                    f"반드시 write 작업(update_task, create_task)을 포함한 계획을 생성하세요.\n"
                    f"관찰 데이터에 있는 정확한 ID를 사용하여 매칭 작업을 수행하세요."
                )
                self._update_plan(context, reason=reason)
            return

        failure_entry = FailureLogEntry(
            step_id=step.id,
            command=json.dumps({"tool": step.tool_name, "parameters": step.parameters}, ensure_ascii=False),
            error_message=result.error_reason or "알 수 없는 오류",
            attempt=result.attempt,
        )
        context.add_failure(failure_entry)
        context.append_scratch(f"step #{step.id} 실패: {failure_entry.error_message}")

        loop_detection: LoopDetection | None = self._loop_detector.evaluate(context, step, result)
        decision: PlanningDecision = self._planning_engine.evaluate(
            context,
            step,
            result,
            loop_detection.reason if loop_detection else None,
        )

        if decision.action == "retry":
            step.status = PlanStepStatus.TODO
            self._logger.info("[EXECUTION] Retry: %s", decision.reason)
            return

        if decision.action == "replan":
            # ✅ NEW: Track replans per step
            step_replans = context.metadata.get(f"replans_step_{step.id}", 0)
            if step_replans >= 2:
                # After 2 replans for same step, escalate to user
                raise EngineError(
                    f"❌ Step {step.id} failed after {step_replans} replan attempts.\n"
                    f"🤔 I need your help:\n"
                    f"- Step goal: {step.description}\n"
                    f"- Last error: {result.error_reason}\n"
                    f"- Available data: {self._format_all_observations(context)}\n\n"
                    f"💡 Please provide missing information or rephrase your request."
                )

            context.metadata[f"replans_step_{step.id}"] = step_replans + 1
            self._logger.warning("[PLANNING] Replan triggered: %s", decision.reason)
            self._update_plan(context, reason=decision.reason)
            return

        raise EngineError(
            decision.reason or f"Step {step.id}에서 복구 불가능한 오류가 발생했습니다."
        )

    def _decorate_final_message(self, context: ExecutionContext, message: str) -> str:
        token_usage = context.metadata.get("token_usage", {})
        total_tokens = token_usage.get("total_tokens")
        if total_tokens is None:
            total_tokens = context.thinking_tokens + context.response_tokens
        thinking_tokens = token_usage.get("thinking_tokens", context.thinking_tokens)
        response_tokens = token_usage.get("response_tokens", context.response_tokens)

        token_usage.update(
            {
                "total_tokens": total_tokens,
                "thinking_tokens": thinking_tokens,
                "response_tokens": response_tokens,
            }
        )
        context.metadata["token_usage"] = token_usage
        return (
            f"{message} [tokens_total={total_tokens}, "
            f"thinking_tokens={thinking_tokens}, response_tokens={response_tokens}]"
        )

    def _extract_direct_message(self, context: ExecutionContext) -> str | None:
        for event in reversed(context.events):
            if isinstance(event, StepCompletedEvent):
                data = getattr(event, "data", None)
                if isinstance(data, dict) and data.get("type") == "direct_response":
                    message = data.get("message")
                    if isinstance(message, str) and message.strip():
                        return message.strip()
        return None

    def _handle_memory_tool_success(
        self,
        context: ExecutionContext,
        step: PlanStep,
        result: StepResult,
    ) -> None:
        if step.tool_name != "memory":
            return
        data = result.data
        if not isinstance(data, dict):
            return
        summary = self._summarise_memory_search(data)
        if summary:
            context.append_scratch(f"memory search insight: {summary}")
            notes_obj = context.metadata.setdefault("memory_search_notes", [])
            if not isinstance(notes_obj, list):
                notes_obj = []
                context.metadata["memory_search_notes"] = notes_obj
            notes_obj.append(summary)
        history_obj = context.metadata.setdefault("memory_search_results", [])
        if not isinstance(history_obj, list):
            history_obj = []
            context.metadata["memory_search_results"] = history_obj
        history_obj.append(data)

    def _record_step_execution(self, context: ExecutionContext, step: PlanStep) -> None:
        history = context.metadata.setdefault("executed_operations", [])
        if not isinstance(history, list):
            history = []
            context.metadata["executed_operations"] = history
        history.append(
            {
                "tool": step.tool_name,
                "operation": self._extract_operation_name(step),
            }
        )

    def _should_request_follow_up_plan(self, context: ExecutionContext, step: PlanStep) -> bool:
        if context.remaining_steps():
            return False
        if not self._is_read_only_step(step):
            return False

        history = context.metadata.get("executed_operations")
        if isinstance(history, list):
            for entry in history:
                if self._is_state_changing_entry(entry):
                    return False

        # Check if we already have enough observations for write operations
        observations_with_data = sum(
            1 for event in context.events
            if isinstance(event, StepCompletedEvent) and event.data
        )

        # If we have 2+ observations (e.g., tasks + projects), we should act!
        if observations_with_data >= 2:
            self._logger.warning(
                "[PLANNING] Read-only step completed. Have %d observation(s) - next plan MUST include write operations",
                observations_with_data
            )

        self._logger.info(
            "[PLANNING] Requesting follow-up plan: current plan only had read-only operations"
        )

        return True

    def _extract_operation_name(self, step: PlanStep) -> Optional[str]:
        if not step.parameters:
            return None
        operation = step.parameters.get("operation")
        if isinstance(operation, str):
            normalized = operation.strip().lower()
            return normalized or None
        return None

    def _is_read_only_step(self, step: PlanStep) -> bool:
        operation = self._extract_operation_name(step)
        if not operation or not step.tool_name:
            return False
        tool_operations = self.READ_ONLY_OPERATIONS.get(step.tool_name.lower())
        if not tool_operations:
            return False
        return operation in tool_operations

    def _is_state_changing_entry(self, entry: Any) -> bool:
        if not isinstance(entry, dict):
            return False
        tool = entry.get("tool")
        operation = entry.get("operation")
        if not isinstance(tool, str) or not isinstance(operation, str):
            return False
        operations = self.STATE_CHANGING_OPERATIONS.get(tool.lower())
        if not operations:
            return False
        return operation in operations

    def _summarise_memory_search(self, data: Dict[str, Any]) -> str:
        matches = data.get("matches")
        if isinstance(matches, list) and matches:
            highlights: List[str] = []
            for entry in matches[:3]:
                if not isinstance(entry, dict):
                    continue
                summary = entry.get("summary")
                score = entry.get("score")
                if not isinstance(summary, str) or not summary.strip():
                    continue
                lowered = summary.lower()
                is_positive = (
                    any(keyword in lowered for keyword in ("좋아", "선호", "기억", "like", "prefer"))
                    and "기억하지" not in lowered
                    and "모르" not in lowered
                    and "알지 못" not in lowered
                )
                label = "preference" if is_positive else "memory"
                if isinstance(score, (int, float)):
                    highlights.append(f"{label}: {summary.strip()} (score={score:.2f})")
                else:
                    highlights.append(f"{label}: {summary.strip()}")
            if highlights:
                return " | ".join(highlights)
        if any(key in data for key in ("tool_usage", "tags")):
            return "usage patterns analysed"
        return ""

    def _prefetch_relevant_memories(self, context: ExecutionContext, user_request: str) -> None:
        if not self._memory_service:
            return

        repository = getattr(self._memory_service, "repository", None)
        if repository is None:
            return

        # Allow duplicated OpenMP runtimes (macOS often loads both PyTorch and FAISS).
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

        cascaded_result: CascadedRetrievalResult | None = None
        matches: Sequence[Tuple["MemoryRecord", float]] = []

        try:
            cascaded_result = self._ensure_cascaded_retriever(repository).retrieve(user_request)
            matches = [(match.record, match.score) for match in cascaded_result.matches]
        except Exception as exc:  # pragma: no cover - runtime safeguard
            self._logger.warning("Cascaded retrieval failed, falling back to single search: %s", exc)

        if not matches:
            try:
                matches = repository.search(user_request, top_k=3)
            except Exception as exc:  # pragma: no cover - runtime safeguard
                self._logger.warning("Memory prefetch fallback failed: %s", exc)
                return

        if not matches:
            return

        reranked_matches = self._rerank_memory_matches(matches)

        serialised_matches: List[Dict[str, Any]] = []
        for record, score in reranked_matches:
            payload: Dict[str, Any] = {
                "summary": record.summary,
                "goal": record.goal,
                "user_intent": record.user_intent,
                "outcome": record.outcome,
                "category": record.category.value,
                "tools_used": list(record.tools_used),
                "tags": list(record.tags),
                "score": float(score),
                "created_at": record.created_at.isoformat()
                if hasattr(record.created_at, "isoformat")
                else record.created_at,
            }
            serialised_matches.append(payload)

        data: Dict[str, Any] = {"matches": serialised_matches}
        if cascaded_result is not None:
            data["metrics"] = [
                {
                    "query": item.query,
                    "depth": item.depth,
                    "total_candidates": item.total_candidates,
                    "kept": item.kept,
                    "follow_up_queries": item.follow_up_queries,
                    "duration_ms": round(item.duration_ms, 2),
                }
                for item in cascaded_result.iterations
            ]
        summary = self._summarise_memory_search(data)
        if summary:
            context.append_scratch(f"memory search insight: {summary}")
            notes_obj = context.metadata.setdefault("memory_search_notes", [])
            if isinstance(notes_obj, list):
                notes_obj.append(summary)
            else:
                context.metadata["memory_search_notes"] = [summary]

        history_obj = context.metadata.setdefault("memory_search_results", [])
        if isinstance(history_obj, list):
            history_obj.append(data)
        else:
            context.metadata["memory_search_results"] = [data]

        if cascaded_result is not None:
            metrics_history = context.metadata.setdefault("memory_search_metrics", [])
            if isinstance(metrics_history, list):
                metrics_history.append(data.get("metrics"))

    def _rerank_memory_matches(
        self,
        matches: Sequence[Tuple["MemoryRecord", float]],
    ) -> List[Tuple["MemoryRecord", float]]:
        def preference_bias(record: "MemoryRecord") -> float:
            text = " ".join(
                filter(
                    None,
                    [record.summary, record.user_intent, record.outcome],
                )
            ).lower()
            tags = {tag.lower() for tag in record.tags}
            bias = 0.0

            if any(keyword in text for keyword in ("좋아", "선호", "favorite", "prefer")):
                bias += 0.45
            if "기억" in text and "기억하지" not in text:
                bias += 0.25
            if any(tag in tags for tag in ("선호 표현", "선호도", "공감", "기억")):
                bias += 0.35
            if any(tag in tags for tag in ("ai 한계", "정보 부족")):
                bias -= 0.4
            if "기억하지" in text or "모르" in text or "알지 못" in text:
                bias -= 0.5
            return bias

        scored: List[Tuple["MemoryRecord", float]] = []
        for record, base_score in matches:
            scored.append((record, base_score + preference_bias(record)))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored

    def _ensure_cascaded_retriever(self, repository) -> CascadedRetriever:
        if self._cascaded_retriever is None:
            self._cascaded_retriever = CascadedRetriever(
                brain=self._brain,
                repository=repository,
            )
        return self._cascaded_retriever

    def _capture_memory(self, context: ExecutionContext, user_request: str) -> None:
        if not self._memory_service:
            return

        if not self._should_capture_memory(context, user_request):
            self._logger.debug("Skipping memory capture for lightweight exchange")
            return

        try:
            capture = self._memory_service.capture(context, user_request)
            capture_info: Dict[str, Any] = {
                "should_store": capture.should_store,
                "reason": capture.reason,
                "stored": capture.stored,
            }
            if capture.duplicate_id:
                capture_info["duplicate_of"] = capture.duplicate_id
            if capture.record_id:
                capture_info["record_id"] = capture.record_id
            if capture.category:
                capture_info["category"] = capture.category
            if capture.stored and capture.record:
                context.append_scratch(f"memory stored: {capture.record.summary}")
            context.metadata["memory_capture"] = capture_info
        except EngineError as exc:
            self._logger.warning("Memory capture failed: %s", exc)
        except Exception as exc:  # pragma: no cover - defensive guard
            self._logger.warning("Unexpected memory capture failure: %s", exc, exc_info=True)

    def _should_capture_memory(self, context: ExecutionContext, user_request: str) -> bool:
        operations = context.metadata.get("executed_operations")
        if isinstance(operations, list):
            for entry in operations:
                if not isinstance(entry, dict):
                    continue
                tool = entry.get("tool")
                operation = entry.get("operation")
                if isinstance(tool, str) and tool.strip() and isinstance(operation, str) and operation.strip():
                    return True

        if self._contains_personal_signal(user_request, context):
            return True

        request_size = len((user_request or "").strip())
        token_usage = context.metadata.get("token_usage", {})
        response_tokens = token_usage.get("response_tokens", context.response_tokens)
        thinking_tokens = token_usage.get("thinking_tokens", context.thinking_tokens)

        if request_size <= 8 and response_tokens <= 16 and thinking_tokens <= 128:
            return False
        return True

    def _contains_personal_signal(self, user_request: str, context: ExecutionContext) -> bool:
        text = (user_request or "").lower()
        if not text:
            return False

        keywords = (
            "내 ",
            "나의",
            "내가",
            "좋아하는",
            "싫어하는",
            "선호",
            "취향",
            "기억해",
            "기억해줘",
            "생일",
            "birthday",
            "phone",
            "전화번호",
            "email",
            "이메일",
            "주소",
            "address",
            "취미",
        )
        if any(keyword in text for keyword in keywords):
            return True

        response_text = "".join(context.metadata.get("final_message", "")).lower()
        if response_text and any(keyword in response_text for keyword in keywords):
            return True

        return False

    # Future: integrate thinking loop with react prompt
    def render_react_prompt(self, context: ExecutionContext) -> str:
        checklist = context.as_plan_checklist()
        current = context.current_step()
        current_text = current.to_prompt_fragment() if current else "(no active step)"
        return (
            self._react_prompt_template
            .replace("{{goal}}", context.goal)
            .replace("{{plan_checklist}}", checklist or "(empty)")
            .replace("{{fail_log}}", context.fail_log_summary())
            .replace("{{current_step}}", current_text)
            .replace("{{scratchpad}}", self._scratchpad.dump(limit=10) or "(empty)")
        )

    def _format_tool_example(self, name: str, params: Mapping[str, Any]) -> str:
        sample: Dict[str, Any] = {}
        for param_name, spec in params.items():
            value: Any
            if isinstance(spec, dict):
                enum_hint = spec.get("enum")
                type_hint = spec.get("type")
                if isinstance(enum_hint, list) and enum_hint:
                    value = enum_hint[0]
                elif type_hint == "boolean":
                    value = False
                elif type_hint == "integer":
                    value = 0
                elif type_hint == "number":
                    value = 0
                elif param_name == "path":
                    value = "~/Desktop"
                else:
                    value = f"<{param_name}>"
            else:
                value = f"<{param_name}>"
            sample[param_name] = value

        if not sample:
            return ""

        example = {"tool": name, "parameters": sample}
        try:
            return json.dumps(example, ensure_ascii=False)
        except TypeError:
            return ""

    def _format_all_observations(self, context: ExecutionContext) -> str:
        """Format all completed steps with their structured data."""
        if not context.events:
            return "(No observations yet)"

        # Group observations by tool for better context
        tasks_obs = []
        projects_obs = []
        other_obs = []

        for event in context.events:
            if not isinstance(event, StepCompletedEvent):
                continue

            step = next((s for s in context.plan_steps if s.id == event.step_id), None)
            if not step:
                continue

            data_str = self._format_observation_data(event.data)
            obs_text = (
                f"Step {event.step_id} ({step.tool_name}): {step.description}\n"
                f"Result:\n{data_str}"
            )

            # Categorize by tool and operation
            if step.tool_name == "notion" and event.data:
                operation = step.parameters.get("operation", "")
                if "task" in operation:
                    tasks_obs.append(obs_text)
                elif "project" in operation:
                    projects_obs.append(obs_text)
                else:
                    other_obs.append(obs_text)
            else:
                other_obs.append(obs_text)

        # Organize output for easier LLM parsing
        sections = []
        if tasks_obs:
            sections.append("### Tasks\n" + "\n\n".join(tasks_obs))
        if projects_obs:
            sections.append("### Projects\n" + "\n\n".join(projects_obs))
        if other_obs:
            sections.append("### Other\n" + "\n\n".join(other_obs))

        # Add matching hint if we have both tasks and projects
        if tasks_obs and projects_obs:
            sections.append(
                "### 💡 Next Step Hint\n"
                "당신은 Tasks와 Projects 데이터를 모두 수집했습니다.\n"
                "이제 update_task를 사용하여 작업을 프로젝트에 연결하세요:\n"
                "1. Tasks의 제목에서 키워드를 추출하세요 (예: 'GPS개론 과제3' → 'GPS개론')\n"
                "2. Projects에서 해당 키워드를 포함하는 프로젝트를 찾으세요\n"
                "3. Tasks의 ID (page_id)와 Projects의 ID (relations)를 사용하여 update_task 계획을 생성하세요\n"
                "4. 여러 작업이 있다면, 각각에 대해 별도의 update_task step을 생성하세요"
            )

        return "\n\n".join(sections) if sections else "(No observations yet)"

    def _format_observation_data(self, data: Any) -> str:
        """Format observation data to expose IDs and structured info."""
        if not data:
            return "(empty)"

        if isinstance(data, dict):
            # Check both "items" (Notion) and "results" (generic)
            items_key = "items" if "items" in data else ("results" if "results" in data else None)

            if items_key:
                items = data[items_key][:10]  # Show first 10 (increased from 5)
                if not items:
                    return "(no items found)"

                formatted = []
                for idx, item in enumerate(items, 1):
                    title = item.get("title", "Untitled")
                    page_id = item.get("id", "no-id")

                    # Include relations if present
                    relations = item.get("relations", [])
                    rel_str = f", Relations: {relations}" if relations else ""

                    formatted.append(f"{idx}. {title}\n   ID: {page_id}{rel_str}")

                # Add summary
                total_count = len(data[items_key])
                summary_line = f"\nTotal: {total_count} items"
                return "\n".join(formatted) + summary_line

            # For single operations, show key fields
            if "id" in data:
                return f"ID: {data['id']}, URL: {data.get('url', 'N/A')}"

        return str(data)[:500]  # Truncate long responses

    def _log_plan_summary(self, steps: list[PlanStep]) -> None:
        """Log a concise summary of the generated plan."""
        if os.getenv("LOG_PLAN_DETAILS") == "true":
            self._logger.info("[PLANNING] Generated %d step(s):", len(steps))
            for step in steps:
                if step.tool_name:
                    operation = step.parameters.get("operation", "")
                    tool_desc = f"{step.tool_name}.{operation}" if operation else step.tool_name
                else:
                    tool_desc = "dialogue"
                # Truncate description to 60 chars
                desc_short = step.description[:60] + "..." if len(step.description) > 60 else step.description
                self._logger.info("  - Step %d: %s [%s]", step.id, desc_short, tool_desc)
        else:
            # Standard mode: show tool + brief description
            self._logger.info("[PLANNING] Generated %d step(s):", len(steps))
            for step in steps:
                if step.tool_name:
                    operation = step.parameters.get("operation", "")
                    tool_desc = f"{step.tool_name}.{operation}" if operation else step.tool_name
                else:
                    tool_desc = "dialogue"
                # Truncate description to 50 chars for compact view
                desc_short = step.description[:50] + "..." if len(step.description) > 50 else step.description
                self._logger.info("  → Step %d [%s]: %s", step.id, tool_desc, desc_short)
