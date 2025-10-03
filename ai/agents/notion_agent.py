"""
agents/notion_agent.py
Notion 워크스페이스 관리 전문 에이전트
"""
from .base_agent import BaseAngminiAgent
from mcp.tools.notion_tool import NotionCrewAITool


class NotionAgent(BaseAngminiAgent):
    """Notion 작업 전문가"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 마크다운에서 프롬프트 로드
        self._prompts = self._load_prompt_from_markdown()

    def role(self) -> str:
        return self._prompts['role']

    def goal(self) -> str:
        return self._prompts['goal']

    def backstory(self) -> str:
        return self._prompts['backstory']

    def tools(self) -> list:
        return [NotionCrewAITool()]