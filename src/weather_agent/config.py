"""Environment-backed configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from weather_agent.errors import ConfigurationError


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number.") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero.")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero.")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings for the LLM, weather API, and tracing."""

    api_key: str
    model: str = "gpt-5.6-sol"
    base_url: str | None = None
    request_timeout_seconds: float = 20.0
    max_agent_rounds: int = 4
    max_cities: int = 10

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> Settings:
        """Load `.env` without overwriting variables already exported by the shell."""

        load_dotenv(dotenv_path=env_file, override=False)
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is missing. Copy .env.example to .env and set it. "
                "For local providers that do not authenticate, use a non-empty placeholder."
            )

        model = os.getenv("OPENAI_MODEL", "gpt-5.6-sol").strip()
        if not model:
            raise ConfigurationError("OPENAI_MODEL cannot be empty.")

        base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
        return cls(
            api_key=api_key,
            model=model,
            base_url=base_url,
            request_timeout_seconds=_positive_float("REQUEST_TIMEOUT_SECONDS", 20.0),
            max_agent_rounds=_positive_int("MAX_AGENT_ROUNDS", 4),
            max_cities=_positive_int("MAX_CITIES", 10),
        )
