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
from .apple_apps_agent import AppleAppsAgent
from .analyzer_agent import AnalyzerAgent


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
            AppleAppsAgent(ai_brain, memory_service, config),
            AnalyzerAgent(ai_brain, memory_service, config),
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

    @staticmethod
    def get_agent_by_role(role_name: str, agents: List[BaseAngminiAgent]) -> Optional[BaseAngminiAgent]:
        """역할명으로 에이전트 찾기

        Args:
            role_name: 찾을 에이전트의 역할명 (agent.role() 값)
            agents: 검색할 에이전트 리스트

        Returns:
            매칭되는 에이전트 또는 None

        Example:
            >>> file_agent = AgentFactory.get_agent_by_role("파일 시스템 관리 전문가", agents)
        """
        for agent in agents:
            if agent.role() == role_name:
                return agent
        return None


__all__ = [
    'AgentFactory',
    'BaseAngminiAgent',
    'PlannerAgent',
    'FileAgent',
    'NotionAgent',
    'MemoryAgent',
    'AppleAppsAgent',
    'AnalyzerAgent',
]