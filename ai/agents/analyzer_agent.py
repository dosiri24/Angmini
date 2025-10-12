"""
agents/analyzer_agent.py
멀티모달 파일 분석 전문 에이전트 (이미지, 문서, PDF)
"""
from .base_agent import BaseAngminiAgent
from mcp.tools.image_analysis_tool import ImageAnalysisCrewAITool
from mcp.tools.document_analysis_tool import DocumentAnalysisCrewAITool
from mcp.tools.pdf_analysis_tool import PDFAnalysisCrewAITool


class AnalyzerAgent(BaseAngminiAgent):
    """멀티모달 파일 분석 전문가 (이미지, 문서, PDF)"""

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
        return [
            ImageAnalysisCrewAITool(),
            DocumentAnalysisCrewAITool(),
            PDFAnalysisCrewAITool(),
        ]
