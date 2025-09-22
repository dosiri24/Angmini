"""Apple 앱과 상호작용하는 MCP 도구."""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger

from ..apple_mcp_manager import AppleMCPManager
from ..tool_blueprint import ToolBlueprint, ToolResult


class AppleTool(ToolBlueprint):
    """
    Apple MCP를 통해 macOS 네이티브 앱들과 상호작용하는 도구.
    
    지원하는 Apple 앱:
    - 연락처 (Contacts): 연락처 검색, 추가, 수정
    - 메모 (Notes): 메모 생성, 검색, 수정
    - 메시지 (Messages): 메시지 전송, 대화 내역 조회
    - 메일 (Mail): 이메일 전송, 수신함 조회
    - 캘린더 (Calendar): 일정 생성, 조회, 수정
    - 미리알림 (Reminders): 알림 생성, 조회, 완료 처리
    - 지도 (Maps): 위치 검색, 길찾기
    
    Why Apple MCP?
    - macOS의 AppleScript를 통한 네이티브 앱 제어
    - 시스템 레벨 통합으로 안정적인 동작
    - 표준 MCP 프로토콜 준수
    """

    tool_name = "apple"
    description = "macOS Apple 앱들과 상호작용 (연락처, 메모, 메시지, 메일, 캘린더, 미리알림, 지도)"
    parameters: Dict[str, Any] = {
        "app": {
            "type": "string",
            "enum": ["contacts", "notes", "messages", "mail", "calendar", "reminders", "maps"],
            "description": "사용할 Apple 앱",
        },
        "operation": {
            "type": "string",
            "enum": [
                # 공통
                "search", "list", "get",
                # 생성/수정
                "create", "add", "update", "delete",
                # 액션
                "send", "mark_complete", "find_route"
            ],
            "description": "수행할 작업",
        },
        "query": {
            "type": "string",
            "description": "검색어 또는 조건",
        },
        "data": {
            "type": "object",
            "description": "생성/수정 시 사용할 데이터 (JSON 객체)",
        },
        "limit": {
            "type": "integer",
            "description": "결과 개수 제한 (기본값: 10)",
            "default": 10,
        },
    }

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """
        Args:
            project_root: Angmini 프로젝트 루트 경로 (None이면 자동 감지)
        """
        super().__init__()
        self._logger = get_logger(self.__class__.__name__)
        
        # macOS 환경 확인
        if not self._is_macos():
            raise ToolError("AppleTool은 macOS에서만 사용할 수 있습니다.")
        
        # Apple MCP 관리자 초기화
        self._manager = AppleMCPManager(project_root)
        
        # 지원하는 앱별 연산 매핑
        self._app_operations = {
            "contacts": ["search", "list", "get", "create", "update", "delete"],
            "notes": ["search", "list", "get", "create", "update", "delete"],
            "messages": ["search", "list", "send"],
            "mail": ["search", "list", "send"],
            "calendar": ["search", "list", "get", "create", "update", "delete"],
            "reminders": ["search", "list", "get", "create", "update", "delete", "mark_complete"],
            "maps": ["search", "find_route"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        """Apple 앱 작업을 실행합니다."""
        try:
            # 파라미터 검증
            app = kwargs.get("app")
            operation = kwargs.get("operation")
            
            if not app or app not in self._app_operations:
                supported_apps = list(self._app_operations.keys())
                raise ToolError(f"app 파라미터는 다음 중 하나여야 합니다: {supported_apps}")
            
            if not operation or operation not in self._app_operations[app]:
                supported_ops = self._app_operations[app]
                raise ToolError(f"{app} 앱에서 지원하는 operation: {supported_ops}")
            
            # Apple MCP 서버 시작 (아직 시작되지 않은 경우)
            if not self._ensure_server_running():
                return ToolResult(
                    success=False,
                    error="Apple MCP 서버를 시작할 수 없습니다. 설치 상태와 권한을 확인해주세요."
                )
            
            # 앱별 작업 실행
            result = self._execute_app_operation(app, operation, kwargs)
            return ToolResult(success=True, data=result)
            
        except ToolError:
            raise
        except Exception as exc:
            self._logger.error(f"Apple tool execution failed: {exc}")
            raise ToolError(f"Apple 앱 작업 중 오류가 발생했습니다: {exc}") from exc

    def _is_macos(self) -> bool:
        """macOS 환경인지 확인합니다."""
        return platform.system() == "Darwin"

    def _ensure_server_running(self) -> bool:
        """
        Apple MCP 서버가 실행 중인지 확인하고, 그렇지 않으면 시작합니다.
        
        Returns:
            서버 시작 성공 여부
        """
        try:
            if self._manager.is_server_running():
                self._logger.debug("Apple MCP server is already running")
                return True
            
            self._logger.info("Starting Apple MCP server...")
            success = self._manager.start_server()
            
            if success:
                self._logger.info("Apple MCP server started successfully")
            else:
                self._logger.error("Failed to start Apple MCP server")
                
            return success
            
        except Exception as exc:
            self._logger.error(f"Error checking/starting Apple MCP server: {exc}")
            return False

    def _execute_app_operation(self, app: str, operation: str, params: Dict[str, Any]) -> Any:
        """
        특정 앱에서 작업을 실행합니다.
        
        Args:
            app: 대상 앱 이름
            operation: 실행할 작업
            params: 작업에 필요한 파라미터들
            
        Returns:
            작업 결과
        """
        # Apple MCP 서버에 전송할 요청 구성
        mcp_method = "tools/call"
        
        # 앱별 파라미터 매핑
        arguments = self._map_parameters_for_app(app, operation, params)
        
        mcp_params = {
            "name": app,  # Apple MCP에서는 직접 앱 이름 사용 (예: "notes", "contacts")
            "arguments": arguments
        }
        
        try:
            # Apple MCP 서버에 요청 전송
            response = self._manager.send_request(mcp_method, mcp_params)
            
            # 응답 처리
            if "content" in response:
                # MCP 도구 응답 형태
                content = response["content"]
                if isinstance(content, list) and len(content) > 0:
                    return content[0].get("text", content)
                return content
            
            # 직접 결과 반환
            return response
            
        except Exception as exc:
            self._logger.error(f"Apple MCP request failed: {exc}")
            
            # 권한 오류인지 확인
            if "permission" in str(exc).lower() or "authorization" in str(exc).lower():
                raise ToolError(
                    f"{app} 앱에 대한 권한이 없습니다. "
                    f"시스템 환경설정 > 보안 및 개인 정보 보호에서 권한을 확인해주세요."
                )
            
            # 서버 연결 오류인지 확인
            if "connection" in str(exc).lower() or "timeout" in str(exc).lower():
                # 서버 재시작 시도
                self._logger.info("Attempting to restart Apple MCP server...")
                if self._manager.restart_server():
                    # 재시도
                    try:
                        response = self._manager.send_request(mcp_method, mcp_params)
                        if "content" in response:
                            content = response["content"]
                            if isinstance(content, list) and len(content) > 0:
                                return content[0].get("text", content)
                            return content
                        return response
                    except Exception as retry_exc:
                        raise ToolError(f"Apple MCP 서버 재시작 후에도 실패: {retry_exc}") from retry_exc
                else:
                    raise ToolError("Apple MCP 서버 재시작에 실패했습니다.") from exc
            
            raise ToolError(f"{app} 앱 작업 실행 실패: {exc}") from exc

    def _map_parameters_for_app(self, app: str, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        앱별로 파라미터를 Apple MCP API 형식에 맞게 매핑합니다.
        
        Args:
            app: 대상 앱 이름
            operation: 실행할 작업
            params: 원본 파라미터들
            
        Returns:
            Apple MCP API용으로 매핑된 파라미터들
        """
        if app == "notes":
            return self._map_notes_parameters(operation, params)
        elif app == "contacts":
            return self._map_contacts_parameters(operation, params)
        # 다른 앱들도 필요에 따라 추가...
        
        # 기본적으로 operation과 다른 파라미터들을 그대로 전달
        return {
            "operation": operation,
            **{k: v for k, v in params.items() if k not in ["app", "operation"]}
        }
    
    def _map_notes_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """메모 앱용 파라미터 매핑."""
        result = {"operation": operation}
        
        if operation == "search":
            # 검색 작업: searchText 파라미터 필요
            query = params.get("query", "")
            if query:
                result["searchText"] = query
        elif operation == "create":
            # 생성 작업: title, body 파라미터 필요
            data = params.get("data", {})
            if isinstance(data, dict):
                if "title" in data:
                    result["title"] = data["title"]
                if "content" in data or "body" in data:
                    result["body"] = data.get("content") or data.get("body")
                if "folderName" in data:
                    result["folderName"] = data["folderName"]
        # "list" 작업은 추가 파라미터가 필요하지 않음
        
        return result
    
    def _map_contacts_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """연락처 앱용 파라미터 매핑."""
        result = {}
        
        # 연락처는 operation 파라미터를 사용하지 않고 name으로 검색
        query = params.get("query", "")
        if query:
            result["name"] = query
            
        return result

    def get_permission_guide(self, app: str) -> str:
        """
        특정 앱에 대한 권한 설정 가이드를 반환합니다.
        
        Args:
            app: 대상 앱 이름
            
        Returns:
            권한 설정 가이드 텍스트
        """
        guides = {
            "contacts": """
연락처 앱 권한 설정:
1. 시스템 환경설정 > 보안 및 개인 정보 보호 > 개인 정보 보호 탭
2. 연락처 선택
3. Terminal 또는 Python 앱에 체크박스 활성화
4. 필요시 앱을 재시작
""",
            "notes": """
메모 앱 권한 설정:
1. 시스템 환경설정 > 보안 및 개인 정보 보호 > 개인 정보 보호 탭
2. 전체 디스크 접근 권한 선택
3. Terminal 또는 Python 앱에 체크박스 활성화
4. 필요시 앱을 재시작
""",
            "messages": """
메시지 앱 권한 설정:
1. 시스템 환경설정 > 보안 및 개인 정보 보호 > 개인 정보 보호 탭
2. 전체 디스크 접근 권한 선택
3. Terminal 또는 Python 앱에 체크박스 활성화
4. 필요시 앱을 재시작
""",
            "mail": """
메일 앱 권한 설정:
1. 시스템 환경설정 > 보안 및 개인 정보 보호 > 개인 정보 보호 탭
2. 전체 디스크 접근 권한 선택
3. Terminal 또는 Python 앱에 체크박스 활성화
4. 필요시 앱을 재시작
""",
            "calendar": """
캘린더 앱 권한 설정:
1. 시스템 환경설정 > 보안 및 개인 정보 보호 > 개인 정보 보호 탭
2. 캘린더 선택
3. Terminal 또는 Python 앱에 체크박스 활성화
4. 필요시 앱을 재시작
""",
            "reminders": """
미리알림 앱 권한 설정:
1. 시스템 환경설정 > 보안 및 개인 정보 보호 > 개인 정보 보호 탭
2. 미리알림 선택
3. Terminal 또는 Python 앱에 체크박스 활성화
4. 필요시 앱을 재시작
""",
            "maps": """
지도 앱 권한 설정:
1. 시스템 환경설정 > 보안 및 개인 정보 보호 > 개인 정보 보호 탭
2. 위치 서비스 선택
3. 지도 앱에 대한 위치 접근 허용
4. 필요시 앱을 재시작
""",
        }
        
        return guides.get(app, "해당 앱에 대한 권한 가이드를 찾을 수 없습니다.")

    def __del__(self) -> None:
        """리소스 정리: Apple MCP 서버 중지"""
        try:
            if hasattr(self, '_manager') and self._manager.is_server_running():
                self._manager.stop_server()
                self._logger.debug("Apple MCP server stopped during cleanup")
        except Exception as exc:
            self._logger.warning(f"Error during Apple MCP cleanup: {exc}")
