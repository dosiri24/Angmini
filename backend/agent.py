"""
LLM Agent 모듈 - Gemini 기반 ReAct 패턴 구현.

Why: 자연어 → 구조화된 데이터 변환은 100% LLM이 담당한다.
Tool은 ISO 형식의 구조화된 데이터만 처리한다. (CLAUDE.md 순수 LLM 원칙)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from collections import deque

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool, content_types

from config import config
from database import Database
from tools import TOOL_DEFINITIONS, execute_tool

# 로깅 설정
logger = logging.getLogger(__name__)


# ============================================================
# 대화 메모리 (Conversation Memory)
# ============================================================

@dataclass
class Message:
    """대화 메시지 단위."""
    role: str  # "user", "model", "function"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    function_call: Optional[dict] = None
    function_response: Optional[dict] = None


class ConversationMemory:
    """
    대화 히스토리를 관리하는 클래스.

    Why: LLM이 이전 대화 맥락을 참조하여 더 정확한 응답을 생성하도록 한다.
    최근 N턴만 유지하여 토큰 사용량을 제한한다.
    """

    def __init__(self, max_size: int = 10):
        """
        Args:
            max_size: 유지할 최대 대화 턴 수
        """
        self._messages: deque[Message] = deque(maxlen=max_size)
        self._max_size = max_size

    def add(self, role: str, content: str, **kwargs) -> None:
        """
        메시지를 추가한다.

        Args:
            role: 역할 ("user", "model", "function")
            content: 메시지 내용
            **kwargs: 추가 메타데이터 (function_call, function_response 등)
        """
        msg = Message(role=role, content=content, **kwargs)
        self._messages.append(msg)
        logger.debug(f"Memory add: [{role}] {content[:50]}...")

    def get_context(self) -> list[dict]:
        """
        Gemini API 형식의 대화 히스토리를 반환한다.

        Returns:
            [{"role": "user", "parts": ["..."]}] 형식의 리스트
        """
        context = []
        for msg in self._messages:
            context.append({
                "role": msg.role,
                "parts": [msg.content],
            })
        return context

    def get_messages(self) -> list[Message]:
        """모든 메시지를 리스트로 반환한다."""
        return list(self._messages)

    def clear(self) -> None:
        """모든 대화 히스토리를 삭제한다."""
        self._messages.clear()
        logger.debug("Memory cleared")

    def __len__(self) -> int:
        return len(self._messages)


# ============================================================
# 시스템 프롬프트 파일 경로
# ============================================================

# Why: 프롬프트를 별도 파일로 분리하여 코드 변경 없이 프롬프트 수정 가능
PROMPT_FILE_PATH = Path(__file__).parent / "prompt.md"


# ============================================================
# Gemini Tool 스키마 변환
# ============================================================

def build_gemini_tools() -> list[Tool]:
    """
    TOOL_DEFINITIONS를 Gemini Function Calling 형식으로 변환한다.

    Why: tools.py의 스키마 정의를 Gemini API가 이해하는 형식으로 변환.
    """
    function_declarations = []

    for name, definition in TOOL_DEFINITIONS.items():
        params_schema = definition.get("parameters", {})

        # properties와 required 추출
        properties_raw = params_schema.get("properties", {})
        required = params_schema.get("required", [])

        # Gemini 형식으로 변환
        properties = {}
        for param_name, param_info in properties_raw.items():
            prop = {
                "type": param_info["type"].upper(),
                "description": param_info["description"],
            }

            # enum 처리
            if "enum" in param_info:
                prop["enum"] = param_info["enum"]

            properties[param_name] = prop

        func_decl = FunctionDeclaration(
            name=name,
            description=definition["description"],
            parameters={
                "type": "OBJECT",
                "properties": properties,
                "required": required,
            } if properties else None,
        )
        function_declarations.append(func_decl)

    return [Tool(function_declarations=function_declarations)]


# ============================================================
# Agent 클래스
# ============================================================

class Agent:
    """
    ReAct 패턴 기반 LLM Agent.

    Why: 사용자의 자연어 입력을 이해하고, 필요한 도구를 호출하여
    결과를 자연어 응답으로 변환한다.
    """

    def __init__(
        self,
        memory: Optional[ConversationMemory] = None,
        db: Optional[Database] = None,
    ):
        """
        Args:
            memory: 대화 메모리 (없으면 새로 생성)
            db: 데이터베이스 (없으면 기본 경로로 생성)
        """
        cfg = config()

        # Gemini API 설정
        genai.configure(api_key=cfg.gemini_api_key)

        # 모델 초기화
        self._model = genai.GenerativeModel(
            model_name=cfg.gemini_flash_model,
            tools=build_gemini_tools(),
            system_instruction=self._build_system_prompt(),
        )

        # 대화 메모리 (None 체크 - 빈 메모리도 유효함)
        self._memory = memory if memory is not None else ConversationMemory(cfg.conversation_memory_size)

        # 데이터베이스
        if db is not None:
            self._db = db
        else:
            self._db = Database(cfg.database_path)
            self._db.init_schema()

        # ReAct 설정
        self._max_iterations = cfg.max_react_iterations

        logger.info(f"Agent initialized with model: {cfg.gemini_flash_model}")

    def _build_system_prompt(self) -> str:
        """
        현재 날짜/시간이 포함된 시스템 프롬프트를 생성한다.

        Why: prompt.md 파일에서 프롬프트를 읽어와서 동적으로 날짜/시간을 삽입.
        파일 분리로 코드 변경 없이 프롬프트 수정이 가능해짐.
        """
        now = datetime.now()

        try:
            prompt_template = PROMPT_FILE_PATH.read_text(encoding="utf-8")
            logger.debug(f"Loaded prompt from: {PROMPT_FILE_PATH}")
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {PROMPT_FILE_PATH}")
            raise RuntimeError(f"프롬프트 파일을 찾을 수 없습니다: {PROMPT_FILE_PATH}")
        except Exception as e:
            logger.error(f"Failed to read prompt file: {e}")
            raise RuntimeError(f"프롬프트 파일 읽기 실패: {e}")

        return prompt_template.format(
            today=now.strftime("%Y-%m-%d (%A)"),
            now=now.strftime("%H:%M"),
        )

    async def process_message(self, user_input: str) -> str:
        """
        사용자 메시지를 처리하고 응답을 반환한다.

        Why: ReAct 패턴으로 도구 호출 → 결과 확인 → 추가 호출/응답 생성을 반복.

        Args:
            user_input: 사용자 입력 메시지

        Returns:
            AI 응답 메시지
        """
        logger.info(f"Processing: {user_input[:50]}...")

        # 사용자 메시지 저장
        self._memory.add("user", user_input)

        # 대화 시작
        chat = self._model.start_chat(history=self._memory.get_context()[:-1])

        # ReAct 루프
        iteration = 0
        response = None

        while iteration < self._max_iterations:
            iteration += 1
            logger.debug(f"ReAct iteration {iteration}")

            # LLM 호출
            if response is None:
                # 첫 호출
                response = await chat.send_message_async(user_input)
            else:
                # 도구 결과 후 후속 호출
                response = await chat.send_message_async(tool_response_parts)

            # 응답 분석
            candidate = response.candidates[0]
            content = candidate.content

            # Function Call 확인
            function_calls = []
            text_parts = []

            for part in content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    function_calls.append(part.function_call)
                elif hasattr(part, "text") and part.text:
                    text_parts.append(part.text)

            # Function Call이 없으면 최종 응답
            if not function_calls:
                final_response = "".join(text_parts)
                self._memory.add("model", final_response)
                logger.info(f"Final response: {final_response[:50]}...")
                return final_response

            # Function Call 실행
            tool_response_parts = []

            for fc in function_calls:
                tool_name = fc.name
                tool_args = dict(fc.args) if fc.args else {}

                logger.info(f"Tool call: {tool_name}({tool_args})")

                # 도구 실행
                try:
                    result = execute_tool(self._db, tool_name, tool_args)
                except Exception as e:
                    logger.error(f"Tool error: {e}")
                    result = {"success": False, "error": str(e)}

                logger.info(f"Tool result: {result}")

                # Gemini에 전달할 형식으로 변환
                tool_response_parts.append(
                    content_types.to_part({
                        "function_response": {
                            "name": tool_name,
                            "response": result,
                        }
                    })
                )

        # 최대 반복 횟수 초과
        logger.warning(f"Max iterations ({self._max_iterations}) exceeded")
        return "죄송해요, 요청을 처리하는 데 문제가 발생했어요. 다시 시도해주세요. 😅"

    def clear_memory(self) -> None:
        """대화 메모리를 초기화한다."""
        self._memory.clear()
        logger.info("Memory cleared")

    @property
    def memory(self) -> ConversationMemory:
        """대화 메모리를 반환한다."""
        return self._memory
