from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from weather_agent.errors import TraceViewerError
from weather_agent.trace_viewer import (
    format_text_trace,
    load_trace,
    resolve_trace_path,
)


def _write_trace(path: Path, run_id: str = "viewer-run") -> None:
    records = [
        {
            "timestamp": "2026-07-22T08:00:00+00:00",
            "elapsed_ms": 0.1,
            "run_id": run_id,
            "sequence": 1,
            "event": "run_started",
            "data": {"summary": "Agent run started.", "question": "How warm is Budapest?"},
        },
        {
            "timestamp": "2026-07-22T08:00:01+00:00",
            "elapsed_ms": 1000.0,
            "run_id": run_id,
            "sequence": 2,
            "event": "tool_call_completed",
            "data": {
                "summary": "Current temperature resolved.",
                "result": {
                    "temperatures": [
                        {
                            "resolved_city": "Budapest, Hungary",
                            "temperature": 21.5,
                            "unit": "degrees Celsius",
                        }
                    ],
                    "errors": [],
                },
            },
        },
        {
            "timestamp": "2026-07-22T08:00:02+00:00",
            "elapsed_ms": 2000.0,
            "run_id": run_id,
            "sequence": 3,
            "event": "run_finished",
            "data": {"summary": "Agent run completed.", "answer": "Budapest: 21.5"},
        },
    ]
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )


def test_trace_viewer_resolves_latest_and_formats_text(tmp_path: Path) -> None:
    older = tmp_path / "older.jsonl"
    latest = tmp_path / "latest.jsonl"
    _write_trace(older, "older")
    _write_trace(latest, "latest")
    os.utime(older, (1, 1))
    os.utime(latest, (2, 2))

    resolved = resolve_trace_path(tmp_path, "latest")
    records = load_trace(resolved)
    text = format_text_trace(records)

    assert resolved == latest
    assert "Trace latest" in text
    assert "TOOL CALL COMPLETED" in text
    assert "Budapest, Hungary: 21.5 degrees Celsius" in text
    assert "Total elapsed: 2000.0 ms" in text


def test_trace_viewer_resolves_run_id_and_explicit_path(tmp_path: Path) -> None:
    trace_path = tmp_path / "known.jsonl"
    _write_trace(trace_path)

    assert resolve_trace_path(tmp_path, "known") == trace_path
    assert resolve_trace_path(tmp_path, str(trace_path)) == trace_path


def test_trace_viewer_reports_missing_empty_and_invalid_traces(tmp_path: Path) -> None:
    with pytest.raises(TraceViewerError, match="No trace files"):
        resolve_trace_path(tmp_path, "latest")
    with pytest.raises(TraceViewerError, match="not found"):
        resolve_trace_path(tmp_path, "missing")

    empty = tmp_path / "empty.jsonl"
    empty.touch()
    with pytest.raises(TraceViewerError, match="empty"):
        load_trace(empty)

    invalid = tmp_path / "invalid.jsonl"
    invalid.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(TraceViewerError, match="Could not read"):
        load_trace(invalid)

    wrong_shape = tmp_path / "wrong-shape.jsonl"
    wrong_shape.write_text("[]\n", encoding="utf-8")
    with pytest.raises(TraceViewerError, match="Invalid trace record"):
        load_trace(wrong_shape)
