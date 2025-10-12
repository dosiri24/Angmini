"""
agents/memory_agent.py
장기 기억 관리 전문 에이전트
"""
from typing import Optional
from .base_agent import BaseAngminiAgent
from mcp.tools.memory_tool import MemoryCrewAITool
from ai.memory.service import MemoryService
from ai.ai_brain import AIBrain
from ai.core.config import Config


class MemoryAgent(BaseAngminiAgent):
    """장기 기억 관리 전문가"""

    def __init__(
        self,
        ai_brain: Optional[AIBrain] = None,
        memory_service: Optional[MemoryService] = None,
        config: Optional[Config] = None,
        verbose: bool = True
    ):
        super().__init__(ai_brain, memory_service, config, verbose)
        # MemoryCrewAITool에 memory_service 전달
        self._memory_tool = MemoryCrewAITool(memory_service=memory_service)
        # 마크다운에서 프롬프트 로드
        self._prompts = self._load_prompt_from_markdown()

    def role(self) -> str:
        return self._prompts['role']

    def goal(self) -> str:
        return self._prompts['goal']

    def backstory(self) -> str:
        return self._prompts['backstory']

    def tools(self) -> list:
        return [self._memory_tool]