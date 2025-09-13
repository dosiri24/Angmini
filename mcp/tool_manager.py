"""
Tool Manager 모듈: 도구들을 등록하고 실행 요청을 라우팅하는 중앙 관리자입니다.

이 모듈은 다음과 같은 책임을 가집니다:
- 도구 등록 및 관리
- 도구 실행 요청 라우팅
- 도구 목록 및 스키마 정보 제공
- 도구 실행 통계 관리
"""

from typing import Dict, List, Optional, Any
from mcp.tool_blueprint import ToolBlueprint, ToolResult, ToolResultStatus
from ai.core.logger import logger
from ai.core.exceptions import ToolError
import json


class ToolManager:
    """
    도구 등록 및 실행을 관리하는 중앙 클래스입니다.
    
    이 클래스는 다음과 같은 설계 원칙을 따릅니다:
    - Rule 1: Design for Extensibility - 새로운 도구를 쉽게 추가할 수 있는 구조
    - Rule 2: Explicit Failure Handling - 모든 오류를 명시적으로 처리
    - Rule 3: Root Cause Resolution - 문제의 근본 원인을 해결하는 구조적 접근
    """
    
    def __init__(self):
        """ToolManager 인스턴스를 초기화합니다."""
        self._tools: Dict[str, ToolBlueprint] = {}
        self._tool_execution_history: List[Dict[str, Any]] = []
        
        logger.info("ToolManager 초기화 완료")
    
    def register_tool(self, tool: ToolBlueprint) -> bool:
        """
        새로운 도구를 등록합니다.
        
        Args:
            tool (ToolBlueprint): 등록할 도구 인스턴스
            
        Returns:
            bool: 등록 성공 시 True, 실패 시 False
            
        Raises:
            ToolError: 동일한 이름의 도구가 이미 등록된 경우
        """
        try:
            # Rule 2: Explicit Failure Handling
            # 동일한 이름의 도구가 이미 등록된 경우, 명시적으로 에러를 발생시켜
            # 개발자가 즉시 문제를 인지하고 해결할 수 있도록 합니다.
            if tool.name in self._tools:
                raise ToolError(
                    f"도구 '{tool.name}'이 이미 등록되어 있습니다. "
                    f"기존 도구를 먼저 해제하거나 다른 이름을 사용해주세요."
                )
            
            # 도구 등록
            self._tools[tool.name] = tool
            logger.info(f"도구 등록 완료: {tool.name} - {tool.description}")
            
            return True
            
        except Exception as e:
            logger.error(f"도구 등록 실패: {str(e)}")
            raise ToolError(f"도구 등록 중 오류가 발생했습니다: {str(e)}")
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        도구를 등록 해제합니다.
        
        Args:
            tool_name (str): 해제할 도구의 이름
            
        Returns:
            bool: 해제 성공 시 True, 도구가 존재하지 않으면 False
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"도구 등록 해제 완료: {tool_name}")
            return True
        else:
            logger.warning(f"등록 해제 요청된 도구를 찾을 수 없습니다: {tool_name}")
            return False
    
    def execute_tool(self, tool_name: str, action_input: str) -> ToolResult:
        """
        지정된 도구를 실행합니다.
        
        Args:
            tool_name (str): 실행할 도구의 이름
            action_input (str): 도구에 전달할 입력값
            
        Returns:
            ToolResult: 도구 실행 결과
            
        Raises:
            ToolError: 도구가 등록되지 않은 경우
        """
        try:
            # Rule 2: Explicit Failure Handling
            # 존재하지 않는 도구에 대한 실행 요청을 명시적으로 처리하여
            # 사용자가 즉시 문제를 인지할 수 있도록 합니다.
            if tool_name not in self._tools:
                available_tools = list(self._tools.keys())
                error_msg = (
                    f"도구 '{tool_name}'을 찾을 수 없습니다. "
                    f"사용 가능한 도구: {', '.join(available_tools) if available_tools else '없음'}"
                )
                logger.error(error_msg)
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    content=error_msg,
                    error_message=error_msg,
                    metadata={"requested_tool": tool_name, "available_tools": available_tools}
                )
            
            # 도구 실행
            tool = self._tools[tool_name]
            result = tool.execute_safe(action_input)
            
            # Rule 4: Clear and Detailed Comments
            # 실행 기록을 저장하여 디버깅 및 성능 분석에 활용할 수 있도록 합니다.
            # 이는 시스템의 동작을 추적하고 문제를 진단하는 데 중요합니다.
            execution_record = {
                "tool_name": tool_name,
                "action_input": action_input,
                "result_status": result.status.value,
                "execution_time": result.execution_time,
                "success": result.is_success()
            }
            self._tool_execution_history.append(execution_record)
            
            logger.debug(f"도구 실행 완료: {tool_name} (상태: {result.status.value})")
            return result
            
        except Exception as e:
            logger.error(f"도구 실행 중 예상치 못한 오류: {str(e)}")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                content=f"도구 실행 중 시스템 오류가 발생했습니다",
                error_message=str(e),
                metadata={"tool_name": tool_name, "input": action_input}
            )
    
    def get_available_tools(self) -> List[str]:
        """
        등록된 모든 도구의 이름 목록을 반환합니다.
        
        Returns:
            List[str]: 등록된 도구 이름 목록
        """
        return list(self._tools.keys())
    
    def get_tool_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        등록된 모든 도구의 스키마 정보를 반환합니다.
        
        Returns:
            Dict[str, Dict[str, Any]]: 도구 이름을 키로 하는 스키마 정보 딕셔너리
        """
        schemas = {}
        for tool_name, tool in self._tools.items():
            try:
                schemas[tool_name] = tool.get_schema()
            except Exception as e:
                logger.warning(f"도구 '{tool_name}'의 스키마 정보를 가져오는 중 오류: {str(e)}")
                schemas[tool_name] = {
                    "name": tool_name,
                    "description": tool.description,
                    "error": f"스키마 정보를 가져올 수 없습니다: {str(e)}"
                }
        
        return schemas
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        특정 도구의 상세 정보를 반환합니다.
        
        Args:
            tool_name (str): 정보를 조회할 도구 이름
            
        Returns:
            Optional[Dict[str, Any]]: 도구 정보 또는 None (도구가 존재하지 않는 경우)
        """
        if tool_name not in self._tools:
            return None
        
        tool = self._tools[tool_name]
        try:
            return {
                "name": tool.name,
                "description": tool.description,
                "schema": tool.get_schema(),
                "statistics": tool.get_statistics(),
                "usage_examples": tool.get_usage_examples()
            }
        except Exception as e:
            logger.warning(f"도구 '{tool_name}' 정보 조회 중 오류: {str(e)}")
            return {
                "name": tool.name,
                "description": tool.description,
                "error": str(e)
            }
    
    def get_tools_summary_for_ai(self) -> str:
        """
        AI가 사용할 수 있는 도구 목록을 문자열 형태로 반환합니다.
        
        이 메서드는 ReAct 엔진이 AI에게 사용 가능한 도구를 알려주기 위해 사용됩니다.
        
        Returns:
            str: AI가 이해할 수 있는 형태의 도구 목록 설명
        """
        if not self._tools:
            return "현재 사용 가능한 도구가 없습니다."
        
        tool_descriptions = []
        for tool_name, tool in self._tools.items():
            try:
                schema = tool.get_schema()
                examples = tool.get_usage_examples()
                
                description = f"**{tool_name}**: {tool.description}"
                if examples:
                    description += f"\n  예시: {examples[0]}"
                
                tool_descriptions.append(description)
            except Exception as e:
                logger.warning(f"도구 '{tool_name}' 설명 생성 중 오류: {str(e)}")
                tool_descriptions.append(f"**{tool_name}**: {tool.description}")
        
        return "\n".join(tool_descriptions)
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """
        전체 도구 실행 통계를 반환합니다.
        
        Returns:
            Dict[str, Any]: 실행 통계 정보
        """
        total_executions = len(self._tool_execution_history)
        successful_executions = sum(1 for record in self._tool_execution_history 
                                  if record["success"])
        
        # 도구별 통계
        tool_stats = {}
        for tool_name, tool in self._tools.items():
            tool_stats[tool_name] = tool.get_statistics()
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": (successful_executions / total_executions * 100 
                           if total_executions > 0 else 0.0),
            "registered_tools_count": len(self._tools),
            "tool_statistics": tool_stats
        }
    
    def clear_execution_history(self) -> int:
        """
        실행 기록을 초기화합니다.
        
        Returns:
            int: 삭제된 기록의 수
        """
        deleted_count = len(self._tool_execution_history)
        self._tool_execution_history.clear()
        logger.info(f"도구 실행 기록 초기화 완료: {deleted_count}개 기록 삭제")
        return deleted_count
    
    def validate_tool_action(self, tool_name: str, action_input: str) -> bool:
        """
        도구 실행 전에 입력값의 유효성을 검증합니다.
        
        Args:
            tool_name (str): 검증할 도구 이름
            action_input (str): 검증할 입력값
            
        Returns:
            bool: 유효한 경우 True, 그렇지 않으면 False
        """
        if tool_name not in self._tools:
            return False
        
        try:
            tool = self._tools[tool_name]
            return tool.validate_input(action_input)
        except Exception as e:
            logger.warning(f"도구 '{tool_name}' 입력 검증 중 오류: {str(e)}")
            return False
    
    def __len__(self) -> int:
        """등록된 도구의 수를 반환합니다."""
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        """도구가 등록되어 있는지 확인합니다."""
        return tool_name in self._tools
    
    def __str__(self) -> str:
        """ToolManager의 문자열 표현을 반환합니다."""
        tool_names = list(self._tools.keys())
        return f"ToolManager(도구 {len(tool_names)}개: {', '.join(tool_names)})"
