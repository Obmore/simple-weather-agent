"""Human-readable text view for JSONL traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from weather_agent.errors import TraceViewerError

TraceRecord = dict[str, Any]


def resolve_trace_path(trace_dir: Path, selector: str) -> Path:
    """Resolve `latest`, a run ID, or an explicit JSONL path."""

    if selector == "latest":
        candidates = list(trace_dir.glob("*.jsonl"))
        if not candidates:
            raise TraceViewerError(f"No trace files were found in {trace_dir}.")
        return max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))

    explicit = Path(selector).expanduser()
    if explicit.is_file():
        return explicit

    candidate = trace_dir / selector
    if candidate.suffix != ".jsonl":
        candidate = candidate.with_suffix(".jsonl")
    if not candidate.is_file():
        raise TraceViewerError(f"Trace file not found: {selector}")
    return candidate


def load_trace(path: Path) -> list[TraceRecord]:
    """Load and minimally validate an append-only JSONL trace."""

    records: list[TraceRecord] = []
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict) or not isinstance(record.get("data"), dict):
                raise TraceViewerError(f"Invalid trace record at line {line_number}.")
            records.append(record)
    except (OSError, json.JSONDecodeError) as exc:
        raise TraceViewerError(f"Could not read trace file: {path}") from exc
    if not records:
        raise TraceViewerError(f"Trace file is empty: {path}")
    return records


def _temperature_lines(record: TraceRecord) -> list[str]:
    data = record.get("data", {})
    result = data.get("result") if isinstance(data, dict) else None
    if not isinstance(result, dict):
        return []
    temperatures = result.get("temperatures")
    if not isinstance(temperatures, list):
        return []

    lines: list[str] = []
    for reading in temperatures:
        if not isinstance(reading, dict):
            continue
        city = reading.get("resolved_city") or reading.get("requested_city") or "Unknown city"
        temperature = reading.get("temperature", "unknown")
        unit = reading.get("unit", "")
        lines.append(f"{city}: {temperature} {unit}".rstrip())
    return lines


def format_text_trace(records: list[TraceRecord]) -> str:
    """Format trace records as a compact terminal timeline."""

    run_id = str(records[0].get("run_id", "unknown"))
    total_ms = float(records[-1].get("elapsed_ms", 0.0))
    lines = [f"Trace {run_id}", f"Total elapsed: {total_ms:.1f} ms", ""]
    for record in records:
        sequence = int(record.get("sequence", 0))
        elapsed_ms = float(record.get("elapsed_ms", 0.0))
        event = str(record.get("event", "unknown")).replace("_", " ").upper()
        data = record.get("data", {})
        summary = str(data.get("summary", "")) if isinstance(data, dict) else ""
        lines.append(f"{sequence:02d}  +{elapsed_ms:8.1f} ms  {event}")
        if summary:
            lines.append(f"    {summary}")
        for temperature in _temperature_lines(record):
            lines.append(f"    {temperature}")
    return "\n".join(lines)
