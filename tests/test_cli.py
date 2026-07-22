from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from weather_agent import cli
from weather_agent.agent import AgentResult
from weather_agent.cli import build_parser
from weather_agent.config import Settings
from weather_agent.errors import ConfigurationError, WeatherServiceError


def test_cli_help_configuration() -> None:
    args = build_parser().parse_args(
        ["--trace", "--ui-port", "9123", "How warm is Budapest right now?"]
    )

    assert args.trace is True
    assert args.ui_port == 9123
    assert args.question == ["How warm is Budapest right now?"]


def test_main_starts_loopback_ui_without_reading_a_question(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = Settings(api_key="key")
    captured: dict[str, object] = {}

    def fake_serve_ui(**kwargs: object) -> int:
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(cli.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(cli, "serve_ui", fake_serve_ui)

    assert (
        cli.main(["--ui", "--ui-port", "9123", "--no-browser", "--trace-dir", str(tmp_path)]) == 0
    )
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 9123
    assert captured["trace_dir"] == tmp_path
    assert captured["open_browser"] is False
    assert callable(captured["question_runner"])


def test_ui_question_runner_returns_answer_and_safe_trace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = Settings(api_key="key")

    def fake_run_agent(**kwargs: object) -> AgentResult:
        tracer = kwargs["tracer"]
        assert isinstance(tracer, cli.JsonlTracer)
        tracer.emit("run_started", summary="Agent run started.")
        tracer.emit("run_finished", summary="Agent run completed.", refused=False)
        return AgentResult(
            answer="Budapest: 21.0 degrees Celsius",
            refused=False,
            temperatures=({"requested_city": "Budapest", "temperature": 21.0},),
            errors=(),
        )

    monkeypatch.setattr(cli, "_run_agent", fake_run_agent)
    runner = cli._ui_question_runner(
        settings=settings,
        trace_dir=tmp_path,
        model=settings.model,
        base_url=None,
    )

    payload, status = runner("What is the current temperature in Budapest?")

    assert status == 200
    assert payload["status"] == "completed"
    assert payload["events"][-1]["event"] == "run_finished"
    assert "trace" not in payload
    assert len(list(tmp_path.glob("*.jsonl"))) == 1


def test_ui_question_runner_records_expected_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = Settings(api_key="key")

    def fail(**_: object) -> AgentResult:
        raise WeatherServiceError("Weather data is temporarily unavailable.")

    monkeypatch.setattr(cli, "_run_agent", fail)
    runner = cli._ui_question_runner(
        settings=settings,
        trace_dir=tmp_path,
        model=settings.model,
        base_url=None,
    )

    payload, status = runner("What is the current temperature in Budapest?")

    assert status == 422
    assert payload["error"] == "Weather data is temporarily unavailable."
    assert payload["events"][-1]["event"] == "run_failed"


@pytest.mark.parametrize("base_url", [None, "http://provider.test/v1"])
def test_main_wires_dependencies_and_closes_weather(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    base_url: str | None,
) -> None:
    settings = Settings(api_key="key", base_url=base_url)
    sdk_calls: list[dict[str, object]] = []

    class StubWeather:
        closed = False

        def close(self) -> None:
            self.closed = True

    weather = StubWeather()

    class StubAgent:
        def __init__(self, **_: object) -> None:
            pass

        def run_result(self, question: str) -> AgentResult:
            assert question == "How warm is Budapest right now?"
            return AgentResult(
                answer="The current temperature in Budapest is 21 degrees Celsius.",
                refused=False,
                temperatures=(
                    {
                        "requested_city": "Budapest",
                        "resolved_city": "Budapest, Hungary",
                        "temperature": 21.0,
                        "unit": "degrees Celsius",
                        "observed_at": "2026-07-22T12:00",
                        "timezone": "Europe/Budapest",
                    },
                ),
                errors=(),
            )

    monkeypatch.setattr(cli.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(
        cli,
        "OpenAI",
        lambda **kwargs: sdk_calls.append(kwargs) or SimpleNamespace(),
    )
    monkeypatch.setattr(cli, "OpenMeteoClient", lambda **_: weather)
    monkeypatch.setattr(cli, "WeatherAgent", StubAgent)

    exit_code = cli.main(["--trace-dir", str(tmp_path), "How warm is Budapest right now?"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "21 degrees Celsius" in captured.out
    assert "Trace:" in captured.err
    assert weather.closed is True
    assert sdk_calls[0].get("base_url") == base_url


def test_main_emits_machine_readable_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = Settings(api_key="key")

    class StubWeather:
        def close(self) -> None:
            pass

    class StubAgent:
        def __init__(self, **_: object) -> None:
            pass

        def run_result(self, _: str) -> AgentResult:
            return AgentResult(
                answer="Budapest: 21.0 degrees Celsius",
                refused=False,
                temperatures=({"requested_city": "Budapest", "temperature": 21.0},),
                errors=(),
            )

    monkeypatch.setattr(cli.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(cli, "OpenAI", lambda **_: SimpleNamespace())
    monkeypatch.setattr(cli, "OpenMeteoClient", lambda **_: StubWeather())
    monkeypatch.setattr(cli, "WeatherAgent", StubAgent)

    assert cli.main(["--json", "--trace-dir", str(tmp_path), "How warm is Budapest?"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "completed"
    assert payload["temperatures"][0]["temperature"] == 21.0
    assert payload["run_id"]
    assert payload["trace"].endswith(".jsonl")


def test_main_shows_text_trace_without_provider_configuration(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    trace_path = tmp_path / "viewer.jsonl"
    trace_path.write_text(
        json.dumps(
            {
                "timestamp": "2026-07-22T08:00:00+00:00",
                "elapsed_ms": 2.5,
                "run_id": "viewer",
                "sequence": 1,
                "event": "run_finished",
                "data": {"summary": "Agent run completed."},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["--trace-dir", str(tmp_path), "--show-trace", "latest"]) == 0
    assert "Trace viewer" in capsys.readouterr().out


def test_main_reports_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail() -> Settings:
        raise ConfigurationError("bad config")

    monkeypatch.setattr(cli.Settings, "from_env", fail)

    assert cli.main(["--trace-dir", str(tmp_path), "question"]) == 2
    assert "bad config" in capsys.readouterr().err
    traces = list(tmp_path.glob("*.jsonl"))
    assert len(traces) == 1
    records = [json.loads(line) for line in traces[0].read_text(encoding="utf-8").splitlines()]
    assert records[-1]["event"] == "run_failed"
