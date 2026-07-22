"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from dotenv import load_dotenv
from openai import OpenAI

from weather_agent.agent import AgentResult, LlmClientProtocol, WeatherAgent
from weather_agent.config import Settings
from weather_agent.errors import WeatherAgentError
from weather_agent.trace_viewer import (
    format_text_trace,
    load_trace,
    resolve_trace_path,
    write_html_report,
)
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
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Write a structured machine-readable result to stdout.",
    )
    parser.add_argument(
        "--show-trace",
        nargs="?",
        const="latest",
        metavar="TRACE",
        help="Show a readable trace timeline by run ID, path, or 'latest'.",
    )
    parser.add_argument(
        "--html",
        nargs="?",
        const=Path("trace-report.html"),
        type=Path,
        metavar="OUTPUT",
        help="With --show-trace, write a self-contained HTML dashboard.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    return parser


def _read_question(parts: list[str]) -> str:
    if parts:
        return " ".join(parts).strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return input("Question: ").strip()


def _json_result(result: AgentResult, tracer: JsonlTracer) -> dict[str, object]:
    return {
        "status": "refused" if result.refused else "completed",
        **result.to_dict(),
        "run_id": tracer.run_id,
        "trace": str(tracer.path.resolve()),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv(dotenv_path=".env", override=False)
    trace_dir = args.trace_dir or Path(os.getenv("TRACE_DIR", "traces")).expanduser()

    if args.show_trace:
        try:
            trace_path = resolve_trace_path(trace_dir, args.show_trace)
            records = load_trace(trace_path)
            if args.html:
                report_path = write_html_report(records, args.html)
                print(f"HTML trace dashboard: {report_path}")
            else:
                print(format_text_trace(records))
            return 0
        except WeatherAgentError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    if args.html:
        print("Error: --html requires --show-trace.", file=sys.stderr)
        return 2

    tracer: JsonlTracer | None = None
    weather_client: OpenMeteoClient | None = None
    try:
        tracer = JsonlTracer(trace_dir, console=args.trace)
        settings = Settings.from_env()
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
        result = agent.run_result(question)
        if args.json_output:
            print(json.dumps(_json_result(result, tracer), ensure_ascii=False))
        else:
            print(result.answer)
        print(f"Trace: {tracer.path.resolve()}", file=sys.stderr)
        return 0
    except WeatherAgentError as exc:
        if tracer is not None and not tracer.has_terminal_event:
            tracer.emit(
                "run_failed",
                summary="Application run failed.",
                error_type=type(exc).__name__,
                error=str(exc),
            )
        print(f"Error: {exc}", file=sys.stderr)
        if tracer is not None:
            print(f"Trace: {tracer.path.resolve()}", file=sys.stderr)
        return 2
    except Exception as exc:
        if tracer is not None and not tracer.has_terminal_event:
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
