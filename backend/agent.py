"""
LLM Agent 모듈 - Gemini 기반 ReAct 패턴 구현.

Why: 자연어 → 구조화된 데이터 변환은 100% LLM이 담당한다.
Tool은 ISO 형식의 구조화된 데이터만 처리한다. (CLAUDE.md 순수 LLM 원칙)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
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
# 시스템 프롬프트
# ============================================================

SYSTEM_PROMPT = """당신은 '앙미니(Angmini)'라는 이름의 AI 일정 관리 비서입니다.
사용자의 자연어 요청을 이해하고, 적절한 도구를 사용하여 일정을 관리합니다.

## 핵심 원칙
1. **자연어 → ISO 형식 변환**: 사용자가 "내일", "다음 주 월요일" 등으로 말하면,
   반드시 YYYY-MM-DD 형식으로 변환하여 도구를 호출하세요.
2. **시간 형식**: 시간은 HH:MM (24시간제)로 변환합니다. "오후 3시" → "15:00"
3. **도구 사용**: 일정 추가, 조회, 완료 처리 등은 반드시 제공된 도구를 사용하세요.
4. **친근한 응답**: 이모지를 적절히 사용하여 친근하게 응답하세요.

## 현재 날짜/시간
오늘은 {today}입니다. 현재 시각은 {now}입니다.

## 카테고리 (major_category)
일정 추가 시 다음 카테고리 중 하나를 **자동으로 추론**하세요:
- 학업: 수업, 과제, 스터디, 시험 등
- 약속: 친구, 가족과의 만남, 모임
- 개인: 운동, 취미, 개인 용무 등
- 업무: 회의, 미팅, 업무 관련
- 루틴: 반복적인 일과
- 기타: 위에 해당하지 않는 경우

**중요**: 사용자에게 카테고리를 묻지 말고, 내용을 보고 자동으로 추론하여 바로 도구를 호출하세요.
예: "친구 만남" → 약속, "팀 미팅" → 업무, "과제 제출" → 학업

## 도구 호출 원칙 (매우 중요!)
1. **즉시 실행**: 일정 관련 요청은 확인 없이 바로 도구를 호출하세요.
2. **질문형도 실행**: "추가해줄 수 있어?", "등록해줄래?" 같은 질문형 요청도 즉시 실행하세요.
3. **"할게요" 금지**: "추가해 드릴게요"라고만 답하지 말고, 실제로 도구를 호출하세요.
4. **말보다 행동**: 텍스트로 "했다"고 말하지 말고, 도구 호출로 실제로 실행하세요.

잘못된 예: "네, 추가해 드릴게요" (도구 미호출)
올바른 예: add_schedule 도구 호출 → "추가되었습니다!"

## 응답 형식
- 도구 호출 후 결과를 사용자에게 친근하게 전달하세요.
- 에러가 발생하면 사용자에게 알기 쉽게 설명하세요.

## 데스크톱 앱 연동 (중요!)
일정 **조회** 결과를 응답할 때는 반드시 아래 형식을 따르세요:
1. 먼저 친근한 자연어 설명을 제공
2. 그 다음 **반드시** `[SCHEDULE_DATA]...[/SCHEDULE_DATA]` 블록 안에 JSON 배열을 포함

예시:
```
오늘 일정이에요! 📅

1. 팀 미팅 (14:00~15:00) - 회의실 A
2. 운동 (18:00~19:00) - 헬스장

[SCHEDULE_DATA]
[{{"id":1,"title":"팀 미팅","date":"2025-11-26","start_time":"14:00","end_time":"15:00","location":"회의실 A","category":"업무","status":"대기"}},{{"id":2,"title":"운동","date":"2025-11-26","start_time":"18:00","end_time":"19:00","location":"헬스장","category":"개인","status":"대기"}}]
[/SCHEDULE_DATA]
```

**주의**: 일정 조회 시에만 SCHEDULE_DATA 블록을 포함하세요. 일정 추가/완료 응답에는 포함하지 마세요.
"""


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
        """현재 날짜/시간이 포함된 시스템 프롬프트를 생성한다."""
        now = datetime.now()
        return SYSTEM_PROMPT.format(
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
