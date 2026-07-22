from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from weather_agent.agent import SCOPE_REFUSAL, AgentResult, WeatherAgent, _city_is_mentioned
from weather_agent.errors import AgentProtocolError
from weather_agent.tracing import JsonlTracer
from weather_agent.weather import TemperatureReading


def _response(*, content: str | None = None, cities: list[str] | None = None) -> Any:
    tool_calls = []
    if cities is not None:
        tool_calls = [
            SimpleNamespace(
                id="call-1",
                function=SimpleNamespace(
                    name="get_current_temperatures",
                    arguments=json.dumps({"cities": cities}),
                ),
            )
        ]
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=tool_calls))]
    )


class FakeCompletions:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        return self.responses.pop(0)


class FakeLlm:
    def __init__(self, responses: list[Any]) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


class FakeWeather:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def get_current_temperatures(self, cities: list[str]):  # type: ignore[no-untyped-def]
        self.calls.append(cities)
        readings = [
            TemperatureReading(
                requested_city=city,
                resolved_city=city,
                temperature=21.5,
                unit="degrees Celsius",
                observed_at="2026-07-21T12:00",
                timezone="Europe/Budapest",
            )
            for city in cities
        ]
        return readings, []


def _agent(tmp_path: Path, llm: FakeLlm, weather: FakeWeather) -> WeatherAgent:
    return WeatherAgent(
        llm_client=llm,  # type: ignore[arg-type]
        weather_client=weather,
        tracer=JsonlTracer(tmp_path, run_id="test-run"),
        model="test-model",
    )


def test_tool_call_round_trip(tmp_path: Path) -> None:
    llm = FakeLlm(
        [
            _response(cities=["Budapest", "Paris"]),
            _response(
                content="The current temperature in Budapest and Paris is 21.5 degrees Celsius."
            ),
        ]
    )
    weather = FakeWeather()

    answer = _agent(tmp_path, llm, weather).run(
        "What is the current temperature in Budapest and Paris?"
    )

    assert "Budapest: 21.5 degrees Celsius" in answer
    assert "Paris: 21.5 degrees Celsius" in answer
    assert weather.calls == [["Budapest", "Paris"]]
    second_messages = llm.chat.completions.requests[1]["messages"]
    assert second_messages[-1]["role"] == "tool"
    assert "21.5" in second_messages[-1]["content"]


def test_empty_final_response_after_tool_call_is_retried(tmp_path: Path) -> None:
    llm = FakeLlm(
        [
            _response(cities=["Budapest"]),
            _response(content=""),
            _response(content="The current temperature in Budapest is 21.5 degrees Celsius."),
        ]
    )
    weather = FakeWeather()
    trace_dir = tmp_path / "trace"
    agent = WeatherAgent(
        llm_client=llm,  # type: ignore[arg-type]
        weather_client=weather,
        tracer=JsonlTracer(trace_dir, run_id="retry-run"),
        model="test-model",
    )

    answer = agent.run("What is the current temperature in Budapest?")

    assert "Budapest: 21.5 degrees Celsius" in answer
    assert len(llm.chat.completions.requests) == 3
    retry_messages = llm.chat.completions.requests[2]["messages"]
    assert retry_messages[-1]["role"] == "system"
    records = [
        json.loads(line)
        for line in (trace_dir / "retry-run.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert any(
        record["event"] == "reasoning_step" and record["data"].get("step") == "empty_response_retry"
        for record in records
    )


def test_out_of_scope_response_does_not_call_weather(tmp_path: Path) -> None:
    llm = FakeLlm([_response(content="Here is a poem about Budapest.")])
    weather = FakeWeather()

    answer = _agent(tmp_path, llm, weather).run("Write a poem about Budapest.")

    assert answer == SCOPE_REFUSAL
    assert weather.calls == []


def test_final_output_uses_only_validated_tool_data(tmp_path: Path) -> None:
    llm = FakeLlm(
        [
            _response(cities=["Budapest"]),
            _response(content="Humidity is 90 percent and rain is likely."),
        ]
    )
    weather = FakeWeather()

    result = _agent(tmp_path, llm, weather).run_result(
        "What is the current temperature in Budapest?"
    )

    assert isinstance(result, AgentResult)
    assert result.refused is False
    assert result.temperatures[0]["requested_city"] == "Budapest"
    assert "Budapest: 21.5 degrees Celsius" in result.answer
    assert "humidity" not in result.answer.casefold()
    assert "rain" not in result.answer.casefold()


def test_unmentioned_tool_city_is_rejected_before_network(tmp_path: Path) -> None:
    llm = FakeLlm(
        [
            _response(cities=["Paris"]),
            _response(content="I cannot complete that request."),
        ]
    )
    weather = FakeWeather()

    _agent(tmp_path, llm, weather).run("What is the temperature in Budapest?")

    assert weather.calls == []
    second_messages = llm.chat.completions.requests[1]["messages"]
    assert "not found in the user request" in second_messages[-1]["content"]


def test_city_binding_accepts_explicit_city_names() -> None:
    assert _city_is_mentioned("Budapest", "How warm is Budapest?")
    assert _city_is_mentioned("Paris", "What is the temperature in Paris?")
    assert _city_is_mentioned("New York", "How warm is New York right now?")
    assert not _city_is_mentioned("Paris", "How warm is Budapest?")


def test_empty_question_is_rejected(tmp_path: Path) -> None:
    trace_dir = tmp_path / "empty"
    tracer = JsonlTracer(trace_dir, run_id="empty-run")
    agent = WeatherAgent(
        llm_client=FakeLlm([]),  # type: ignore[arg-type]
        weather_client=FakeWeather(),
        tracer=tracer,
        model="test-model",
    )

    with pytest.raises(AgentProtocolError, match="cannot be empty"):
        agent.run("  ")

    records = [json.loads(line) for line in tracer.path.read_text(encoding="utf-8").splitlines()]
    assert [record["event"] for record in records] == ["run_started", "run_failed"]


def test_model_response_without_choices_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(AgentProtocolError):
        _agent(tmp_path, FakeLlm([SimpleNamespace(choices=[])]), FakeWeather()).run(
            "How warm is Budapest?"
        )
