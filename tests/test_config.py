from __future__ import annotations

from pathlib import Path

import pytest

from weather_agent.config import Settings
from weather_agent.errors import ConfigurationError


def test_settings_require_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        Settings.from_env(tmp_path / "missing.env")


def test_settings_read_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "local-model")
    monkeypatch.setenv("MAX_AGENT_ROUNDS", "7")

    settings = Settings.from_env(tmp_path / "missing.env")

    assert settings.api_key == "test-key"
    assert settings.model == "local-model"
    assert settings.max_agent_rounds == 7


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("REQUEST_TIMEOUT_SECONDS", "slow", "must be a number"),
        ("REQUEST_TIMEOUT_SECONDS", "0", "greater than zero"),
        ("MAX_AGENT_ROUNDS", "many", "must be an integer"),
        ("MAX_AGENT_ROUNDS", "-1", "greater than zero"),
    ],
)
def test_settings_validate_numeric_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
    value: str,
    message: str,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv(name, value)

    with pytest.raises(ConfigurationError, match=message):
        Settings.from_env(tmp_path / "missing.env")
