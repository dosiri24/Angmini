"""
이 모듈은 프로젝트의 설정을 관리합니다.
.env 파일에서 환경 변수를 로드하고, 애플리케이션 전반에서 사용될 설정 값들을 속성으로 제공합니다.
"""
import os
from dotenv import load_dotenv

class Config:
    """
    설정 클래스는 .env 파일에서 환경 변수를 로드하고,
    필요한 설정 값들을 클래스 속성으로 정의합니다.
    """
    def __init__(self):
        """
        Config 클래스의 인스턴스를 초기화합니다.
        프로젝트 루트의 .env 파일을 찾아 환경 변수를 로드합니다.
        """
        # Rule 4: "why" not just "what"
        # .env 파일을 명시적으로 로드하여, 환경 변수가 설정되지 않았을 때
        # 발생하는 문제를 사전에 방지하고, 코드의 명확성을 높입니다.
        load_dotenv()

        # Rule 2: Explicit Failure Handling
        # API 키와 같은 필수 환경 변수가 설정되지 않은 경우,
        # 기본값으로 대체하지 않고 명시적으로 에러를 발생시켜
        # 설정 문제를 즉시 인지하고 해결하도록 유도합니다.
        self.google_api_key = self._get_required_env("GOOGLE_API_KEY")
        self.discord_token = self._get_required_env("DISCORD_TOKEN")
        self.notion_api_key = os.getenv("NOTION_API_KEY") # 선택적 값
        
        # 기본 인터페이스 설정 (선택적, 기본값: menu)
        self.default_interface = os.getenv("DEFAULT_INTERFACE", "menu").lower()
        
        # 유효한 인터페이스 값인지 검증
        valid_interfaces = ["cli", "discord", "menu"]
        if self.default_interface not in valid_interfaces:
            raise ValueError(f"DEFAULT_INTERFACE는 {', '.join(valid_interfaces)} 중 하나여야 합니다. 현재 값: {self.default_interface}")

    def _get_required_env(self, var_name: str) -> str:
        """
        필수 환경 변수를 가져옵니다. 변수가 설정되지 않은 경우, 설정 오류를 발생시킵니다.

        Args:
            var_name (str): 가져올 환경 변수의 이름

        Returns:
            str: 환경 변수의 값

        Raises:
            ValueError: 해당 환경 변수가 .env 파일에 설정되지 않았을 경우
        """
        value = os.getenv(var_name)
        if value is None:
            raise ValueError(f"'{var_name}' 환경 변수가 .env 파일에 설정되지 않았습니다. 프로그램을 실행하기 전에 설정을 완료해주세요.")
        return value

# 프로젝트 전역에서 사용될 단일 설정 인스턴스
# 이 인스턴스를 임포트하여 어디서든 동일한 설정 값을 참조할 수 있습니다.
config = Config()
