"""
config.py 테스트 모듈.

TDD: 환경변수 로드 및 검증 로직 테스트
"""

import os
import pytest
from pathlib import Path

from config import (
    load_dotenv,
    Config,
    ConfigError,
    get_config,
    config,
    reset_config,
)


class TestLoadDotenv:
    """load_dotenv 함수 테스트."""

    def test_load_dotenv_parses_key_value(self, tmp_path: Path):
        """KEY=VALUE 형식을 올바르게 파싱한다."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_KEY=test_value\n")

        # 기존 환경변수 백업 및 제거
        original = os.environ.pop("TEST_KEY", None)

        try:
            load_dotenv(env_file)
            assert os.environ.get("TEST_KEY") == "test_value"
        finally:
            # 정리
            os.environ.pop("TEST_KEY", None)
            if original:
                os.environ["TEST_KEY"] = original

    def test_load_dotenv_ignores_comments(self, tmp_path: Path):
        """주석은 무시한다."""
        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\nVALID_KEY=valid_value\n")

        original = os.environ.pop("VALID_KEY", None)

        try:
            load_dotenv(env_file)
            assert os.environ.get("VALID_KEY") == "valid_value"
            assert "# This is a comment" not in os.environ
        finally:
            os.environ.pop("VALID_KEY", None)
            if original:
                os.environ["VALID_KEY"] = original

    def test_load_dotenv_ignores_empty_lines(self, tmp_path: Path):
        """빈 줄은 무시한다."""
        env_file = tmp_path / ".env"
        env_file.write_text("\n\nKEY=value\n\n")

        original = os.environ.pop("KEY", None)

        try:
            load_dotenv(env_file)
            assert os.environ.get("KEY") == "value"
        finally:
            os.environ.pop("KEY", None)
            if original:
                os.environ["KEY"] = original

    def test_load_dotenv_does_not_override_existing(self, tmp_path: Path):
        """override=False일 때 이미 설정된 환경변수는 덮어쓰지 않는다."""
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING_KEY=new_value\n")

        os.environ["EXISTING_KEY"] = "original_value"

        try:
            load_dotenv(env_file, override=False)
            assert os.environ.get("EXISTING_KEY") == "original_value"
        finally:
            os.environ.pop("EXISTING_KEY", None)

    def test_load_dotenv_override_true_overwrites_existing(self, tmp_path: Path):
        """override=True(기본값)일 때 기존 환경변수를 덮어쓴다."""
        env_file = tmp_path / ".env"
        env_file.write_text("OVERRIDE_KEY=new_value\n")

        os.environ["OVERRIDE_KEY"] = "original_value"

        try:
            load_dotenv(env_file, override=True)
            assert os.environ.get("OVERRIDE_KEY") == "new_value"
        finally:
            os.environ.pop("OVERRIDE_KEY", None)

    def test_load_dotenv_handles_missing_file(self, tmp_path: Path):
        """존재하지 않는 파일은 무시한다."""
        env_file = tmp_path / "nonexistent.env"
        # 에러 없이 실행되어야 함
        load_dotenv(env_file)


class TestConfig:
    """Config 데이터 클래스 테스트."""

    def test_config_is_immutable(self):
        """Config는 불변(frozen)이다."""
        cfg = Config(
            gemini_api_key="test_key",
            discord_bot_token=None,
            discord_channel_id=None,
            database_path="./test.db",
            log_level="INFO",
        )

        with pytest.raises(AttributeError):
            cfg.gemini_api_key = "new_key"  # type: ignore

    def test_config_has_default_values(self):
        """Config는 기본값을 가진다."""
        cfg = Config(
            gemini_api_key="test_key",
            discord_bot_token=None,
            discord_channel_id=None,
            database_path="./test.db",
            log_level="INFO",
        )

        assert cfg.gemini_flash_model == "gemini-flash-latest"
        assert cfg.max_react_iterations == 5
        assert cfg.conversation_memory_size == 10


class TestGetConfig:
    """get_config 함수 테스트."""

    def setup_method(self):
        """각 테스트 전에 싱글톤 리셋."""
        reset_config()

    def teardown_method(self):
        """각 테스트 후에 싱글톤 리셋."""
        reset_config()

    def test_get_config_raises_on_missing_api_key(self, monkeypatch):
        """GEMINI_API_KEY가 없으면 ConfigError 발생."""
        # load_dotenv를 no-op으로 대체하여 .env 파일 로드 방지
        import config as config_module
        monkeypatch.setattr(config_module, "load_dotenv", lambda *args, **kwargs: None)
        monkeypatch.setenv("GEMINI_API_KEY", "")

        with pytest.raises(ConfigError) as exc_info:
            get_config()

        assert "GEMINI_API_KEY" in str(exc_info.value)

    def test_get_config_loads_required_values(self, monkeypatch):
        """필수 환경변수를 올바르게 로드한다."""
        # load_dotenv를 no-op으로 대체하여 테스트 환경변수만 사용
        import config as config_module
        monkeypatch.setattr(config_module, "load_dotenv", lambda *args, **kwargs: None)
        monkeypatch.setenv("GEMINI_API_KEY", "test_api_key")
        monkeypatch.setenv("DATABASE_PATH", "./custom.db")
        monkeypatch.setenv("LOG_LEVEL", "debug")

        cfg = get_config()

        assert cfg.gemini_api_key == "test_api_key"
        assert cfg.database_path == "./custom.db"
        assert cfg.log_level == "DEBUG"  # 대문자로 변환

    def test_get_config_handles_optional_values(self, monkeypatch):
        """선택적 환경변수는 None으로 설정된다."""
        # load_dotenv를 no-op으로 대체하여 테스트 환경변수만 사용
        import config as config_module
        monkeypatch.setattr(config_module, "load_dotenv", lambda *args, **kwargs: None)
        monkeypatch.setenv("GEMINI_API_KEY", "test_api_key")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "")
        monkeypatch.setenv("DISCORD_CHANNEL_ID", "")

        cfg = get_config()

        assert cfg.discord_bot_token is None
        assert cfg.discord_channel_id is None


class TestConfigSingleton:
    """config() 싱글톤 함수 테스트."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_config_returns_same_instance(self, monkeypatch):
        """config()는 동일한 인스턴스를 반환한다."""
        # load_dotenv를 no-op으로 대체하여 테스트 환경변수만 사용
        import config as config_module
        monkeypatch.setattr(config_module, "load_dotenv", lambda *args, **kwargs: None)
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")

        cfg1 = config()
        cfg2 = config()

        assert cfg1 is cfg2

    def test_reset_config_clears_singleton(self, monkeypatch):
        """reset_config()은 싱글톤을 초기화한다."""
        # load_dotenv를 no-op으로 대체하여 테스트 환경변수만 사용
        import config as config_module
        monkeypatch.setattr(config_module, "load_dotenv", lambda *args, **kwargs: None)
        monkeypatch.setenv("GEMINI_API_KEY", "test_key_1")
        cfg1 = config()

        reset_config()
        monkeypatch.setenv("GEMINI_API_KEY", "test_key_2")
        cfg2 = config()

        assert cfg1 is not cfg2
        assert cfg2.gemini_api_key == "test_key_2"
