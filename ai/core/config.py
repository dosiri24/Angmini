"""Configuration loader for the Personal AI Assistant."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Optional

from dotenv import load_dotenv

from .exceptions import ConfigError


def _coerce_optional(value: Optional[str]) -> Optional[str]:
    """Return stripped value or ``None`` when the input is empty."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration derived from environment variables."""

    default_interface: str
    discord_bot_token: Optional[str]
    gemini_api_key: Optional[str]
    gemini_model: str
    log_level: str

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
            load_dotenv(dotenv_path=env_file, override=False)
        else:
            load_dotenv(override=False)

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

        gemini_model = _coerce_optional(os.getenv("GEMINI_MODEL")) or "models/gemini-1.5-pro"

        return cls(
            default_interface=interface_value,
            discord_bot_token=_coerce_optional(os.getenv("DISCORD_BOT_TOKEN")),
            gemini_api_key=_coerce_optional(os.getenv("GEMINI_API_KEY")),
            gemini_model=gemini_model,
            log_level=log_level,
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
