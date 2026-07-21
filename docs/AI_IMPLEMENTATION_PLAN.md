# AI development implementation plan

Status: approved baseline plan  
Last updated: 2026-07-21

## 1. Goal and scope

Build a locally runnable Python command-line agent powered through an
OpenAI-compatible Chat Completions API. The agent has one business capability:
retrieve and answer with the current 2-metre air temperature for cities explicitly
named in the user's question.

The agent briefly refuses requests for other weather data, forecasts, general
knowledge, or unrelated actions. Open-Meteo is reachable only through the narrow
tool invoked by the LLM.

## 2. Requirement mapping

| Requirement | Implementation | Verification |
| --- | --- | --- |
| Python implementation | `src/weather_agent` package, Python 3.11+ | import and CLI tests |
| OpenAI-compatible LLM | official `openai` SDK with configurable `base_url`, model, and API key | mocked tool-calling test |
| Current city temperature only | strict system policy, one `get_current_temperatures` tool, constrained tool output | scope and refusal tests |
| Cities named in the request | explicit city list plus city-to-question binding | multi-city and rejection tests |
| Open-Meteo forecast API | `/v1/forecast?current=temperature_2m&timezone=auto`; separate Open-Meteo geocoding endpoint | HTTP mocks and live smoke check |
| Observable reasoning and tool calls | per-run JSONL event log and optional console trace | trace schema test |
| Bash execution | root-level `run.sh` | `bash run.sh --help` |
| Separate user and developer documentation | `docs/USER_GUIDE.md`, `docs/DEVELOPMENT.md` | documentation checklist |
| Cursor Composer continuity | `AGENTS.md`, `.cursor/rules/project.mdc`, plan, ADRs, and changelog | file presence and language scan |

## 3. Architecture

```text
CLI
 |- Settings (environment variables)
 |- JsonlTracer (run ID and audit events)
 `- WeatherAgent (bounded tool-calling loop)
      |- OpenAI-compatible Chat Completions client
      `- OpenMeteoClient
           |- Geocoding API: city -> coordinates
           `- Forecast API: coordinates -> current.temperature_2m
```

Layer boundaries:

1. The CLI performs configuration and output only; it contains no network logic.
2. The agent manages messages and the tool-calling protocol, but no HTTP details.
3. The weather client is deterministic, LLM-independent, and separately testable.
4. The tracer has a stable append-only JSONL format and excludes secrets and full
   provider responses.

## 4. Agent loop and safeguards

1. The CLI submits one question to the agent.
2. The system instruction defines the exclusive scope and refusal behavior.
3. The LLM either returns a refusal/final response or calls the temperature tool.
4. Tool arguments contain an array of city names validated against a JSON Schema.
5. The client deduplicates cities, geocodes each one, and requests only
   `current=temperature_2m` from the forecast API.
6. Tool results return to the LLM, which produces a short temperature-only answer.
7. A configured maximum number of LLM rounds prevents infinite loops.

Layered protection:

- no generic HTTP tool or arbitrary forecast parameter is exposed;
- tool output contains only city, temperature, unit, and observation time;
- the system policy forbids non-temperature answers;
- errors remain user-friendly while diagnostic details stay in the trace;
- API keys and authorization headers are never traced.

## 5. Observability

Every run receives a unique `run_id`. The `traces/<run_id>.jsonl` events include:

- `run_started`, `run_finished`, and `run_failed`;
- `reasoning_step`: a concise system-generated decision summary, not hidden
  chain-of-thought;
- `model_request` and `model_response`;
- `tool_call_requested`, `tool_call_completed`, and `tool_call_failed`.

The `--trace` flag also writes concise event summaries to stderr. The log exists to
audit the execution path, not to reconstruct private model reasoning.

## 6. Quality gates

- Ruff formatting and linting.
- Strict mypy checking for the source package.
- Pytest with network-free HTTP mocks.
- Branch-aware coverage for critical agent, tool, and weather paths.
- A separate live Open-Meteo smoke check outside the default test run.
- GitHub Actions on Python 3.11, 3.12, and 3.13.
- Repository-wide English-language scan.

## 7. Milestones and definition of done

### M1 - Foundation

- [x] Requirements and decisions recorded.
- [x] Package structure, configuration, and domain errors implemented.

### M2 - Functional core

- [x] Open-Meteo geocoding and current-temperature client implemented.
- [x] OpenAI-compatible tool-calling loop implemented.
- [x] Per-run JSONL tracing implemented.

### M3 - Usability

- [x] Bash entry point and CLI implemented.
- [x] Separate user and developer documentation completed.
- [x] Cursor and Codex project instructions completed.
- [x] All project-authored language converted to English.

### M4 - Evidence

- [x] Unit and integration-style tests pass.
- [x] Ruff and mypy pass.
- [x] Secret and repository-content checks completed.
- [x] Private GitHub repository published without adding the collaborator.

The project is complete when a clean environment can install it with the documented
command, the tool-calling path is verified with a mocked LLM, a live Open-Meteo
reading can be fetched, every run is traceable, and the private remote repository is
published.

## 8. Configurable decisions and continuation

The following choices remain configurable and do not block implementation:

- provider and model through `OPENAI_BASE_URL` and `OPENAI_MODEL`;
- timeout, retry behavior, and maximum agent rounds;
- trace directory and console trace behavior;
- geocoding response language through `OPEN_METEO_GEOCODING_LANGUAGE`.

Before the next AI session, read `AGENTS.md`, this plan, `docs/ARCHITECTURE.md`, and
`docs/DEVELOPMENT.md` in that order. At the end of the session, update the milestone
checkboxes and `docs/AI_CHANGELOG.md`.
