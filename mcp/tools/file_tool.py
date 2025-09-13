"""
File Tool 모듈: 파일 시스템 작업을 수행하는 도구입니다.

이 도구는 다음과 같은 기능을 제공합니다:
- 파일 읽기 (텍스트 파일)
- 파일 쓰기 (텍스트 파일)
- 디렉토리 목록 조회
- 파일 존재 여부 확인
- 파일 정보 조회 (크기, 수정 시간 등)
"""

import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from mcp.tool_blueprint import ToolBlueprint, ToolResult, ToolResultStatus
from ai.core.logger import logger


class FileTool(ToolBlueprint):
    """
    파일 시스템 작업을 수행하는 도구 클래스입니다.
    
    이 클래스는 보안을 고려하여 다음과 같은 제한사항을 가집니다:
    - 사용자 홈 디렉토리 및 하위 디렉토리만 접근 허용
    - 시스템 파일 수정 금지
    - 실행 파일 생성/수정 금지
    """
    
    def __init__(self, allowed_base_paths: Optional[List[str]] = None):
        """
        FileTool 인스턴스를 초기화합니다.
        
        Args:
            allowed_base_paths (List[str]): 접근 허용된 기본 경로 목록
                                          None이면 사용자 홈 디렉토리로 제한
        """
        super().__init__(
            name="file_tool",
            description="파일 읽기, 쓰기, 디렉토리 조회 등의 파일 시스템 작업을 수행합니다"
        )
        
        # Rule 2: Explicit Failure Handling
        # 보안을 위해 접근 가능한 경로를 명시적으로 제한합니다.
        # 이는 악의적이거나 실수에 의한 시스템 파일 접근을 방지합니다.
        if allowed_base_paths is None:
            self.allowed_base_paths = [str(Path.home())]
        else:
            self.allowed_base_paths = [os.path.abspath(path) for path in allowed_base_paths]
        
        # 지원하는 파일 확장자 (보안상 제한)
        self.safe_extensions = {
            '.txt', '.md', '.json', '.csv', '.log', '.py', '.js', '.html', '.css',
            '.yaml', '.yml', '.xml', '.ini', '.conf', '.cfg'
        }
        
        logger.info(f"FileTool 초기화 완료 - 허용 경로: {self.allowed_base_paths}")
    
    def execute(self, action_input: str) -> ToolResult:
        """
        파일 도구의 핵심 실행 메서드입니다.
        
        Args:
            action_input (str): JSON 형태의 입력 
                예: {"action": "read", "path": "/path/to/file.txt"}
                
        Returns:
            ToolResult: 실행 결과
        """
        try:
            # Rule 4: Clear and Detailed Comments
            # 입력을 JSON으로 파싱하여 구조화된 명령을 처리합니다.
            # 이는 AI가 복잡한 파일 작업을 정확하게 지시할 수 있도록 돕습니다.
            
            # JSON 파싱 시도
            try:
                params = json.loads(action_input)
            except json.JSONDecodeError:
                # JSON이 아닌 경우 단순 경로로 간주하고 읽기 시도
                params = {"action": "read", "path": action_input.strip()}
            
            action = params.get("action", "read").lower()
            file_path = params.get("path", "")
            
            if not file_path:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    content="파일 경로가 제공되지 않았습니다",
                    error_message="필수 매개변수 'path'가 누락되었습니다"
                )
            
            # 경로 보안 검증
            if not self._is_path_allowed(file_path):
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    content="접근이 허용되지 않은 경로입니다",
                    error_message=f"경로 '{file_path}'는 보안상 접근이 제한됩니다"
                )
            
            # 액션별 처리
            if action == "read":
                return self._read_file(file_path)
            elif action == "write":
                content = params.get("content", "")
                return self._write_file(file_path, content)
            elif action == "list" or action == "ls":
                return self._list_directory(file_path)
            elif action == "exists":
                return self._check_file_exists(file_path)
            elif action == "info":
                return self._get_file_info(file_path)
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    content=f"지원하지 않는 액션입니다: {action}",
                    error_message=f"사용 가능한 액션: read, write, list, exists, info"
                )
                
        except Exception as e:
            logger.error(f"FileTool 실행 중 오류: {str(e)}")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content="파일 작업 중 예상치 못한 오류가 발생했습니다",
                error_message=str(e)
            )
    
    def _is_path_allowed(self, file_path: str) -> bool:
        """
        주어진 경로가 접근 허용된 경로인지 확인합니다.
        
        Args:
            file_path (str): 확인할 파일 경로
            
        Returns:
            bool: 접근 허용 시 True
        """
        try:
            abs_path = os.path.abspath(file_path)
            
            # 허용된 기본 경로 내에 있는지 확인
            for allowed_path in self.allowed_base_paths:
                if abs_path.startswith(allowed_path):
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _read_file(self, file_path: str) -> ToolResult:
        """
        파일을 읽어서 내용을 반환합니다.
        
        Args:
            file_path (str): 읽을 파일 경로
            
        Returns:
            ToolResult: 읽기 결과
        """
        try:
            if not os.path.exists(file_path):
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    content=f"파일을 찾을 수 없습니다: {file_path}",
                    error_message="파일이 존재하지 않습니다"
                )
            
            if os.path.isdir(file_path):
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    content=f"디렉토리입니다: {file_path}",
                    error_message="파일이 아닌 디렉토리입니다"
                )
            
            # 파일 확장자 확인
            file_ext = Path(file_path).suffix.lower()
            if file_ext and file_ext not in self.safe_extensions:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    content=f"지원하지 않는 파일 형식입니다: {file_ext}",
                    error_message="보안상 허용되지 않는 파일 형식입니다"
                )
            
            # 파일 크기 확인 (10MB 제한)
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # 10MB
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    content=f"파일이 너무 큽니다: {file_size / (1024*1024):.1f}MB",
                    error_message="10MB 이하의 파일만 읽을 수 있습니다"
                )
            
            # 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=content,
                data={
                    "file_path": file_path,
                    "file_size": file_size,
                    "lines_count": content.count('\\n') + 1
                }
            )
            
        except UnicodeDecodeError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content="텍스트 파일이 아닙니다 (인코딩 오류)",
                error_message="UTF-8로 디코딩할 수 없는 파일입니다"
            )
        except PermissionError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content="파일 읽기 권한이 없습니다",
                error_message="파일에 대한 읽기 권한이 없습니다"
            )
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content="파일 읽기 중 오류가 발생했습니다",
                error_message=str(e)
            )
    
    def _write_file(self, file_path: str, content: str) -> ToolResult:
        """
        파일에 내용을 씁니다.
        
        Args:
            file_path (str): 쓸 파일 경로
            content (str): 파일에 쓸 내용
            
        Returns:
            ToolResult: 쓰기 결과
        """
        try:
            # 파일 확장자 확인
            file_ext = Path(file_path).suffix.lower()
            if file_ext and file_ext not in self.safe_extensions:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    content=f"지원하지 않는 파일 형식입니다: {file_ext}",
                    error_message="보안상 허용되지 않는 파일 형식입니다"
                )
            
            # 디렉토리 생성 (필요한 경우)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 파일 쓰기
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            file_size = os.path.getsize(file_path)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"파일이 성공적으로 저장되었습니다: {file_path}",
                data={
                    "file_path": file_path,
                    "file_size": file_size,
                    "lines_written": content.count('\\n') + 1
                }
            )
            
        except PermissionError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content="파일 쓰기 권한이 없습니다",
                error_message="파일에 대한 쓰기 권한이 없습니다"
            )
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content="파일 쓰기 중 오류가 발생했습니다",
                error_message=str(e)
            )
    
    def _list_directory(self, dir_path: str) -> ToolResult:
        """
        디렉토리의 내용을 나열합니다.
        
        Args:
            dir_path (str): 조회할 디렉토리 경로
            
        Returns:
            ToolResult: 디렉토리 목록 결과
        """
        try:
            if not os.path.exists(dir_path):
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    content=f"디렉토리를 찾을 수 없습니다: {dir_path}",
                    error_message="디렉토리가 존재하지 않습니다"
                )
            
            if not os.path.isdir(dir_path):
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    content=f"파일입니다 (디렉토리가 아님): {dir_path}",
                    error_message="디렉토리가 아닙니다"
                )
            
            # 디렉토리 목록 조회
            items = []
            for item_name in sorted(os.listdir(dir_path)):
                item_path = os.path.join(dir_path, item_name)
                is_dir = os.path.isdir(item_path)
                
                try:
                    size = os.path.getsize(item_path) if not is_dir else 0
                    modified = datetime.fromtimestamp(os.path.getmtime(item_path))
                    
                    items.append({
                        "name": item_name,
                        "type": "directory" if is_dir else "file",
                        "size": size,
                        "modified": modified.strftime("%Y-%m-%d %H:%M:%S")
                    })
                except (OSError, PermissionError):
                    # 접근할 수 없는 항목은 기본 정보만 포함
                    items.append({
                        "name": item_name,
                        "type": "directory" if is_dir else "file",
                        "size": 0,
                        "modified": "접근 불가"
                    })
            
            # 결과 포맷팅
            content_lines = [f"디렉토리: {dir_path}", f"항목 수: {len(items)}개", ""]
            
            for item in items:
                type_marker = "📁" if item["type"] == "directory" else "📄"
                if item["modified"] != "접근 불가":
                    size_str = f"{item['size']:,} bytes" if item["type"] == "file" else ""
                    content_lines.append(
                        f"{type_marker} {item['name']} {size_str} ({item['modified']})"
                    )
                else:
                    content_lines.append(f"{type_marker} {item['name']} (접근 불가)")
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content="\\n".join(content_lines),
                data={
                    "directory_path": dir_path,
                    "items": items,
                    "total_count": len(items)
                }
            )
            
        except PermissionError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content="디렉토리 접근 권한이 없습니다",
                error_message="디렉토리에 대한 읽기 권한이 없습니다"
            )
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content="디렉토리 조회 중 오류가 발생했습니다",
                error_message=str(e)
            )
    
    def _check_file_exists(self, file_path: str) -> ToolResult:
        """
        파일이 존재하는지 확인합니다.
        
        Args:
            file_path (str): 확인할 파일 경로
            
        Returns:
            ToolResult: 존재 여부 확인 결과
        """
        try:
            exists = os.path.exists(file_path)
            is_file = os.path.isfile(file_path) if exists else False
            is_dir = os.path.isdir(file_path) if exists else False
            
            if exists:
                item_type = "파일" if is_file else "디렉토리" if is_dir else "기타"
                content = f"{item_type}이 존재합니다: {file_path}"
            else:
                content = f"존재하지 않습니다: {file_path}"
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=content,
                data={
                    "path": file_path,
                    "exists": exists,
                    "is_file": is_file,
                    "is_directory": is_dir
                }
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content="파일 존재 확인 중 오류가 발생했습니다",
                error_message=str(e)
            )
    
    def _get_file_info(self, file_path: str) -> ToolResult:
        """
        파일의 상세 정보를 조회합니다.
        
        Args:
            file_path (str): 정보를 조회할 파일 경로
            
        Returns:
            ToolResult: 파일 정보 조회 결과
        """
        try:
            if not os.path.exists(file_path):
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    content=f"파일을 찾을 수 없습니다: {file_path}",
                    error_message="파일이 존재하지 않습니다"
                )
            
            stat = os.stat(file_path)
            is_file = os.path.isfile(file_path)
            is_dir = os.path.isdir(file_path)
            
            info = {
                "path": file_path,
                "type": "파일" if is_file else "디렉토리" if is_dir else "기타",
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "accessed": datetime.fromtimestamp(stat.st_atime).strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if is_file:
                info["extension"] = Path(file_path).suffix
                info["size_mb"] = round(stat.st_size / (1024 * 1024), 2)
            
            content_lines = [
                f"파일 정보: {file_path}",
                f"유형: {info['type']}",
                f"크기: {info['size']:,} bytes" + (f" ({info.get('size_mb', 0)}MB)" if is_file else ""),
                f"생성일: {info['created']}",
                f"수정일: {info['modified']}",
                f"접근일: {info['accessed']}"
            ]
            
            if is_file and info.get("extension"):
                content_lines.append(f"확장자: {info['extension']}")
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content="\\n".join(content_lines),
                data=info
            )
            
        except PermissionError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content="파일 정보 접근 권한이 없습니다",
                error_message="파일에 대한 정보 조회 권한이 없습니다"
            )
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content="파일 정보 조회 중 오류가 발생했습니다",
                error_message=str(e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """
        FileTool의 스키마 정보를 반환합니다.
        
        Returns:
            Dict[str, Any]: 스키마 정보
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "action": {
                    "type": "string",
                    "description": "수행할 작업 (read, write, list, exists, info)",
                    "required": True,
                    "enum": ["read", "write", "list", "exists", "info"]
                },
                "path": {
                    "type": "string", 
                    "description": "대상 파일 또는 디렉토리 경로",
                    "required": True
                },
                "content": {
                    "type": "string",
                    "description": "파일에 쓸 내용 (write 액션에서만 사용)",
                    "required": False
                }
            },
            "input_format": "JSON",
            "allowed_extensions": list(self.safe_extensions)
        }
    
    def get_usage_examples(self) -> List[str]:
        """
        FileTool의 사용 예시를 반환합니다.
        
        Returns:
            List[str]: 사용 예시 목록
        """
        return [
            '{"action": "read", "path": "/Users/user/documents/memo.txt"}',
            '{"action": "write", "path": "/Users/user/notes.md", "content": "새로운 메모 내용"}',
            '{"action": "list", "path": "/Users/user/documents"}',
            '{"action": "exists", "path": "/Users/user/important.txt"}',
            '{"action": "info", "path": "/Users/user/data.json"}'
        ]
