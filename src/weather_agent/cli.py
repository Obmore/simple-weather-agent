"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from openai import OpenAI

from weather_agent.agent import LlmClientProtocol, WeatherAgent
from weather_agent.config import Settings
from weather_agent.errors import WeatherAgentError
from weather_agent.tracing import JsonlTracer
from weather_agent.weather import OpenMeteoClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="temperature-agent",
        description=("Answer only current-temperature questions for explicitly named cities."),
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="Question to answer. If omitted, the program prompts once on stdin.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Mirror structured trace events to stderr (JSONL is always written).",
    )
    parser.add_argument("--trace-dir", type=Path, help="Override the JSONL trace directory.")
    parser.add_argument("--model", help="Override OPENAI_MODEL for this run.")
    parser.add_argument("--base-url", help="Override OPENAI_BASE_URL for this run.")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    return parser


def _read_question(parts: list[str]) -> str:
    if parts:
        return " ".join(parts).strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return input("Question: ").strip()


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tracer: JsonlTracer | None = None
    weather_client: OpenMeteoClient | None = None
    try:
        settings = Settings.from_env()
        trace_dir = args.trace_dir or settings.trace_dir
        tracer = JsonlTracer(trace_dir, console=args.trace)
        model = args.model or settings.model
        base_url = args.base_url or settings.base_url
        question = _read_question(args.question)

        if base_url:
            sdk_client = OpenAI(
                api_key=settings.api_key,
                base_url=base_url,
                timeout=settings.request_timeout_seconds,
                max_retries=2,
            )
        else:
            sdk_client = OpenAI(
                api_key=settings.api_key,
                timeout=settings.request_timeout_seconds,
                max_retries=2,
            )
        llm_client = cast(LlmClientProtocol, sdk_client)

        weather_client = OpenMeteoClient(
            geocoding_language=settings.geocoding_language,
            geocoding_url=settings.geocoding_url,
            forecast_url=settings.forecast_url,
            timeout_seconds=settings.request_timeout_seconds,
        )
        agent = WeatherAgent(
            llm_client=llm_client,
            weather_client=weather_client,
            tracer=tracer,
            model=model,
            max_rounds=settings.max_agent_rounds,
            max_cities=settings.max_cities,
        )
        answer = agent.run(question)
        print(answer)
        print(f"Trace: {tracer.path.resolve()}", file=sys.stderr)
        return 0
    except WeatherAgentError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        if tracer is not None:
            print(f"Trace: {tracer.path.resolve()}", file=sys.stderr)
        return 2
    except Exception as exc:
        if tracer is not None:
            tracer.emit(
                "run_failed",
                summary="Unhandled application error.",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            print(f"Trace: {tracer.path.resolve()}", file=sys.stderr)
        print("Error: the service is temporarily unavailable.", file=sys.stderr)
        return 1
    finally:
        if weather_client is not None:
            weather_client.close()
