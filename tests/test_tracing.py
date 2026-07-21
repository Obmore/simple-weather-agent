from __future__ import annotations

import json
from pathlib import Path

from weather_agent.tracing import JsonlTracer


def test_tracer_writes_ordered_utf8_jsonl(tmp_path: Path) -> None:
    tracer = JsonlTracer(tmp_path, run_id="known-run")

    tracer.emit("run_started", summary="Current temperature lookup")
    tracer.emit("run_finished", answer="21 degrees Celsius")

    records = [json.loads(line) for line in tracer.path.read_text(encoding="utf-8").splitlines()]
    assert [record["sequence"] for record in records] == [1, 2]
    assert all(record["run_id"] == "known-run" for record in records)
    assert records[0]["data"]["summary"] == "Current temperature lookup"
