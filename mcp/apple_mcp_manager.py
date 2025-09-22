"""
Apple MCP 서버와의 통신을 관리하는 모듈.

이 모듈은 외부 Node.js Apple MCP 서버를 Python 프로세스와 연결하는 브릿지 역할을 합니다.
Apple MCP는 macOS의 네이티브 앱들(연락처, 메시지, 메일 등)과 상호작용하기 위해
AppleScript를 사용하는 TypeScript/Node.js 기반 서버입니다.

Architecture Design:
- 프로세스 격리: Apple MCP 서버를 별도 프로세스로 실행하여 안정성 확보
- 표준 통신: STDIO 기반 JSON-RPC 프로토콜 사용
- 복구 메커니즘: 서버 장애 시 자동 재시작 및 연결 복구
- 확장성: 새로운 Apple 앱 지원이 Apple MCP에 추가되면 자동으로 활용 가능
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
import uuid
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

from ai.core.exceptions import ToolError
from ai.core.logger import get_logger


class STDIOCommunicator:
    """
    Apple MCP 서버와 STDIO 기반 JSON-RPC 통신을 담당하는 클래스.
    
    Why STDIO?
    - Apple MCP 서버가 표준 입출력으로 통신하도록 설계됨
    - HTTP보다 오버헤드가 적고 지연시간이 짧음
    - MCP(Model Context Protocol) 표준 준수
    """
    
    def __init__(self, command: List[str], working_dir: Optional[Path] = None):
        """
        Args:
            command: 실행할 명령어 리스트 (예: ["bun", "run", "start"])
            working_dir: 작업 디렉토리 (Apple MCP 서버 위치)
        """
        self._logger = get_logger(self.__class__.__name__)
        self._command = command
        self._working_dir = working_dir
        self._process: Optional[subprocess.Popen] = None
        self._response_queue: Queue[Dict[str, Any]] = Queue()
        self._pending_requests: Dict[str, Queue[Dict[str, Any]]] = {}
        self._reader_thread: Optional[threading.Thread] = None
        self._shutdown = False
        
    def start(self) -> None:
        """서버 프로세스를 시작하고 통신 스레드를 초기화합니다."""
        if self._process is not None:
            raise ToolError("STDIOCommunicator is already running")
            
        try:
            # Apple MCP 서버 프로세스 시작
            # text=True: 문자열로 입출력 처리
            # bufsize=0: 즉시 플러시하여 실시간 통신 보장
            self._process = subprocess.Popen(
                self._command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
                cwd=self._working_dir
            )
            
            # 응답 읽기를 위한 별도 스레드 시작
            # Why separate thread? 
            # - STDIO 읽기는 블로킹 연산이므로 메인 스레드가 멈출 수 있음
            # - 비동기적으로 여러 요청을 처리하기 위해 필요
            self._reader_thread = threading.Thread(target=self._read_responses, daemon=True)
            self._reader_thread.start()
            
            self._logger.info(f"Apple MCP server started with PID {self._process.pid}")
            
        except Exception as e:
            self._cleanup()
            raise ToolError(f"Failed to start Apple MCP server: {e}") from e
    
    def stop(self) -> None:
        """서버 프로세스를 중지하고 리소스를 정리합니다."""
        self._shutdown = True
        self._cleanup()
    
    def send_request(self, method: str, params: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """
        Apple MCP 서버에 JSON-RPC 요청을 전송하고 응답을 받습니다.
        
        Why timeout?
        - Apple 앱 작업(메시지 전송, 연락처 검색 등)은 시간이 걸릴 수 있음
        - 무한 대기를 방지하여 시스템 안정성 확보
        
        Args:
            method: MCP 메서드 이름 (예: "tools/call")
            params: 요청 파라미터
            timeout: 응답 대기 시간 (초)
            
        Returns:
            서버 응답 딕셔너리
            
        Raises:
            ToolError: 통신 실패, 시간 초과, 또는 서버 오류 시
        """
        if self._process is None or self._process.poll() is not None:
            raise ToolError("Apple MCP server is not running")
        
        if self._process.stdin is None:
            raise ToolError("Apple MCP server stdin is not available")
        
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        # 응답을 받을 큐 생성
        response_queue: Queue[Dict[str, Any]] = Queue()
        self._pending_requests[request_id] = response_queue
        
        try:
            # 요청 전송
            request_line = json.dumps(request) + '\n'
            self._process.stdin.write(request_line)
            self._process.stdin.flush()
            
            self._logger.debug(f"Sent request: {method} with ID {request_id}")
            
            # 응답 대기
            try:
                response = response_queue.get(timeout=timeout)
                self._logger.debug(f"Received response for ID {request_id}")
                
                # JSON-RPC 오류 확인
                if "error" in response:
                    error_info = response["error"]
                    raise ToolError(f"Apple MCP server error: {error_info}")
                
                return response.get("result", {})
                
            except Empty:
                raise ToolError(f"Timeout waiting for response from Apple MCP server (timeout: {timeout}s)")
                
        finally:
            # 대기 중인 요청 정리
            self._pending_requests.pop(request_id, None)
    
    def is_running(self) -> bool:
        """서버가 실행 중인지 확인합니다."""
        return self._process is not None and self._process.poll() is None
    
    def _read_responses(self) -> None:
        """
        서버로부터 응답을 읽어서 해당하는 요청 큐에 전달하는 스레드 함수.
        
        Why separate thread?
        - stdout.readline()은 블로킹 연산이므로 메인 스레드에서 실행하면 전체 시스템이 멈출 수 있음
        - 여러 요청이 동시에 처리될 수 있도록 비동기 처리 필요
        """
        while not self._shutdown and self.is_running():
            try:
                if self._process is None or self._process.stdout is None:
                    break
                    
                line = self._process.stdout.readline()
                if not line:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                
                response = json.loads(line)
                request_id = response.get("id")
                
                if request_id and request_id in self._pending_requests:
                    self._pending_requests[request_id].put(response)
                else:
                    self._logger.warning(f"Received response for unknown request ID: {request_id}")
                    
            except json.JSONDecodeError as e:
                self._logger.error(f"Failed to parse JSON response: {e}")
            except Exception as e:
                self._logger.error(f"Error reading response: {e}")
                break
    
    def _cleanup(self) -> None:
        """프로세스와 관련 리소스를 정리합니다."""
        if self._process:
            try:
                self._process.terminate()
                # 정상 종료를 위해 잠시 대기
                self._process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                # 강제 종료
                self._process.kill()
                self._process.wait()
            except Exception as e:
                self._logger.error(f"Error during process cleanup: {e}")
            finally:
                self._process = None
        
        # 대기 중인 요청들에 오류 응답 전송
        for queue in self._pending_requests.values():
            try:
                queue.put({"error": {"message": "Server shutdown"}})
            except Exception:
                pass
        self._pending_requests.clear()


class ProcessManager:
    """
    Apple MCP 서버 프로세스의 생명주기를 관리하는 클래스.
    
    Why separate from STDIOCommunicator?
    - 단일 책임 원칙: 통신과 프로세스 관리는 별도 관심사
    - 재사용성: 다른 프로세스 관리에도 활용 가능
    - 테스트 용이성: 각 기능을 독립적으로 테스트 가능
    """
    
    def __init__(self, max_restarts: int = 3, restart_delay: float = 1.0):
        """
        Args:
            max_restarts: 최대 재시작 횟수 (무한 재시작 방지)
            restart_delay: 재시작 간 대기 시간 (초)
        """
        self._logger = get_logger(self.__class__.__name__)
        self._max_restarts = max_restarts
        self._restart_delay = restart_delay
        self._restart_count = 0
        self._last_restart_time = 0.0
        
    def can_restart(self) -> bool:
        """재시작이 가능한지 확인합니다."""
        return self._restart_count < self._max_restarts
    
    def should_restart(self, communicator: STDIOCommunicator) -> bool:
        """
        서버 재시작이 필요한지 판단합니다.
        
        Why not just restart immediately?
        - 일시적인 네트워크 문제일 수 있음
        - 너무 빈번한 재시작은 시스템 리소스 낭비
        - 재시작 횟수 제한으로 무한 루프 방지
        """
        if not communicator.is_running():
            return self.can_restart()
        return False
    
    def restart_server(self, communicator: STDIOCommunicator, 
                      command: List[str], working_dir: Optional[Path] = None) -> bool:
        """
        서버를 재시작합니다.
        
        Returns:
            재시작 성공 여부
        """
        if not self.can_restart():
            self._logger.error(f"Maximum restart attempts ({self._max_restarts}) reached")
            return False
        
        current_time = time.time()
        
        # 너무 빠른 연속 재시작 방지
        if current_time - self._last_restart_time < self._restart_delay:
            time.sleep(self._restart_delay)
        
        try:
            self._logger.info(f"Restarting Apple MCP server (attempt {self._restart_count + 1}/{self._max_restarts})")
            
            # 기존 프로세스 정리
            communicator.stop()
            
            # 새 프로세스 시작
            communicator.__init__(command, working_dir)  # 재초기화
            communicator.start()
            
            self._restart_count += 1
            self._last_restart_time = current_time
            
            self._logger.info("Apple MCP server restarted successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to restart Apple MCP server: {e}")
            return False
    
    def reset_restart_count(self) -> None:
        """재시작 카운터를 리셋합니다. (성공적인 동작 후 호출)"""
        self._restart_count = 0


class AppleMCPInstaller:
    """
    Apple MCP 설치 상태를 확인하고 설치 가이드를 제공하는 클래스.
    
    Why separate installer?
    - 설치는 일회성 작업이므로 런타임 로직과 분리
    - 사용자에게 명확한 설치 가이드 제공
    - 환경 검증을 통한 조기 오류 발견
    """
    
    def __init__(self, project_root: Path):
        """
        Args:
            project_root: Angmini 프로젝트 루트 디렉토리
        """
        self._logger = get_logger(self.__class__.__name__)
        self._project_root = project_root
        self._apple_mcp_path = project_root / "external" / "apple-mcp"
    
    def is_installed(self) -> bool:
        """Apple MCP가 설치되어 있는지 확인합니다."""
        required_files = [
            self._apple_mcp_path / "package.json",
            self._apple_mcp_path / "dist" / "index.js",
            self._apple_mcp_path / "node_modules"
        ]
        
        return all(path.exists() for path in required_files)
    
    def check_prerequisites(self) -> Dict[str, bool]:
        """
        필수 요구사항을 확인합니다.
        
        Returns:
            각 요구사항의 충족 여부를 담은 딕셔너리
        """
        checks = {}
        
        # Bun 런타임 확인
        try:
            result = subprocess.run(["bun", "--version"], 
                                   capture_output=True, text=True, timeout=5.0)
            checks["bun"] = result.returncode == 0
            if checks["bun"]:
                self._logger.info(f"Bun version: {result.stdout.strip()}")
        except Exception:
            checks["bun"] = False
        
        # macOS 확인
        try:
            result = subprocess.run(["sw_vers", "-productName"], 
                                   capture_output=True, text=True, timeout=5.0)
            checks["macos"] = "macOS" in result.stdout or "Mac OS X" in result.stdout
        except Exception:
            checks["macos"] = False
        
        # Apple MCP 경로 확인
        checks["apple_mcp_path"] = self._apple_mcp_path.exists()
        
        return checks
    
    def get_installation_guide(self) -> str:
        """설치 가이드 문자열을 반환합니다."""
        guide = """
