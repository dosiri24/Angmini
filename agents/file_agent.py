"""
agents/file_agent.py
파일 시스템 관리 전문 에이전트
"""
from .base_agent import BaseAngminiAgent
from mcp.crewai_adapters.file_crewai_tool import FileCrewAITool


class FileAgent(BaseAngminiAgent):
    """파일 시스템 작업 전문가"""

    def role(self) -> str:
        return "파일 시스템 관리 전문가"

    def goal(self) -> str:
        return "파일 및 디렉토리 작업을 정확하고 효율적으로 수행"

    def backstory(self) -> str:
        return """
        당신은 파일 시스템 작업의 전문가입니다.
        파일 읽기/쓰기, 디렉토리 탐색, 파일 검색을 담당합니다.
        사용자가 요청한 파일 작업을 안전하고 정확하게 수행하세요.

        주요 책임:
        - 파일 내용 읽기 및 분석
        - 파일 생성 및 수정
        - 디렉토리 구조 탐색
        - 파일 검색 및 필터링

        작업 원칙:
        - 파일 작업 시 항상 경로를 명확히 확인
        - 파일 쓰기 전 기존 파일 백업 고려
        - 대용량 파일 처리 시 효율성 고려
        - 파일 권한 및 보안 준수
        """

    def tools(self) -> list:
        return [FileCrewAITool()]