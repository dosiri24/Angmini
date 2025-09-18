"""Configuration loader for the Personal AI Assistant."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Optional

import logging

from dotenv import load_dotenv

from .exceptions import ConfigError


def _coerce_optional(value: Optional[str]) -> Optional[str]:
    """Return stripped value or ``None`` when the input is empty."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _normalise_gemini_model(value: Optional[str]) -> str:
    """Return a Gemini 모델 이름을 표준 형태로 정리합니다."""
    model = _coerce_optional(value) or "gemini-1.5-pro"
    if model.startswith("models/"):
        # google-generativeai 패키지는 접두어 없이 모델 이름을 기대합니다.
        model = model.split("/", 1)[1]
    return model


def _mask(value: Optional[str]) -> str:
    if not value:
        return "<empty>"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-4:]}"


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration derived from environment variables."""

    default_interface: str
    discord_bot_token: Optional[str]
    gemini_api_key: Optional[str]
    gemini_model: str
    log_level: str
    env_path: Optional[str] = field(default=None, repr=False)

    @classmethod
    def load(
        cls,
        env_file: Optional[Path | str] = None,
        *,
        supported_interfaces: Optional[Iterable[str]] = None,
        override_env: Optional[MutableMapping[str, str]] = None,
    ) -> "Config":
        """Load configuration from ``.env`` and the current environment."""
        if env_file is not None:
            env_path = Path(env_file)
        else:
            env_path = Path.cwd() / ".env"

        logger = logging.getLogger(__name__)
        logger.debug("Attempting to load environment variables", extra={"env_path": str(env_path)})

        env_path_str: Optional[str] = None

        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
            logger.debug(
                "Loaded .env file",
                extra={
                    "env_path": str(env_path),
                    "override": True,
                },
            )
            env_path_str = str(env_path)
        else:
            load_dotenv(override=True)
            logger.warning(
                "Specified .env file not found; falling back to default discovery",
                extra={"env_path": str(env_path)},
            )

        if override_env:
            for key, value in override_env.items():
                os.environ[key] = value

        raw_interface = os.getenv("DEFAULT_INTERFACE", "cli")
        if raw_interface is None:
            raise ConfigError("DEFAULT_INTERFACE environment variable is missing.")
        interface_value = raw_interface.strip()
        if not interface_value:
            raise ConfigError("DEFAULT_INTERFACE environment variable is empty.")

        if supported_interfaces:
            normalized_supported = {name.lower(): name for name in supported_interfaces}
            normalized_interface = interface_value.lower()
            if normalized_interface not in normalized_supported:
                supported_display = ", ".join(sorted(normalized_supported.values()))
                raise ConfigError(
                    f"Unsupported DEFAULT_INTERFACE '{interface_value}'. Supported interfaces: {supported_display}."
                )
            interface_value = normalized_supported[normalized_interface]
        else:
            interface_value = interface_value.lower()

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        raw_key = os.getenv("GEMINI_API_KEY")
        gemini_model = _normalise_gemini_model(os.getenv("GEMINI_MODEL"))
        logger.debug(
            "Environment variables resolved",
            extra={
                "gemini_api_key": _mask(raw_key),
                "gemini_model": gemini_model,
            },
        )

        return cls(
            default_interface=interface_value,
            discord_bot_token=_coerce_optional(os.getenv("DISCORD_BOT_TOKEN")),
            gemini_api_key=_coerce_optional(raw_key),
            gemini_model=gemini_model,
            log_level=log_level,
            env_path=env_path_str,
        )

    def as_dict(self) -> Mapping[str, Optional[str]]:
        """Expose configuration values for debugging or serialization."""
        return {
            "default_interface": self.default_interface,
            "discord_bot_token": self.discord_bot_token,
            "gemini_api_key": self.gemini_api_key,
            "gemini_model": self.gemini_model,
            "log_level": self.log_level,
        }
