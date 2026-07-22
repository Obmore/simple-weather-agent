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
tests/           network-free automated tests
docs/            user, developer, architecture, and AI documentation
scripts/         setup and quality-gate commands
```

## Critical invariants

1. The agent has exactly one tool: `get_current_temperatures`.
2. The forecast request asks for no weather data beyond `current=temperature_2m`.
3. Only cities found in the user question may reach the tool.
4. Every agent run creates a trace, including failed runs.
5. API keys, complete provider responses, and authorization headers are never logged.
6. The agent loop is always bounded by `MAX_AGENT_ROUNDS`.

## Agent protocol

The implementation uses the broadly supported OpenAI Chat Completions tool-calling
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
- The trace test verifies ordering, run IDs, and UTF-8 JSONL serialization.
- Output-guard tests prove that unrelated model text cannot reach the user.
- Trace-viewer tests cover run selection, text rendering, HTML escaping, and failures.
- Entry-point contract tests cover the PowerShell wrapper, setup path safety, and demo.
- Automated tests require no real API key.

## Trace viewer and local dashboard

`trace_viewer.py` reads only application-generated JSONL records. Text mode provides
a compact terminal timeline. HTML mode writes a self-contained static dashboard with
escaped event data and no external assets. It does not start a server or expose a new
network surface.

Each trace event contains `elapsed_ms`. Model and tool completion events also record
their own `duration_ms`, enabling latency inspection without storing provider payloads.

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
