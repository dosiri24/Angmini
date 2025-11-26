"""
환경변수 로드 및 설정 관리 모듈.

Why: 환경변수를 중앙 집중화하여 관리하고, 필수 값 검증을 통해
런타임 에러를 방지한다.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


def load_dotenv(env_path: Optional[Path] = None) -> None:
    """
    .env 파일을 읽어 환경변수로 로드한다.

    Why: python-dotenv 의존성 없이 간단하게 .env 파일을 파싱한다.
    외부 라이브러리 최소화 원칙.
    """
    if env_path is None:
        # 현재 파일 기준으로 .env 찾기
        env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 빈 줄이나 주석 무시
            if not line or line.startswith("#"):
                continue
            # KEY=VALUE 형식 파싱
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # 이미 설정된 환경변수는 덮어쓰지 않음
                if key and key not in os.environ:
                    os.environ[key] = value


@dataclass(frozen=True)
class Config:
    """
    애플리케이션 설정을 담는 불변 데이터 클래스.

    Why: frozen=True로 런타임 중 설정 변경을 방지하여 예측 가능성 확보.
    """
    gemini_api_key: str
    discord_bot_token: Optional[str]
    discord_channel_id: Optional[str]
    database_path: str
    log_level: str

    # Gemini 모델 설정
    gemini_flash_model: str = "gemini-2.0-flash"  # 빠른 응답용
    gemini_pro_model: str = "gemini-2.0-flash-thinking-exp"  # 복잡한 추론용 (실험적)

    # Agent 설정
    max_react_iterations: int = 5  # ReAct 무한루프 방지
    conversation_memory_size: int = 10  # 최근 N턴 유지


class ConfigError(Exception):
    """설정 관련 에러."""
    pass


def get_config() -> Config:
    """
    환경변수에서 Config 객체를 생성한다.

    Why: 팩토리 함수로 분리하여 테스트 시 환경변수 모킹이 용이하도록 함.

    Raises:
        ConfigError: 필수 환경변수가 누락된 경우
    """
    # .env 파일 로드 (아직 로드되지 않은 경우)
    load_dotenv()

    # 필수 환경변수 검증
    gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gemini_api_key:
        raise ConfigError(
            "GEMINI_API_KEY 환경변수가 설정되지 않았습니다. "
            ".env 파일을 확인하세요."
        )

    return Config(
        gemini_api_key=gemini_api_key,
        discord_bot_token=os.environ.get("DISCORD_BOT_TOKEN", "").strip() or None,
        discord_channel_id=os.environ.get("DISCORD_CHANNEL_ID", "").strip() or None,
        database_path=os.environ.get("DATABASE_PATH", "./schedules.db").strip(),
        log_level=os.environ.get("LOG_LEVEL", "INFO").strip().upper(),
    )


# 모듈 레벨 싱글톤 (lazy initialization)
_config: Optional[Config] = None


def config() -> Config:
    """
    Config 싱글톤을 반환한다.

    Why: 매번 환경변수를 파싱하지 않고 캐싱하여 성능 최적화.
    """
    global _config
    if _config is None:
        _config = get_config()
    return _config


def reset_config() -> None:
    """
    Config 싱글톤을 리셋한다.

    Why: 테스트 시 환경변수 변경 후 재로드가 필요할 때 사용.
    """
    global _config
    _config = None
