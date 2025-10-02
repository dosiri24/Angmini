"""
agents/__init__.py
에이전트 팩토리 및 공통 유틸리티
"""
from typing import List, Optional
from ai.ai_brain import AIBrain
from ai.memory.service import MemoryService
from ai.core.config import Config

from .base_agent import BaseAngminiAgent
from .planner_agent import PlannerAgent
from .file_agent import FileAgent
from .notion_agent import NotionAgent
from .memory_agent import MemoryAgent
from .system_agent import SystemAgent


class AgentFactory:
    """에이전트 생성 팩토리"""

    @staticmethod
    def create_all_agents(
        ai_brain: Optional[AIBrain] = None,
        memory_service: Optional[MemoryService] = None,
        config: Optional[Config] = None
    ) -> List[BaseAngminiAgent]:
        """모든 에이전트 생성"""
        config = config or Config.load()

        agents = [
            FileAgent(ai_brain, memory_service, config),
            NotionAgent(ai_brain, memory_service, config),
            MemoryAgent(ai_brain, memory_service, config),
            SystemAgent(ai_brain, memory_service, config)
        ]

        return agents

    @staticmethod
    def create_planner(
        ai_brain: Optional[AIBrain] = None,
        memory_service: Optional[MemoryService] = None,
        config: Optional[Config] = None
    ) -> PlannerAgent:
        """Planner 에이전트 생성"""
        config = config or Config.load()
        return PlannerAgent(ai_brain, memory_service, config)


__all__ = [
    'AgentFactory',
    'BaseAngminiAgent',
    'PlannerAgent',
    'FileAgent',
    'NotionAgent',
    'MemoryAgent',
    'SystemAgent',
]