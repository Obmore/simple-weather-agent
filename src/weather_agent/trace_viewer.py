"""Human-readable text and self-contained HTML views for JSONL traces."""

from __future__ import annotations

import html
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


def format_html_trace(records: list[TraceRecord]) -> str:
    """Render a self-contained local dashboard for one trace."""

    run_id = html.escape(str(records[0].get("run_id", "unknown")))
    total_ms = float(records[-1].get("elapsed_ms", 0.0))
    model_rounds = sum(record.get("event") == "model_request" for record in records)
    tool_calls = sum(record.get("event") == "tool_call_requested" for record in records)
    status = str(records[-1].get("event", "unknown")).replace("run_", "")
    cards: list[str] = []
    for record in records:
        sequence = int(record.get("sequence", 0))
        elapsed_ms = float(record.get("elapsed_ms", 0.0))
        event_raw = str(record.get("event", "unknown"))
        event = html.escape(event_raw.replace("_", " ").title())
        data = record.get("data", {})
        summary = html.escape(str(data.get("summary", ""))) if isinstance(data, dict) else ""
        details = html.escape(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        cards.append(
            f"""<article class="event {html.escape(event_raw)}">
  <div class="marker">{sequence:02d}</div>
  <div class="event-body">
    <div class="event-heading"><h2>{event}</h2><time>+{elapsed_ms:.1f} ms</time></div>
    <p>{summary}</p>
    <details><summary>Structured event data</summary><pre>{details}</pre></details>
  </div>
</article>"""
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Trace dashboard · {run_id}</title>
  <style>
    :root {{ color-scheme: dark; --bg:#07111f; --panel:#0e1b2e; --line:#263a55;
      --text:#e8f0fa; --muted:#9eb0c7; --accent:#54d2c4; --warn:#ffcb6b; --bad:#ff6b7d; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font:15px/1.55 Inter,Segoe UI,sans-serif; color:var(--text);
      background:radial-gradient(circle at 15% 0%,#163252 0,var(--bg) 38%); }}
    main {{ width:min(980px,calc(100% - 32px)); margin:48px auto 80px; }}
    header {{ margin-bottom:32px; }}
    .eyebrow {{ color:var(--accent); font-weight:700; letter-spacing:.13em;
      text-transform:uppercase; }}
    h1 {{ margin:.25rem 0; font-size:clamp(2rem,5vw,3.5rem); letter-spacing:-.045em; }}
    .run-id {{ color:var(--muted); overflow-wrap:anywhere; }}
    .metrics {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:28px 0; }}
    .metric {{ padding:18px; background:rgba(14,27,46,.88); border:1px solid var(--line);
      border-radius:14px; box-shadow:0 16px 45px rgba(0,0,0,.18); }}
    .metric strong {{ display:block; font-size:1.5rem; }}
    .metric span {{ color:var(--muted); }}
    .timeline {{ position:relative; display:grid; gap:14px; }}
    .timeline::before {{ content:""; position:absolute; left:23px; top:28px; bottom:28px;
      width:2px; background:var(--line); }}
    .event {{ position:relative; display:grid; grid-template-columns:48px 1fr; gap:14px; }}
    .marker {{ z-index:1; width:48px; height:48px; display:grid; place-items:center;
      border-radius:50%;
      color:#06121f; background:var(--accent); font-weight:800; box-shadow:0 0 0 6px var(--bg); }}
    .run_failed .marker,.tool_call_failed .marker {{ background:var(--bad); }}
    .reasoning_step .marker {{ background:var(--warn); }}
    .event-body {{ padding:18px 20px; background:rgba(14,27,46,.92); border:1px solid var(--line);
      border-radius:14px; }}
    .event-heading {{ display:flex; align-items:baseline; justify-content:space-between;
      gap:16px; }}
    h2 {{ margin:0; font-size:1rem; letter-spacing:.03em; }}
    time,p,details summary {{ color:var(--muted); }} p {{ margin:.5rem 0 0; }}
    details {{ margin-top:12px; }} summary {{ cursor:pointer; }}
    pre {{ overflow:auto; padding:14px; border-radius:9px; background:#07101c; color:#c9d8e9; }}
    @media (max-width:680px) {{ .metrics {{ grid-template-columns:repeat(2,1fr); }}
      .event-heading {{ align-items:flex-start; flex-direction:column; gap:2px; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <div class="eyebrow">Simple Weather Agent</div>
    <h1>Trace dashboard</h1>
    <div class="run-id">Run {run_id}</div>
    <section class="metrics">
      <div class="metric"><strong>{html.escape(status.title())}</strong><span>Status</span></div>
      <div class="metric"><strong>{total_ms:.1f} ms</strong><span>Total elapsed</span></div>
      <div class="metric"><strong>{model_rounds}</strong><span>Model rounds</span></div>
      <div class="metric"><strong>{tool_calls}</strong><span>Tool calls</span></div>
    </section>
  </header>
  <section class="timeline">{"".join(cards)}</section>
</main>
</body>
</html>
"""


def write_html_report(records: list[TraceRecord], output_path: Path) -> Path:
    """Write a self-contained UTF-8 HTML dashboard and return its resolved path."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(format_html_trace(records), encoding="utf-8", newline="\n")
    return output_path.resolve()
