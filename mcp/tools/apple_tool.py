"""Apple 앱과 상호작용하는 MCP 도구."""

from __future__ import annotations

import asyncio
import platform
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger

from ..apple_mcp_manager import AppleMCPManager, AppleMCPInstaller
from ..tool_blueprint import ToolBlueprint, ToolResult


@dataclass
class PerformanceMetrics:
    """Apple MCP 성능 메트릭."""
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration: float = 0.0
    retry_count: int = 0
    
    def success_rate(self) -> float:
        """성공률 계산."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    def average_duration(self) -> float:
        """평균 응답 시간 계산."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_duration / self.successful_requests


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
            "description": "생성/수정 시 사용할 데이터 (JSON 객체). 메시지 전송: {\"to\": \"전화번호\", \"message\": \"내용\"} 또는 {\"to\": \"전화번호\", \"body\": \"내용\"}",
        },
        "limit": {
            "type": "integer",
            "description": "결과 개수 제한 (기본값: 10)",
            "default": 10,
        },
    }

    def __init__(self, project_root: Optional[Path] = None):
        """
        Args:
            project_root: Angmini 프로젝트 루트 경로 (자동 감지 가능)
        """
        super().__init__()
        
        # macOS 환경 확인
        if not self._is_macos():
            raise ToolError("AppleTool은 macOS에서만 사용할 수 있습니다.")
        
        # 프로젝트 루트 설정
        if project_root is None:
            # 현재 파일 위치에서 프로젝트 루트 추정
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
        
        self._project_root = project_root
        self._apple_mcp_path = project_root / "external" / "apple-mcp"
        
        # Apple MCP 관리자 및 설치 관리자 초기화
        self._manager = AppleMCPManager(self._project_root)
        self._installer = AppleMCPInstaller(self._project_root)
        
        # 성능 메트릭
        self._metrics = PerformanceMetrics()
        
        # 보안 설정
        self._dangerous_patterns = [
            r"do\s+shell\s+script",
            r"tell\s+application\s+\"system",
            r"osascript\s+-e",
            r"\/usr\/bin\/",
            r"\/bin\/",
            r"sudo\s+",
            r"rm\s+-rf",
            r"killall\s+"
        ]
        self._max_text_length = 10000
        
        # 앱별 타임아웃 설정 (초)
        self._app_timeouts = {
            "contacts": 8.0,
            "notes": 6.0,
            "messages": 15.0,
            "mail": 20.0,
            "calendar": 10.0,
            "reminders": 8.0,
            "maps": 25.0,
        }
        
        # 연산별 특별 타임아웃 (실제 성능 측정 기반)
        self._operation_timeouts = {
            "notes.list": 8.0,      # list는 더 긴 시간 필요
            "notes.search": 15.0,   # search는 가장 오래 걸림
            "notes.create": 3.0,    # create는 빠르게
            "contacts.list": 5.0,   # contacts는 상대적으로 빠름
            "contacts.search": 8.0,
            "contacts.create": 3.0,
        }
        
        # 최대 재시도 횟수
        self._max_retries = 2
        
        # 지원하는 앱별 연산 매핑 (실제 Apple MCP 스키마 기반)
        self._app_operations = {
            "contacts": ["search", "list", "create"],  # Apple MCP 실제 지원 작업
            "notes": ["search", "list", "create", "update"],     # update 기능 추가됨
            "messages": ["search", "list", "send"],
            "mail": ["search", "list", "send"],
            "calendar": ["search", "list", "create"],
            "reminders": ["search", "list", "create", "mark_complete"],
            "maps": ["search", "find_route"],
        }

    def run(self, **kwargs: Any) -> ToolResult:
        """Apple 앱 작업을 실행합니다 (성능 최적화 및 안정성 기능 포함)."""
        start_time = time.time()
        
        try:
            # 1. 보안 검증
            security_violations = self._validate_security(kwargs)
            if security_violations:
                self._metrics.failed_requests += 1
                self._metrics.total_requests += 1
                return ToolResult(
                    success=False,
                    error=f"보안 검증 실패: {'; '.join(security_violations)}"
                )
            
            # 2. 파라미터 검증
            app = kwargs.get("app")
            operation = kwargs.get("operation")
            
            if not app or app not in self._app_operations:
                supported_apps = list(self._app_operations.keys())
                self._metrics.failed_requests += 1
                self._metrics.total_requests += 1
                return ToolResult(
                    success=False,
                    error=f"app 파라미터는 다음 중 하나여야 합니다: {supported_apps}"
                )
            
            if not operation or operation not in self._app_operations[app]:
                supported_ops = self._app_operations[app]
                self._metrics.failed_requests += 1
                self._metrics.total_requests += 1
                return ToolResult(
                    success=False,
                    error=f"{app} 앱에서 지원하는 operation: {supported_ops}. "
                           f"각 앱마다 지원되는 작업이 다릅니다. 위의 목록을 참고해주세요."
                )
            
            # 3. Apple MCP 서버 시작 (아직 시작되지 않은 경우)
            if not self._ensure_server_running():
                self._metrics.failed_requests += 1
                self._metrics.total_requests += 1
                return ToolResult(
                    success=False,
                    error="Apple MCP 서버를 시작할 수 없습니다. 설치 상태와 권한을 확인해주세요."
                )
            
            # 4. 타임아웃과 재시도가 적용된 작업 실행
            result = self._execute_with_retry_and_timeout(app, operation, kwargs)
            
            # 5. 성공 메트릭 업데이트
            duration = time.time() - start_time
            self._metrics.successful_requests += 1
            self._metrics.total_requests += 1
            self._metrics.total_duration += duration
            
            self._logger.info(
                f"Apple {app}.{operation} completed in {duration:.2f}s "
                f"(success rate: {self._metrics.success_rate():.1%})"
            )
            
            return ToolResult(success=True, data=result)
            
        except ToolError:
            self._metrics.failed_requests += 1
            self._metrics.total_requests += 1
            raise
        except Exception as exc:
            self._metrics.failed_requests += 1
            self._metrics.total_requests += 1
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
            # 먼저 설치 상태 확인
            if not self._installer.is_installed():
                self._logger.error("Apple MCP is not installed")
                return False
            
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

    def _validate_security(self, params: Dict[str, Any]) -> List[str]:
        """
        파라미터의 보안을 검증합니다.
        
        Args:
            params: 검증할 파라미터
            
        Returns:
            발견된 보안 위반 사항 목록
        """
        violations = []
        
        for key, value in params.items():
            if isinstance(value, str):
                # 텍스트 길이 검증
                if len(value) > self._max_text_length:
                    violations.append(f"{key}: 텍스트가 너무 깁니다 ({len(value)} > {self._max_text_length})")
                
                # 위험한 패턴 검사
                for pattern in self._dangerous_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        violations.append(f"{key}: 위험한 패턴 감지 - {pattern}")
            
            elif isinstance(value, dict):
                # 중첩된 딕셔너리도 재귀적으로 검증
                nested_violations = self._validate_security(value)
                violations.extend([f"{key}.{v}" for v in nested_violations])
        
        return violations

    def _execute_with_retry_and_timeout(self, app: str, operation: str, params: Dict[str, Any]) -> Any:
        """
        타임아웃과 재시도가 적용된 작업 실행.
        
        Args:
            app: 대상 앱
            operation: 실행할 작업
            params: 작업 파라미터
            
        Returns:
            작업 결과
        """
        # 연산별 특별 타임아웃이 있으면 사용, 없으면 앱 기본값 사용
        operation_key = f"{app}.{operation}"
        timeout = self._operation_timeouts.get(operation_key, self._app_timeouts.get(app, 10.0))
        
        last_error = None
        
        for attempt in range(self._max_retries + 1):
            try:
                if attempt > 0:
                    self._logger.info(f"Retrying {app}.{operation} (attempt {attempt + 1})")
                    self._metrics.retry_count += 1
                    # 재시도 간 대기 (지수 백오프)
                    time.sleep(0.5 * (2 ** attempt))
                
                # 실제 작업 실행
                return self._execute_app_operation_with_timeout(app, operation, params, timeout)
                
            except Exception as exc:
                last_error = exc
                self._logger.warning(f"Attempt {attempt + 1} failed for {app}.{operation}: {exc}")
                
                # 재시도 불가능한 오류들
                if self._is_non_retryable_error(exc):
                    break
        
        # 모든 재시도 실패
        raise last_error or ToolError(f"{app}.{operation} 작업이 {self._max_retries + 1}번의 시도 후 실패했습니다")

    def _execute_app_operation_with_timeout(self, app: str, operation: str, params: Dict[str, Any], timeout: float) -> Any:
        """
        타임아웃이 적용된 작업 실행.
        """
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"{app}.{operation} 작업이 {timeout}초 후 타임아웃되었습니다")
        
        # 타임아웃 설정 (Unix 시스템에서만)
        if hasattr(signal, 'SIGALRM'):
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout))
        
        try:
            result = self._execute_app_operation(app, operation, params)
            return result
        finally:
            # 타임아웃 해제
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

    def _is_non_retryable_error(self, error: Exception) -> bool:
        """
        재시도 불가능한 오류인지 판단합니다.
        """
        error_str = str(error).lower()
        
        non_retryable_keywords = [
            "permission",
            "authorization",
            "invalid parameter",
            "not found",
            "not supported",
            "unauthorized"
        ]
        
        return any(keyword in error_str for keyword in non_retryable_keywords)

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
        elif app == "messages":
            return self._map_messages_parameters(operation, params)
        # 다른 앱들도 필요에 따라 추가...
        
        # 기본적으로 operation과 다른 파라미터들을 그대로 전달
        return {
            "operation": operation,
            **{k: v for k, v in params.items() if k not in ["app", "operation"]}
        }
    
    def _map_notes_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """메모 앱용 파라미터 매핑."""
        result = {"operation": operation}  # operation은 항상 필수
        
        if operation == "search":
            # 검색 작업: searchText 파라미터 필요
            query = params.get("query", "")
            if query:
                result["searchText"] = query
        elif operation == "list":
            # 목록 조회 작업: limit 파라미터 설정
            limit = params.get("limit", 20)  # 기본 20개로 증가 (더 많은 최근 메모 조회)
            result["limit"] = limit
        elif operation == "create":
            # 생성 작업: title, body 파라미터 필요
            data = params.get("data", {})
            if isinstance(data, dict):
                # title이 없으면 content/body의 일부를 title로 사용
                if "title" in data:
                    result["title"] = data["title"]
                elif "content" in data or "body" in data:
                    content = data.get("content") or data.get("body", "")
                    # 내용의 첫 줄이나 첫 20자를 제목으로 사용
                    result["title"] = content[:20] + ("..." if len(content) > 20 else "")
                
                if "content" in data or "body" in data:
                    result["body"] = data.get("content") or data.get("body")
                if "folderName" in data:
                    result["folderName"] = data["folderName"]
            
            # 직접 content가 제공된 경우 (data 객체 없이)
            if "content" in params:
                content = params["content"]
                result["body"] = content
                if "title" not in result:
                    result["title"] = content[:20] + ("..." if len(content) > 20 else "")
        elif operation == "update":
            # 업데이트 작업: Apple MCP의 새로운 update 스키마 사용
            # searchQuery와 newContent 파라미터가 필요
            
            # 검색 조건 설정
            if "query" in params:
                result["searchQuery"] = params["query"]
            elif "search_text" in params:
                result["searchQuery"] = params["search_text"]
            elif "searchQuery" in params:
                result["searchQuery"] = params["searchQuery"]
            
            # 새로운 내용 설정
            data = params.get("data", {})
            if isinstance(data, dict):
                if "content" in data or "body" in data:
                    result["newContent"] = data.get("content") or data.get("body")
            
            # 직접 content가 제공된 경우
            if "content" in params:
                result["newContent"] = params["content"]
            elif "newContent" in params:
                result["newContent"] = params["newContent"]
            
            # 업데이트 모드 설정 (replace, append, prepend)
            if "updateMode" in params:
                result["updateMode"] = params["updateMode"]
            elif "mode" in params:
                result["updateMode"] = params["mode"]
            else:
                result["updateMode"] = "replace"  # 기본값
        elif operation == "delete":
            # 삭제 작업: 검색 조건 필요
            if "query" in params:
                result["searchText"] = params["query"]
            elif "id" in params:
                result["id"] = params["id"]
        
        return result
    
    def _map_contacts_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """연락처 앱용 파라미터 매핑."""
        result = {}
        
        # 연락처는 operation 파라미터를 사용하지 않고 name으로 검색
        query = params.get("query", "")
        if query:
            result["name"] = query
            
        return result

    def _map_messages_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        메시지 앱용 파라미터 매핑.
        
        AI가 생성하는 중첩 구조를 Apple MCP가 기대하는 플랫 구조로 변환합니다.
        
        변환 예시:
        입력: {"data": {"to": "010-1234-5678", "message": "안녕하세요"}}
        출력: {"operation": "send", "phoneNumber": "010-1234-5678", "message": "안녕하세요"}
        """
        result = {"operation": operation}
        
        if operation == "send":
            # AI가 data 객체에 중첩해서 보내는 경우 처리
            data = params.get("data", {})
            if isinstance(data, dict):
                # to → phoneNumber 필드명 변환
                if "to" in data:
                    result["phoneNumber"] = data["to"]
                # message 또는 body 필드 처리 (AI가 두 방식 모두 사용할 수 있음)
                if "message" in data:
                    result["message"] = data["message"]
                elif "body" in data:
                    result["message"] = data["body"]
            
            # 직접 파라미터로 전달된 경우도 처리 (백워드 호환성)
            if "to" in params:
                result["phoneNumber"] = params["to"]
            if "phoneNumber" in params:
                result["phoneNumber"] = params["phoneNumber"]
            if "message" in params:
                result["message"] = params["message"]
                
        elif operation == "list":
            # 메시지 목록 조회 시 필요한 파라미터들
            if "limit" in params:
                result["limit"] = params["limit"]
            if "contact" in params:
                result["contact"] = params["contact"]
        elif operation == "search":
            # 메시지 검색 시 필요한 파라미터들
            if "query" in params:
                result["searchText"] = params["query"]
            if "contact" in params:
                result["contact"] = params["contact"]
        
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

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        현재까지의 성능 메트릭을 반환합니다.
        
        Returns:
            성능 메트릭 딕셔너리
        """
        return {
            "total_requests": self._metrics.total_requests,
            "successful_requests": self._metrics.successful_requests,
            "failed_requests": self._metrics.failed_requests,
            "success_rate": self._metrics.success_rate(),
            "average_duration": self._metrics.average_duration(),
            "retry_count": self._metrics.retry_count,
        }

    def reset_metrics(self) -> None:
        """성능 메트릭을 초기화합니다."""
        self._metrics = PerformanceMetrics()
        self._logger.info("Performance metrics reset")

    def execute_batch(self, tasks: List[Dict[str, Any]]) -> List[ToolResult]:
        """
        여러 Apple 앱 작업을 배치로 처리합니다.
        
        Args:
            tasks: 실행할 작업 목록 (각각 app, operation 등을 포함하는 딕셔너리)
            
        Returns:
            각 작업의 결과 목록
        """
        results = []
        
        self._logger.info(f"Executing batch of {len(tasks)} tasks")
        
        for i, task in enumerate(tasks):
            try:
                self._logger.debug(f"Executing batch task {i + 1}/{len(tasks)}: {task}")
                result = self.run(**task)
                results.append(result)
            except Exception as exc:
                self._logger.error(f"Batch task {i + 1} failed: {exc}")
                results.append(ToolResult(
                    success=False,
                    error=f"Batch task {i + 1} failed: {exc}"
                ))
        
        success_count = sum(1 for r in results if r.success)
        self._logger.info(f"Batch completed: {success_count}/{len(tasks)} successful")
        
        return results

    def configure_timeouts(self, app_timeouts: Dict[str, float]) -> None:
        """
        앱별 타임아웃을 설정합니다.
        
        Args:
            app_timeouts: 앱별 타임아웃 딕셔너리 (앱 이름 -> 초)
        """
        self._app_timeouts.update(app_timeouts)
        self._logger.info(f"Updated app timeouts: {app_timeouts}")

    def configure_security(self, max_text_length: Optional[int] = None, 
                          additional_patterns: Optional[List[str]] = None) -> None:
        """
        보안 설정을 구성합니다.
        
        Args:
            max_text_length: 최대 텍스트 길이 제한
            additional_patterns: 추가로 차단할 위험한 패턴들
        """
        if max_text_length is not None:
            self._max_text_length = max_text_length
        
        if additional_patterns:
            self._dangerous_patterns.extend(additional_patterns)
        
        self._logger.info("Security configuration updated")

    def __del__(self) -> None:
        """리소스 정리: Apple MCP 서버 중지"""
        try:
            if hasattr(self, '_manager') and self._manager.is_server_running():
                self._manager.stop_server()
                self._logger.debug("Apple MCP server stopped during cleanup")
        except Exception as exc:
            self._logger.warning(f"Error during Apple MCP cleanup: {exc}")
