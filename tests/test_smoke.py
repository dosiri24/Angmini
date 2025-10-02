"""High-level smoke tests to ensure critical components wire up correctly."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ai.ai_brain import AIBrain
from ai.core.config import Config
from ai.core.exceptions import EngineError
from mcp.tool_blueprint import ToolBlueprint, ToolResult


@pytest.fixture(name="dummy_genai")
def fixture_dummy_genai(monkeypatch):
    """Provide a fake Gemini client so tests run without external dependencies."""

    class DummyGenerativeModel:
        def __init__(self, model_name: str) -> None:
            self.model_name = model_name

        def generate_content(self, contents, generation_config=None):
            return SimpleNamespace(
                candidates=[
                    SimpleNamespace(
                        content=SimpleNamespace(
                            parts=[SimpleNamespace(text="smoke-output")]
                        )
                    )
                ]
            )

    fake_genai = SimpleNamespace(
        configure=lambda api_key: None,
        GenerativeModel=lambda model_name: DummyGenerativeModel(model_name),
    )

    import ai.ai_brain as brain

    monkeypatch.setattr(brain, "genai", fake_genai, raising=False)
    monkeypatch.setattr(brain, "_IMPORT_ERROR", None, raising=False)
    return fake_genai


def test_ai_brain_generate_text_smoke(dummy_genai):
    config = Config(
        default_interface="cli",
        discord_bot_token=None,
        gemini_api_key="fake-key",
        gemini_model="models/gemini-1.5-pro",
        log_level="INFO",
    )

    brain = AIBrain(config)
    response = brain.generate_text("hello")
    assert response.text == "smoke-output"


def test_ai_brain_requires_api_key(dummy_genai):
    config = Config(
        default_interface="cli",
        discord_bot_token=None,
        gemini_api_key=None,
        gemini_model="models/gemini-1.5-pro",
        log_level="INFO",
    )

    with pytest.raises(EngineError):
        AIBrain(config)


# ToolManager 관련 테스트는 제거됨 (CrewAI 마이그레이션으로 ToolManager 미사용)