🍎 Apple MCP 설치 가이드

1. 필수 요구사항:
   - macOS 시스템
   - Bun 런타임 (https://bun.sh/)

2. 설치 명령어:
   cd {project_root}/external
   git clone https://github.com/supermemoryai/apple-mcp.git
   cd apple-mcp
   bun install
   bun run build

3. macOS 권한 설정:
   시스템 설정 > 개인정보 보호 및 보안에서 다음 권한 허용:
   - 자동화 (Automation)
   - 전체 디스크 접근 (Full Disk Access)
   - 연락처 (Contacts)

권한 설정 없이는 Apple 앱에 접근할 수 없습니다.
        """.format(project_root=self._project_root)
        
        return guide.strip()


class AppleMCPManager:
    """
    Apple MCP 서버와의 모든 상호작용을 총괄 관리하는 메인 클래스.
    
    This is the main facade class that provides a simple interface for:
    - Starting/stopping the Apple MCP server
    - Sending commands to Apple apps
    - Handling server failures and recovery
    - Managing installation and prerequisites
    
    Design Pattern: Facade Pattern
    - 복잡한 서브시스템(STDIOCommunicator, ProcessManager, AppleMCPInstaller)을
      단순한 인터페이스로 감싸서 사용자가 쉽게 사용할 수 있게 함
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Args:
            project_root: Angmini 프로젝트 루트 (None이면 자동 감지)
        """
        self._logger = get_logger(self.__class__.__name__)
        
        # 프로젝트 루트 자동 감지
        if project_root is None:
            # 현재 파일에서 프로젝트 루트 찾기
            current_file = Path(__file__)
            project_root = current_file.parent.parent  # mcp/apple_mcp_manager.py -> project_root
        
        self._project_root = project_root
        self._apple_mcp_path = project_root / "external" / "apple-mcp"
        
        # 하위 컴포넌트들 초기화
        self._installer = AppleMCPInstaller(project_root)
        self._process_manager = ProcessManager()
        self._communicator: Optional[STDIOCommunicator] = None
        
        # 서버 실행 명령어
        self._server_command = ["bun", "run", "start"]
    
    def start_server(self) -> bool:
        """
        Apple MCP 서버를 시작합니다.
        
        Returns:
            시작 성공 여부
        """
        try:
            # 설치 상태 확인
            if not self._installer.is_installed():
                self._logger.error("Apple MCP is not installed")
                self._logger.info(self._installer.get_installation_guide())
                return False
            
            # 필수 요구사항 확인
            checks = self._installer.check_prerequisites()
            if not all(checks.values()):
                failed_checks = [k for k, v in checks.items() if not v]
                self._logger.error(f"Prerequisites not met: {failed_checks}")
                return False
            
            # 이미 실행 중인지 확인
            if self._communicator and self._communicator.is_running():
                self._logger.info("Apple MCP server is already running")
                return True
            
            # 새 통신기 생성 및 시작
            self._communicator = STDIOCommunicator(
                command=self._server_command,
                working_dir=self._apple_mcp_path
            )
            self._communicator.start()
            
            # 서버 응답 테스트
            if self._test_server_connection():
                self._process_manager.reset_restart_count()
                return True
            else:
                self._logger.error("Server started but failed connection test")
                self.stop_server()
                return False
                
        except Exception as e:
            self._logger.error(f"Failed to start Apple MCP server: {e}")
            return False
    
    def stop_server(self) -> None:
        """Apple MCP 서버를 중지합니다."""
        if self._communicator:
            self._communicator.stop()
            self._communicator = None
            self._logger.info("Apple MCP server stopped")
    
    def send_request(self, method: str, params: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """
        Apple MCP 서버에 JSON-RPC 요청을 전송합니다.
        
        이는 AppleTool에서 직접 사용하는 저수준 인터페이스입니다.
        일반적인 명령은 send_command 메서드를 사용하세요.
        
        Args:
            method: JSON-RPC 메서드 이름
            params: 요청 파라미터
            timeout: 응답 대기 시간 (초)
            
        Returns:
            서버 응답 데이터
        """
        if not self._ensure_server_running():
            raise ToolError("Cannot establish connection to Apple MCP server")
        
        if self._communicator is None:
            raise ToolError("Apple MCP communicator is not available")
        
        return self._communicator.send_request(method, params, timeout)

    def restart_server(self) -> bool:
        """
        서버를 재시작합니다.
        
        Returns:
            재시작 성공 여부
        """
        if self._communicator is not None:
            self.stop_server()
        
        return self.start_server()

    def send_command(self, tool_name: str, operation: str, **params) -> Dict[str, Any]:
        """
        Apple MCP 서버에 명령을 전송합니다.
        
        Args:
            tool_name: 도구 이름 (예: "contacts", "messages")
            operation: 작업 종류 (예: "search", "send")
            **params: 추가 파라미터
            
        Returns:
            서버 응답 데이터
            
        Raises:
            ToolError: 서버 연결 실패, 명령 실행 오류 등
        """
        # 서버 상태 확인 및 복구
        if not self._ensure_server_running():
            raise ToolError("Cannot establish connection to Apple MCP server")
        
        if self._communicator is None:
            raise ToolError("Apple MCP communicator is not available")
        
        try:
            # MCP 표준 형식으로 요청 구성
            request_params = {
                "name": tool_name,
                "arguments": {
                    "operation": operation,
                    **params
                }
            }
            
            response = self._communicator.send_request("tools/call", request_params)
            return response
            
        except Exception as e:
            self._logger.error(f"Command failed: {tool_name}.{operation} - {e}")
            raise ToolError(f"Apple MCP command failed: {e}") from e
    
    def is_server_running(self) -> bool:
        """서버가 실행 중인지 확인합니다."""
        return self._communicator is not None and self._communicator.is_running()
    
    def get_status(self) -> Dict[str, Any]:
        """현재 상태 정보를 반환합니다."""
        return {
            "server_running": self.is_server_running(),
            "installed": self._installer.is_installed(),
            "prerequisites": self._installer.check_prerequisites(),
            "restart_count": self._process_manager._restart_count,
            "can_restart": self._process_manager.can_restart()
        }
    
    def _ensure_server_running(self) -> bool:
        """
        서버가 실행 중인지 확인하고, 필요시 재시작합니다.
        
        Why this method?
        - Apple 앱 작업 중 서버가 크래시할 수 있음
        - 자동 복구로 사용자 경험 향상
        - Explicit Failure Handling (Rule 2) 준수: 복구 불가능하면 명시적 실패
        """
        if self.is_server_running():
            return True
        
        self._logger.warning("Apple MCP server is not running, attempting restart...")
        
        # None 체크 추가
        if self._communicator is not None and self._process_manager.should_restart(self._communicator):
            success = self._process_manager.restart_server(
                self._communicator, 
                self._server_command, 
                self._apple_mcp_path
            )
            if success and self._test_server_connection():
                return True
        
        return False
    
    def _test_server_connection(self) -> bool:
        """서버 연결을 테스트합니다."""
        if self._communicator is None:
            return False
            
        try:
            # 간단한 테스트 명령: tools/list로 사용 가능한 도구 목록 요청
            # 이는 Apple MCP에서 가장 기본적인 요청입니다
            self._communicator.send_request("tools/list", {}, timeout=10.0)
            return True
        except Exception as e:
            self._logger.debug(f"Server connection test failed: {e}")
            return False