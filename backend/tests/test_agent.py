"""
agent.py 테스트 모듈.

TDD: ConversationMemory 및 Agent 테스트
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from agent import (
    Message,
    ConversationMemory,
    build_gemini_tools,
    Agent,
    SYSTEM_PROMPT,
)


class TestMessage:
    """Message 데이터 클래스 테스트."""

    def test_message_creation(self):
        """Message 객체를 생성할 수 있다."""
        msg = Message(role="user", content="안녕하세요")

        assert msg.role == "user"
        assert msg.content == "안녕하세요"
        assert isinstance(msg.timestamp, datetime)

    def test_message_with_function_call(self):
        """function_call 메타데이터를 저장할 수 있다."""
        msg = Message(
            role="model",
            content="",
            function_call={"name": "add_schedule", "args": {}},
        )

        assert msg.function_call == {"name": "add_schedule", "args": {}}


class TestConversationMemory:
    """ConversationMemory 클래스 테스트."""

    def test_add_message(self):
        """메시지를 추가할 수 있다."""
        memory = ConversationMemory(max_size=10)

        memory.add("user", "안녕하세요")
        memory.add("model", "안녕하세요! 무엇을 도와드릴까요?")

        assert len(memory) == 2

    def test_max_size_limit(self):
        """max_size를 초과하면 오래된 메시지가 삭제된다."""
        memory = ConversationMemory(max_size=3)

        memory.add("user", "메시지 1")
        memory.add("model", "응답 1")
        memory.add("user", "메시지 2")
        memory.add("model", "응답 2")  # 이 시점에 "메시지 1"은 삭제됨

        assert len(memory) == 3
        messages = memory.get_messages()
        assert messages[0].content == "응답 1"  # 첫 번째 메시지는 삭제됨

    def test_get_context_format(self):
        """get_context()는 Gemini API 형식을 반환한다."""
        memory = ConversationMemory()

        memory.add("user", "오늘 일정 알려줘")
        memory.add("model", "오늘 일정은 없습니다.")

        context = memory.get_context()

        assert context == [
            {"role": "user", "parts": ["오늘 일정 알려줘"]},
            {"role": "model", "parts": ["오늘 일정은 없습니다."]},
        ]

    def test_clear(self):
        """clear()는 모든 메시지를 삭제한다."""
        memory = ConversationMemory()
        memory.add("user", "테스트")
        memory.add("model", "응답")

        memory.clear()

        assert len(memory) == 0
        assert memory.get_messages() == []

    def test_get_messages(self):
        """get_messages()는 모든 메시지를 리스트로 반환한다."""
        memory = ConversationMemory()
        memory.add("user", "첫 번째")
        memory.add("model", "두 번째")

        messages = memory.get_messages()

        assert len(messages) == 2
        assert all(isinstance(m, Message) for m in messages)


class TestBuildGeminiTools:
    """build_gemini_tools 함수 테스트."""

    def test_returns_tool_list(self):
        """Tool 객체 리스트를 반환한다."""
        tools = build_gemini_tools()

        assert isinstance(tools, list)
        assert len(tools) == 1  # 하나의 Tool 객체에 모든 함수 포함

    def test_includes_all_tool_definitions(self):
        """모든 TOOL_DEFINITIONS가 포함된다."""
        from tools import TOOL_DEFINITIONS

        tools = build_gemini_tools()
        func_declarations = tools[0].function_declarations

        tool_names = {fd.name for fd in func_declarations}
        expected_names = set(TOOL_DEFINITIONS.keys())

        assert tool_names == expected_names


class TestAgentUnit:
    """Agent 클래스 단위 테스트 (mock 사용)."""

    @pytest.fixture
    def mock_genai(self, monkeypatch):
        """google.generativeai 모듈을 모킹한다."""
        mock = MagicMock()
        monkeypatch.setattr("agent.genai", mock)
        return mock

    @pytest.fixture
    def mock_config(self, monkeypatch):
        """config() 함수를 모킹한다."""
        mock_cfg = MagicMock()
        mock_cfg.gemini_api_key = "test_key"
        mock_cfg.gemini_flash_model = "gemini-2.0-flash"
        mock_cfg.conversation_memory_size = 10
        mock_cfg.max_react_iterations = 5
        mock_cfg.database_path = ":memory:"  # 테스트용 인메모리 DB

        monkeypatch.setattr("agent.config", lambda: mock_cfg)
        return mock_cfg

    def test_agent_initialization(self, mock_genai, mock_config):
        """Agent가 올바르게 초기화된다."""
        agent = Agent()

        # Gemini API 설정 확인
        mock_genai.configure.assert_called_once_with(api_key="test_key")

        # 모델 생성 확인
        mock_genai.GenerativeModel.assert_called_once()

    def test_agent_with_custom_memory(self, mock_genai, mock_config):
        """커스텀 메모리를 주입할 수 있다."""
        custom_memory = ConversationMemory(max_size=5)
        agent = Agent(memory=custom_memory)

        assert agent.memory is custom_memory

    def test_clear_memory(self, mock_genai, mock_config):
        """clear_memory()는 메모리를 초기화한다."""
        agent = Agent()
        agent.memory.add("user", "테스트")

        agent.clear_memory()

        assert len(agent.memory) == 0


class TestSystemPrompt:
    """시스템 프롬프트 테스트."""

    def test_system_prompt_has_placeholders(self):
        """시스템 프롬프트에 날짜/시간 플레이스홀더가 있다."""
        assert "{today}" in SYSTEM_PROMPT
        assert "{now}" in SYSTEM_PROMPT

    def test_system_prompt_has_categories(self):
        """시스템 프롬프트에 카테고리 설명이 있다."""
        assert "학업" in SYSTEM_PROMPT
        assert "약속" in SYSTEM_PROMPT
        assert "개인" in SYSTEM_PROMPT

    def test_system_prompt_mentions_iso_format(self):
        """시스템 프롬프트에 ISO 형식 변환 지침이 있다."""
        assert "YYYY-MM-DD" in SYSTEM_PROMPT
        assert "HH:MM" in SYSTEM_PROMPT


# ============================================================
# 통합 테스트 (실제 Gemini API 호출)
# ============================================================

@pytest.mark.integration
class TestAgentIntegration:
    """
    실제 Gemini API를 호출하는 통합 테스트.

    실행: pytest -m integration tests/test_agent.py -v
    """

    @pytest.fixture
    def agent(self):
        """실제 Agent 인스턴스를 생성한다."""
        return Agent()

    @pytest.mark.asyncio
    async def test_simple_greeting(self, agent):
        """간단한 인사에 응답한다."""
        response = await agent.process_message("안녕하세요!")

        assert response  # 응답이 있어야 함
        assert isinstance(response, str)
        # 친근한 응답인지 확인 (이모지 포함 가능성)
        print(f"\n[응답] {response}")

    @pytest.mark.asyncio
    async def test_add_schedule_natural_language(self, agent):
        """자연어로 일정을 추가한다."""
        response = await agent.process_message(
            "내일 오후 3시에 팀 미팅 일정 추가해줘"
        )

        assert response
        print(f"\n[응답] {response}")
        # 응답에 일정 추가 관련 내용이 있어야 함
        # (정확한 텍스트는 LLM에 따라 다를 수 있음)

    @pytest.mark.asyncio
    async def test_get_today_schedules(self, agent):
        """오늘 일정을 조회한다."""
        response = await agent.process_message("오늘 일정 알려줘")

        assert response
        print(f"\n[응답] {response}")

    @pytest.mark.asyncio
    async def test_conversation_context(self, agent):
        """대화 맥락을 유지한다."""
        # 첫 번째 메시지
        await agent.process_message("내일 오전 10시에 회의 추가해줘")

        # 두 번째 메시지 (이전 맥락 참조)
        response = await agent.process_message("그 회의 장소는 회의실 A야")

        assert response
        print(f"\n[응답] {response}")
        assert len(agent.memory) >= 2  # 메모리에 대화가 저장되어 있어야 함

    @pytest.mark.asyncio
    async def test_travel_time_check(self, agent):
        """이동시간 확인 기능을 테스트한다."""
        # 먼저 일정 추가
        await agent.process_message("오늘 오후 2시에 강남역에서 미팅 추가해줘")

        # 이동시간 확인이 필요한 일정 추가
        response = await agent.process_message(
            "오늘 오후 3시에 판교에서 회의가 있어. 이동시간 괜찮을까?"
        )

        assert response
        print(f"\n[응답] {response}")
