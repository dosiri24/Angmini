"""
이 모듈은 프로젝트 전반에서 사용될 커스텀 예외 클래스를 정의합니다.
각 예외는 특정 도메인(AI 엔진, 도구 등)에서 발생하는 오류를 명확하게 나타냅니다.
"""

# Rule 2: Explicit Failure Handling
# 기본 Exception을 상속받는 최상위 커스텀 예외를 정의하여,
# 프로젝트에서 발생하는 모든 예측 가능한 오류를 하나의 타입으로 묶어 관리할 수 있습니다.
# 이를 통해 포괄적인 예외 처리 블록을 만들 수 있습니다.
class AngminiError(Exception):
    """프로젝트의 모든 커스텀 예외의 기본 클래스입니다."""
    pass

class EngineError(AngminiError):
    """AI 엔진(ReAct 등) 내부에서 오류가 발생했을 때 사용되는 예외입니다."""
    pass

class ToolError(AngminiError):
    """도구(Tool)를 실행하는 과정에서 오류가 발생했을 때 사용되는 예외입니다."""
    pass

class LLMError(AngminiError):
    """LLM API 호출 또는 응답 처리 중 오류가 발생했을 때 사용되는 예외입니다."""
    pass

class ConfigurationError(AngminiError):
    """프로젝트 설정 (예: .env 파일)에 문제가 있을 때 사용되는 예외입니다."""
    pass
