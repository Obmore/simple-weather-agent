from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from weather_agent import cli
from weather_agent.cli import build_parser
from weather_agent.config import Settings
from weather_agent.errors import ConfigurationError


def test_cli_help_configuration() -> None:
    args = build_parser().parse_args(["--trace", "How warm is Budapest right now?"])

    assert args.trace is True
    assert args.question == ["How warm is Budapest right now?"]


@pytest.mark.parametrize("base_url", [None, "http://provider.test/v1"])
def test_main_wires_dependencies_and_closes_weather(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    base_url: str | None,
) -> None:
    settings = Settings(api_key="key", base_url=base_url, trace_dir=tmp_path)
    sdk_calls: list[dict[str, object]] = []

    class StubWeather:
        closed = False

        def close(self) -> None:
            self.closed = True

    weather = StubWeather()

    class StubAgent:
        def __init__(self, **_: object) -> None:
            pass

        def run(self, question: str) -> str:
            assert question == "How warm is Budapest right now?"
            return "The current temperature in Budapest is 21 degrees Celsius."

    monkeypatch.setattr(cli.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(
        cli,
        "OpenAI",
        lambda **kwargs: sdk_calls.append(kwargs) or SimpleNamespace(),
    )
    monkeypatch.setattr(cli, "OpenMeteoClient", lambda **_: weather)
    monkeypatch.setattr(cli, "WeatherAgent", StubAgent)

    exit_code = cli.main(["How warm is Budapest right now?"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "21 degrees Celsius" in captured.out
    assert "Trace:" in captured.err
    assert weather.closed is True
    assert sdk_calls[0].get("base_url") == base_url


def test_main_reports_configuration_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail() -> Settings:
        raise ConfigurationError("bad config")

    monkeypatch.setattr(cli.Settings, "from_env", fail)

    assert cli.main(["question"]) == 2
    assert "bad config" in capsys.readouterr().err
