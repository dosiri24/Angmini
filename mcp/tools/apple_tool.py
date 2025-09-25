"""Apple 앱과 상호작용하는 MCP 도구."""

from __future__ import annotations

import platform
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

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
    - 연락처 (Contacts): 연락처 검색 및 조회
    - 메모 (Notes): 메모 생성, 검색, 조회
    - 메시지 (Messages): 메시지 전송, 읽기, 예약, 미확인 메시지 조회
    - 메일 (Mail): 이메일 조회, 검색, 전송 및 계정/메일함 탐색
    - 캘린더 (Calendar): 일정 검색, 열기, 생성, 기간별 조회
    - 미리알림 (Reminders): 알림 조회, 검색, 생성, 리스트 단위 조회
    - 지도 (Maps): 위치 검색, 즐겨찾기/가이드 관리, 길찾기
    
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
                "accounts",
                "addToGuide",
                "create",
                "createGuide",
                "directions",
                "latest",
                "list",
                "listById",
                "listGuides",
                "mailboxes",
                "open",
                "pin",
                "read",
                "save",
                "schedule",
                "search",
                "send",
                "unread",
            ],
            "description": "수행할 작업",
        },
        "query": {
            "type": "string",
            "description": "검색어 또는 조건",
        },
        "limit": {
            "type": "integer",
            "description": "결과 개수 제한",
        },
        "phone_number": {
            "type": "string",
            "description": "전화번호 (메시지 앱)",
        },
        "scheduled_time": {
            "type": "string",
            "description": "예약 발송 시간 ISO 문자열 (메시지 앱)",
        },
        "to": {
            "type": "string",
            "description": "메일/메시지 수신자",
        },
        "subject": {
            "type": "string",
            "description": "메일 제목",
        },
        "body": {
            "type": "string",
            "description": "메일/메시지 본문",
        },
        "account": {
            "type": "string",
            "description": "메일 계정 이름",
        },
        "mailbox": {
            "type": "string",
            "description": "메일함 이름",
        },
        "calendar_name": {
            "type": "string",
            "description": "캘린더 이름",
        },
        "start_date": {
            "type": "string",
            "description": "시작 일시 ISO 문자열 (캘린더)",
        },
        "end_date": {
            "type": "string",
            "description": "종료 일시 ISO 문자열 (캘린더)",
        },
        "location": {
            "type": "string",
            "description": "위치 정보",
        },
        "notes": {
            "type": "string",
            "description": "추가 메모",
        },
        "is_all_day": {
            "type": "boolean",
            "description": "종일 일정 여부",
        },
        "list_id": {
            "type": "string",
            "description": "Reminders 리스트 ID",
        },
        "guide_name": {
            "type": "string",
            "description": "지도 가이드 이름",
        },
        "from_address": {
            "type": "string",
            "description": "출발지 주소 (지도)",
        },
        "to_address": {
            "type": "string",
            "description": "도착지 주소 (지도)",
        },
        "transport_type": {
            "type": "string",
            "enum": ["driving", "walking", "transit"],
            "description": "이동 수단 (지도)",
        },
        "data": {
            "type": "object",
            "description": "생성/수정 시 사용할 데이터 (JSON 객체). 메시지 전송: {\"to\": \"전화번호\", \"message\": \"내용\"} 또는 {\"to\": \"전화번호\", \"body\": \"내용\"}",
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
            "notes.list": 8.0,
            "notes.search": 15.0,
            "notes.create": 3.0,
            "messages.send": 15.0,
            "messages.schedule": 20.0,
            "mail.search": 20.0,
            "maps.directions": 30.0,
        }
        
        # 최대 재시도 횟수
        self._max_retries = 2
        
        # 지원하는 앱별 연산 매핑 (실제 Apple MCP 스키마 기반)
        self._app_operations = {
            "contacts": ["list", "search"],
            "notes": ["list", "search", "create"],
            "messages": ["send", "read", "schedule", "unread"],
            "mail": ["unread", "search", "send", "mailboxes", "accounts", "latest"],
            "calendar": ["search", "open", "list", "create"],
            "reminders": ["list", "search", "open", "create", "listById"],
            "maps": ["search", "save", "directions", "pin", "listGuides", "addToGuide", "createGuide"],
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

    def _get_param_value(self, params: Dict[str, Any], *keys: str) -> Optional[Any]:
        """요청 파라미터에서 지정된 키 중 첫 번째로 발견되는 값을 반환합니다."""
        data = params.get("data")
        if isinstance(data, dict):
            for key in keys:
                if key in data and data[key] is not None:
                    return data[key]

        for key in keys:
            if key in params and params[key] is not None:
                return params[key]

        return None

    def _coerce_int(self, value: Any, field_name: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ToolError(f"{field_name} 값은 정수여야 합니다: {value}") from None

    def _coerce_bool(self, value: Any, field_name: str) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no"}:
                return False
        raise ToolError(f"{field_name} 값은 true/false 여야 합니다: {value}")

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
        if app == "contacts":
            return self._map_contacts_parameters(operation, params)
        if app == "messages":
            return self._map_messages_parameters(operation, params)
        if app == "mail":
            return self._map_mail_parameters(operation, params)
        if app == "calendar":
            return self._map_calendar_parameters(operation, params)
        if app == "reminders":
            return self._map_reminders_parameters(operation, params)
        if app == "maps":
            return self._map_maps_parameters(operation, params)

        # 기본적으로 operation과 다른 파라미터들을 그대로 전달 (data는 평탄화하지 않음)
        return {
            "operation": operation,
            **{k: v for k, v in params.items() if k not in ["app", "operation", "data"]}
        }
    
    def _map_notes_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """메모 앱용 파라미터 매핑."""
        result = {"operation": operation}

        if operation == "search":
            query = self._get_param_value(params, "query", "searchText", "search_text")
            if not query:
                raise ToolError("notes.search 작업에는 검색어(query)가 필요합니다.")
            result["searchText"] = query
            limit = self._get_param_value(params, "limit")
            if limit is not None:
                result["limit"] = limit
        elif operation == "list":
            limit = self._get_param_value(params, "limit")
            if limit is not None:
                result["limit"] = limit
        elif operation == "create":
            title = self._get_param_value(params, "title")
            body = self._get_param_value(params, "body", "content")

            if body is None:
                raise ToolError("notes.create 작업에는 메모 본문(body 또는 content)이 필요합니다.")

            body_text = str(body)
            if not title:
                title = body_text[:20] + ("..." if len(body_text) > 20 else "")

            result["title"] = title
            result["body"] = body

            folder = self._get_param_value(params, "folderName", "folder_name")
            if folder:
                result["folderName"] = folder
        else:
            raise ToolError(f"notes 앱은 '{operation}' 작업을 지원하지 않습니다.")

        return result
    
    def _map_contacts_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """연락처 앱용 파라미터 매핑."""
        if operation == "list":
            return {}

        if operation == "search":
            name = self._get_param_value(params, "query", "name")
            if not name:
                raise ToolError("contacts.search 작업에는 검색어(query)가 필요합니다.")
            return {"name": name}

        raise ToolError(f"contacts 앱은 '{operation}' 작업을 지원하지 않습니다.")

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
            phone = self._get_param_value(params, "phoneNumber", "phone_number", "to")
            message = self._get_param_value(params, "message", "body", "text")

            if not phone or not message:
                raise ToolError("messages.send 작업에는 수신자(to/phoneNumber)와 message가 필요합니다.")

            result["phoneNumber"] = phone
            result["message"] = message

        elif operation == "read":
            phone = self._get_param_value(params, "phoneNumber", "phone_number", "to")
            if not phone:
                raise ToolError("messages.read 작업에는 phoneNumber가 필요합니다.")

            result["phoneNumber"] = phone
            limit = self._get_param_value(params, "limit")
            if limit is not None:
                result["limit"] = limit

        elif operation == "schedule":
            phone = self._get_param_value(params, "phoneNumber", "phone_number", "to")
            message = self._get_param_value(params, "message", "body", "text")
            scheduled_time = self._get_param_value(params, "scheduledTime", "scheduled_time")

            if not phone or not message or not scheduled_time:
                raise ToolError("messages.schedule 작업에는 phoneNumber, message, scheduled_time이 모두 필요합니다.")

            result["phoneNumber"] = phone
            result["message"] = message
            result["scheduledTime"] = scheduled_time

        elif operation == "unread":
            limit = self._get_param_value(params, "limit")
            if limit is not None:
                result["limit"] = limit

        else:
            raise ToolError(f"messages 앱은 '{operation}' 작업을 지원하지 않습니다.")

        return result

    def _map_mail_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """메일 앱용 파라미터 매핑."""
        result = {"operation": operation}

        if operation == "unread":
            account = self._get_param_value(params, "account")
            mailbox = self._get_param_value(params, "mailbox")
            limit = self._get_param_value(params, "limit")

            if account:
                result["account"] = account
            if mailbox:
                result["mailbox"] = mailbox
            if limit is not None:
                result["limit"] = self._coerce_int(limit, "limit")

        elif operation == "search":
            search_term = self._get_param_value(params, "query", "searchTerm", "search_term")
            if not search_term:
                raise ToolError("mail.search 작업에는 검색어(query)가 필요합니다.")

            result["searchTerm"] = search_term

            account = self._get_param_value(params, "account")
            mailbox = self._get_param_value(params, "mailbox")
            limit = self._get_param_value(params, "limit")

            if account:
                result["account"] = account
            if mailbox:
                result["mailbox"] = mailbox
            if limit is not None:
                result["limit"] = self._coerce_int(limit, "limit")

        elif operation == "send":
            to_addr = self._get_param_value(params, "to", "recipient")
            subject = self._get_param_value(params, "subject")
            body = self._get_param_value(params, "body", "content")

            if not to_addr or not subject or body is None:
                raise ToolError("mail.send 작업에는 to, subject, body가 모두 필요합니다.")

            result.update({
                "to": to_addr,
                "subject": subject,
                "body": body,
            })

            cc = self._get_param_value(params, "cc")
            bcc = self._get_param_value(params, "bcc")
            if cc:
                result["cc"] = cc
            if bcc:
                result["bcc"] = bcc

        elif operation == "mailboxes":
            account = self._get_param_value(params, "account")
            if account:
                result["account"] = account

        elif operation == "accounts":
            pass

        elif operation == "latest":
            account = self._get_param_value(params, "account")
            mailbox = self._get_param_value(params, "mailbox")
            limit = self._get_param_value(params, "limit")

            if account:
                result["account"] = account
            if mailbox:
                result["mailbox"] = mailbox
            if limit is not None:
                result["limit"] = self._coerce_int(limit, "limit")

        else:
            raise ToolError(f"mail 앱은 '{operation}' 작업을 지원하지 않습니다.")

        return result

    def _map_calendar_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """캘린더 앱용 파라미터 매핑."""
        result = {"operation": operation}

        if operation == "search":
            search_text = self._get_param_value(params, "query", "searchText", "search_text")
            if not search_text:
                raise ToolError("calendar.search 작업에는 검색어(query)가 필요합니다.")
            result["searchText"] = search_text

            limit = self._get_param_value(params, "limit")
            if limit is not None:
                result["limit"] = self._coerce_int(limit, "limit")

            from_date = self._get_param_value(params, "fromDate", "from_date", "start_date")
            to_date = self._get_param_value(params, "toDate", "to_date", "end_date")
            if from_date:
                result["fromDate"] = from_date
            if to_date:
                result["toDate"] = to_date

        elif operation == "open":
            event_id = self._get_param_value(params, "eventId", "event_id", "id")
            if not event_id:
                raise ToolError("calendar.open 작업에는 eventId가 필요합니다.")
            result["eventId"] = event_id

        elif operation == "list":
            limit = self._get_param_value(params, "limit")
            if limit is not None:
                result["limit"] = self._coerce_int(limit, "limit")

            from_date = self._get_param_value(params, "fromDate", "from_date", "start_date")
            to_date = self._get_param_value(params, "toDate", "to_date", "end_date")
            if from_date:
                result["fromDate"] = from_date
            if to_date:
                result["toDate"] = to_date

        elif operation == "create":
            title = self._get_param_value(params, "title")
            start_date = self._get_param_value(params, "startDate", "start_date")
            end_date = self._get_param_value(params, "endDate", "end_date")

            if not title or not start_date or not end_date:
                raise ToolError("calendar.create 작업에는 title, start_date, end_date가 필요합니다.")

            result.update({
                "title": title,
                "startDate": start_date,
                "endDate": end_date,
            })

            location = self._get_param_value(params, "location")
            notes = self._get_param_value(params, "notes")
            is_all_day = self._get_param_value(params, "isAllDay", "is_all_day")
            calendar_name = self._get_param_value(params, "calendarName", "calendar_name")

            if location:
                result["location"] = location
            if notes:
                result["notes"] = notes
            if is_all_day is not None:
                result["isAllDay"] = self._coerce_bool(is_all_day, "is_all_day")
            if calendar_name:
                result["calendarName"] = calendar_name

        else:
            raise ToolError(f"calendar 앱은 '{operation}' 작업을 지원하지 않습니다.")

        return result

    def _map_reminders_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """미리알림 앱용 파라미터 매핑."""
        result = {"operation": operation}

        if operation == "list":
            return result

        if operation == "search":
            search_text = self._get_param_value(params, "query", "searchText", "search_text")
            if not search_text:
                raise ToolError("reminders.search 작업에는 검색어(query)가 필요합니다.")
            result["searchText"] = search_text
            return result

        if operation == "open":
            search_text = self._get_param_value(params, "query", "searchText", "search_text")
            if not search_text:
                raise ToolError("reminders.open 작업에는 검색어(query)가 필요합니다.")
            result["searchText"] = search_text
            return result

        if operation == "create":
            name = self._get_param_value(params, "name", "title")
            if not name:
                raise ToolError("reminders.create 작업에는 name이 필요합니다.")

            result["name"] = name

            list_name = self._get_param_value(params, "listName", "list_name")
            notes = self._get_param_value(params, "notes")
            due_date = self._get_param_value(params, "dueDate", "due_date")

            if list_name:
                result["listName"] = list_name
            if notes:
                result["notes"] = notes
            if due_date:
                result["dueDate"] = due_date

            return result

        if operation == "listById":
            list_id = self._get_param_value(params, "listId", "list_id")
            if not list_id:
                raise ToolError("reminders.listById 작업에는 list_id가 필요합니다.")

            result["listId"] = list_id

            props = self._get_param_value(params, "props")
            if props:
                if isinstance(props, str):
                    result["props"] = [props]
                elif isinstance(props, list):
                    result["props"] = props
                else:
                    raise ToolError("props 값은 문자열 또는 문자열 리스트여야 합니다.")

            return result

        raise ToolError(f"reminders 앱은 '{operation}' 작업을 지원하지 않습니다.")

    def _map_maps_parameters(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """지도 앱용 파라미터 매핑."""
        result = {"operation": operation}

        if operation == "search":
            query = self._get_param_value(params, "query")
            if not query:
                raise ToolError("maps.search 작업에는 query가 필요합니다.")
            result["query"] = query

            limit = self._get_param_value(params, "limit")
            if limit is not None:
                result["limit"] = self._coerce_int(limit, "limit")

            return result

        if operation in {"save", "pin"}:
            name = self._get_param_value(params, "name")
            address = self._get_param_value(params, "address")

            if not name or not address:
                raise ToolError(f"maps.{operation} 작업에는 name과 address가 필요합니다.")

            result["name"] = name
            result["address"] = address
            return result

        if operation == "directions":
            from_address = self._get_param_value(params, "fromAddress", "from_address")
            to_address = self._get_param_value(params, "toAddress", "to_address")

            if not from_address or not to_address:
                raise ToolError("maps.directions 작업에는 from_address와 to_address가 필요합니다.")

            result["fromAddress"] = from_address
            result["toAddress"] = to_address

            transport_type = (self._get_param_value(params, "transportType", "transport_type") or "driving").lower()
            if transport_type not in {"driving", "walking", "transit"}:
                raise ToolError("maps.directions transport_type는 driving/walking/transit 중 하나여야 합니다.")

            result["transportType"] = transport_type
            return result

        if operation == "listGuides":
            return result

        if operation == "addToGuide":
            address = self._get_param_value(params, "address")
            guide_name = self._get_param_value(params, "guideName", "guide_name")

            if not address or not guide_name:
                raise ToolError("maps.addToGuide 작업에는 address와 guide_name이 필요합니다.")

            result["address"] = address
            result["guideName"] = guide_name
            return result

        if operation == "createGuide":
            guide_name = self._get_param_value(params, "guideName", "guide_name")
            if not guide_name:
                raise ToolError("maps.createGuide 작업에는 guide_name이 필요합니다.")
            result["guideName"] = guide_name
            return result

        raise ToolError(f"maps 앱은 '{operation}' 작업을 지원하지 않습니다.")

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
