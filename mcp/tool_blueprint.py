"""
Tool Blueprint 모듈: 모든 도구의 기반이 되는 추상 클래스와 데이터 구조를 정의합니다.

이 모듈은 MCP(Model Context Protocol) 표준을 기반으로 하여
다양한 도구들이 일관된 인터페이스를 통해 동작할 수 있도록 설계되었습니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import json
import time
from ai.core.logger import logger


class ToolResultStatus(Enum):
    """도구 실행 결과의 상태를 나타내는 열거형입니다."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    PARTIAL = "partial"  # 부분적 성공 (일부 데이터만 가져온 경우 등)


@dataclass
class ToolResult:
    """
    도구 실행 결과를 표현하는 데이터 클래스입니다.
    
    이 클래스는 ReAct 엔진이 도구의 실행 결과를 일관되게 처리할 수 있도록
    표준화된 인터페이스를 제공합니다.
    
    Attributes:
        status (ToolResultStatus): 실행 결과 상태
        content (str): 사용자에게 표시될 주요 결과 내용
        data (Optional[Dict[str, Any]]): 추가 구조화된 데이터
        error_message (Optional[str]): 오류 발생 시 상세 메시지
        execution_time (float): 실행 소요 시간 (초)
        metadata (Optional[Dict[str, Any]]): 실행 관련 메타데이터
    """
    status: ToolResultStatus
    content: str
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    
    def is_success(self) -> bool:
        """실행이 성공했는지 확인합니다."""
        return self.status == ToolResultStatus.SUCCESS
    
    def is_error(self) -> bool:
        """실행 중 오류가 발생했는지 확인합니다."""
        return self.status == ToolResultStatus.ERROR
    
    def to_observation(self) -> str:
        """
        ReAct 패턴의 Observation으로 사용할 문자열을 생성합니다.
        
        Returns:
            str: AI가 이해할 수 있는 형태의 관찰 결과
        """
        if self.is_success():
            return f"도구 실행 성공: {self.content}"
        elif self.is_error():
            return f"도구 실행 오류: {self.error_message or self.content}"
        else:
            return f"도구 실행 상태 ({self.status.value}): {self.content}"
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 형태로 변환합니다."""
        return {
            "status": self.status.value,
            "content": self.content,
            "data": self.data,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }


class ToolBlueprint(ABC):
    """
    모든 도구가 상속받아야 하는 추상 기본 클래스입니다.
    
    이 클래스는 다음과 같은 설계 원칙을 따릅니다:
    - Rule 1: Design for Extensibility - 새로운 도구를 쉽게 추가할 수 있도록 설계
    - Rule 2: Explicit Failure Handling - 모든 오류를 명시적으로 처리
    - Rule 4: Clear and Detailed Comments - 각 메서드의 역할과 사용법을 명확히 문서화
    """
    
    def __init__(self, name: str, description: str):
        """
        도구 인스턴스를 초기화합니다.
        
        Args:
            name (str): 도구의 고유 이름 (AI가 Action에서 사용할 이름)
            description (str): 도구의 기능과 사용법에 대한 설명
        """
        self.name = name
        self.description = description
        self._execution_count = 0
        self._total_execution_time = 0.0
        
        logger.info(f"도구 초기화: {self.name}")
    
    @abstractmethod
    def execute(self, action_input: str) -> ToolResult:
        """
        도구의 핵심 기능을 실행합니다.
        
        Args:
            action_input (str): ReAct 패턴에서 "Action Input"으로 전달되는 입력값
            
        Returns:
            ToolResult: 실행 결과를 담은 객체
            
        Raises:
            NotImplementedError: 하위 클래스에서 반드시 구현해야 함
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        도구의 스키마 정보를 반환합니다.
        
        이 메서드는 AI가 도구를 올바르게 사용할 수 있도록
        입력 형식과 예시를 제공합니다.
        
        Returns:
            Dict[str, Any]: 도구의 스키마 정보
            
        Example:
            {
                "name": "file_read",
                "description": "파일의 내용을 읽어옵니다",
                "parameters": {
                    "file_path": {
                        "type": "string",
                        "description": "읽을 파일의 경로",
                        "required": True
                    }
                },
                "examples": [
                    "data/example.txt",
                    "/Users/user/document.md"
                ]
            }
        """
        pass
    
    def execute_safe(self, action_input: str) -> ToolResult:
        """
        안전한 실행을 위한 래퍼 메서드입니다.
        
        이 메서드는 다음과 같은 기능을 제공합니다:
        - 실행 시간 측정
        - 예외 처리 및 로깅
        - 실행 통계 업데이트
        
        Args:
            action_input (str): 도구에 전달할 입력값
            
        Returns:
            ToolResult: 실행 결과 (오류 발생 시에도 ToolResult 객체 반환)
        """
        start_time = time.time()
        self._execution_count += 1
        
        try:
            logger.debug(f"도구 '{self.name}' 실행 시작 - 입력: {action_input[:100]}...")
            
            result = self.execute(action_input)
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            self._total_execution_time += execution_time
            
            logger.debug(f"도구 '{self.name}' 실행 완료 - 소요시간: {execution_time:.2f}초")
            return result
            
        except Exception as e:
            # Rule 2: Explicit Failure Handling
            # 도구 실행 중 발생한 모든 예외를 ToolResult로 변환하여
            # 상위 시스템이 일관되게 처리할 수 있도록 합니다.
            execution_time = time.time() - start_time
            self._total_execution_time += execution_time
            
            logger.error(f"도구 '{self.name}' 실행 실패: {str(e)}")
            
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content=f"도구 실행 중 오류가 발생했습니다",
                error_message=str(e),
                execution_time=execution_time,
                metadata={"tool_name": self.name, "input": action_input}
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        도구의 실행 통계를 반환합니다.
        
        Returns:
            Dict[str, Any]: 실행 횟수, 총 실행 시간, 평균 실행 시간 등
        """
        avg_time = (self._total_execution_time / self._execution_count 
                   if self._execution_count > 0 else 0.0)
        
        return {
            "name": self.name,
            "execution_count": self._execution_count,
            "total_execution_time": self._total_execution_time,
            "average_execution_time": avg_time
        }
    
    def validate_input(self, action_input: str) -> bool:
        """
        입력값의 유효성을 검사합니다.
        
        기본 구현은 항상 True를 반환하며, 필요에 따라 하위 클래스에서
        오버라이드하여 구체적인 검증 로직을 구현할 수 있습니다.
        
        Args:
            action_input (str): 검증할 입력값
            
        Returns:
            bool: 입력값이 유효한 경우 True
        """
        # Rule 4: Clear and Detailed Comments
        # 기본적으로는 모든 입력을 허용하지만, 하위 클래스에서
        # 구체적인 검증 로직을 구현할 수 있도록 확장 포인트를 제공합니다.
        return True
    
    def get_usage_examples(self) -> List[str]:
        """
        도구 사용 예시를 반환합니다.
        
        AI가 도구를 올바르게 사용할 수 있도록 구체적인 예시를 제공합니다.
        하위 클래스에서 오버라이드하여 구체적인 예시를 제공해야 합니다.
        
        Returns:
            List[str]: 사용 예시 목록
        """
        return [
            f"기본 사용 예시: {self.name}을 위한 예시가 구현되지 않았습니다."
        ]
    
    def __str__(self) -> str:
        """도구의 문자열 표현을 반환합니다."""
        return f"{self.name}: {self.description}"
    
    def __repr__(self) -> str:
        """도구의 개발자용 문자열 표현을 반환합니다."""
        return f"ToolBlueprint(name='{self.name}', executions={self._execution_count})"
