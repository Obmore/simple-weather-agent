# Developer guide

## Development environment

Recommended tools: Python 3.12, Bash, and Git. Bootstrap the environment with:

```bash
./scripts/setup.sh
```

On Windows, use Git Bash or WSL. The equivalent PowerShell setup is:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Run the complete local quality gate with:

```bash
./scripts/check.sh
```

Equivalent direct commands:

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy
python -m pytest --cov=weather_agent --cov-report=term-missing
```

## Project structure

```text
src/weather_agent/
  agent.py       bounded tool-calling loop and scope policy
  cli.py         argument parsing and dependency wiring
  config.py      environment-backed configuration
  trace_viewer.py text and self-contained HTML trace rendering
  tracing.py     per-run append-only JSONL trace
  weather.py     Open-Meteo geocoding and forecast client
  web_ui.py      loopback-only HTTP adapter for interactive runs
  web/           embedded HTML, CSS, and JavaScript with no remote assets
tests/           network-free automated tests
docs/            user, developer, architecture, and AI documentation
scripts/         setup and quality-gate commands
```

## Critical invariants

1. The agent has exactly one tool: `get_current_temperatures`.
2. The forecast request asks for no weather data beyond `current=temperature_2m`.
3. Clearly out-of-scope requests are rejected before an LLM or weather call.
4. Only cities found in the user question may reach the tool.
5. Every agent run creates a trace, including failed runs.
6. API keys, complete provider responses, and authorization headers are never logged.
7. The agent loop is always bounded by `MAX_AGENT_ROUNDS`.

## Agent protocol

The implementation first applies a deterministic, conservative scope gate. Missing
temperature intent and explicit forecast, history, non-temperature weather, advice,
general-knowledge, or prompt-override indicators produce a traced refusal without
calling the model. This is intentionally allowed to prefer a safe false rejection
over an out-of-scope answer.

Eligible requests use the broadly supported OpenAI Chat Completions tool-calling
format. In each round, the assistant returns either final text or tool calls. For a
tool call, the assistant message and every tool result are appended to the message
list before the next model round. If a provider returns an empty response immediately
after a successful tool call, the agent makes one traced final-answer retry within
the existing `MAX_AGENT_ROUNDS` hard limit. The final public answer is rendered from
validated tool data, not copied from unrestricted model output. A response without a
validated tool result becomes an application-controlled scope refusal.

`WeatherAgent.run_result` exposes the validated answer, refusal state, temperature
records, and per-city errors. The CLI uses that object for `--json`; the compatibility
`WeatherAgent.run` method still returns plain text.

Provider replacement is a configuration task. After setting `OPENAI_BASE_URL`, the
provider must support the Chat Completions `tools` and `tool_calls` fields. The
default model matched the official current OpenAI model guidance when the plan was
created, but remains configurable for access and compatibility.

## Open-Meteo integration

The Open-Meteo Geocoding API converts city names to coordinates. The Forecast API
provides the measurement:

```http
GET /v1/forecast?latitude=...&longitude=...&current=temperature_2m&timezone=auto
```

The adapter forwards only `current.temperature_2m`, `current.time`,
`current_units.temperature_2m`, and timezone fields. Multiple cities currently use
separate requests, which provides straightforward error handling and partial results.

The default geocoding language is `en`. Use `OPEN_METEO_GEOCODING_LANGUAGE` to
adapt result ranking and display names for another primary audience.

## Test strategy

- HTTP tests use `httpx.MockTransport` and do not access the network.
- Agent tests use predefined LLM responses to prove the tool-calling round trip.
- A dedicated test prevents the LLM from querying a city absent from the question.
- Parametrized scope-gate tests prove that disallowed requests reach neither the LLM
  nor Open-Meteo, even when a simulated model would have requested the tool.
- The trace test verifies ordering, run IDs, and UTF-8 JSONL serialization.
- Output-guard tests prove that unrelated model text cannot reach the user.
- Trace-viewer tests cover run selection, text rendering, HTML escaping, and failures.
- Interactive-UI tests use an ephemeral loopback port and verify assets, security
  headers, input validation, safe trace projection, and trace-download isolation.
- Entry-point contract tests cover the PowerShell wrapper, setup path safety, and demo.
- Automated tests require no real API key.

## Trace viewer and local dashboard

`trace_viewer.py` reads only application-generated JSONL records. Text mode provides
a compact terminal timeline. HTML mode writes a self-contained static dashboard with
escaped event data and no external assets. It does not start a server or expose a new
network surface.

Each trace event contains `elapsed_ms`. Model and tool completion events also record
their own `duration_ms`, enabling latency inspection without storing provider payloads.

## Interactive UI boundary

`web_ui.py` is a thin transport adapter around the same `_run_agent` composition used
by the CLI. It contains no weather or LLM business logic. Each `POST /api/ask` creates
a new `JsonlTracer`, executes one bounded agent run, and returns the structured
`AgentResult` plus an allowlisted projection of trace fields.

The server deliberately uses only the Python standard library and embedded package
assets, so it adds no runtime dependency. `create_server` rejects any host other than
the exact IPv4 loopback address `127.0.0.1`. Request sizes and question lengths are
bounded, trace downloads accept only 32-character hexadecimal run IDs, and browser
responses include a restrictive Content Security Policy and related security headers.
No API key or provider authorization data is sent to the browser.

## Change workflow for AI and Cursor Composer

1. Read `AGENTS.md` and `docs/AI_IMPLEMENTATION_PLAN.md`.
2. Inspect `git status -sb`; never overwrite unrelated changes.
3. Mark the active milestone in the plan.
4. Add a test or acceptance example before changing behavior.
5. Preserve layer boundaries and scope invariants.
6. Run the complete quality gate.
7. Update plan checkboxes and `docs/AI_CHANGELOG.md`.

## Versioning and CI

GitHub Actions runs formatting, linting, mypy, and pytest on Python 3.11 through
3.13. Update the version in both `pyproject.toml` and `weather_agent.__version__`.
