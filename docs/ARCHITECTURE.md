# Architecture and decisions

## System overview

```text
user -> run.sh/run.ps1 -> CLI ---------> WeatherAgent -> OpenAI-compatible LLM
                           |                  |
                           |                  +-> get_current_temperatures
                           |                        |
                           |                        +-> Open-Meteo Geocoding API
                           |                        +-> Open-Meteo Forecast API
                           |
                           `-> loopback web UI -----'

CLI + WeatherAgent + tool ---------------------------------> JSONL trace
                                                              |
                                                              +-> text timeline
                                                              `-> local HTML dashboard
```

## ADR-001: Chat Completions compatibility surface

Status: accepted.

The requirement calls for an OpenAI-compatible LLM, so the implementation uses the
widely supported Chat Completions tool-calling surface instead of a provider-specific
agent framework. The official `openai` Python client's `base_url` parameter allows
the provider to be replaced. Consequently, the selected compatible model must
support the `tools` and `tool_calls` protocol.

## ADR-002: Explicit agent loop instead of a framework

Status: accepted.

The agent needs one tool and only a few rounds. A small explicit loop reduces
dependencies and makes auditing and testing easier. A configurable maximum round
count provides a hard safety bound.

## ADR-003: Layered scope enforcement

Status: accepted.

A system prompt is not a sufficient invariant by itself. Therefore:

- only one narrow tool is available;
- a deterministic pre-model gate rejects clear forecast, history, mixed-weather,
  advice, general-knowledge, and prompt-override requests;
- the tool accepts neither arbitrary URLs nor selectable weather fields;
- tool city arguments are bound back to words in the user question;
- the model must refuse the entire request when allowed and disallowed scopes are mixed.

Normalized conservative similarity matching handles grammatical suffixes. This is a
safety boundary rather than a general natural-language understanding or named-entity
recognition system. The input gate intentionally prefers a safe false rejection over
an out-of-scope answer, and rejections remain diagnosable through the trace.

## ADR-004: Execution trace, not chain-of-thought

Status: accepted.

The application logs explicit state transitions and concise execution decisions.
It neither requests nor stores hidden chain-of-thought. JSONL files are append-only,
one file is created per run, and every record includes a run ID, sequence number,
and UTC timestamp.

## ADR-005: Deterministic public output guard

Status: accepted.

The LLM controls tool selection but does not directly control the public response.
Without a validated temperature tool result, the application returns a fixed scope
refusal. After a tool round trip, Python renders the answer only from the validated
city, temperature, unit, observation time, and error fields. This prevents prompt
injection or provider drift from adding forecasts, other weather variables, advice,
or general knowledge.

## ADR-006: Static local trace dashboard

Status: accepted.

The optional UI is a self-contained HTML rendering of an existing local JSONL trace.
It starts no server, loads no remote assets, and introduces no runtime dependency or
additional LLM tool. The required Bash CLI remains the canonical execution surface.

## ADR-007: Optional interactive loopback UI

Status: accepted.

An interactive browser UI is an additive local presentation layer. It invokes the
same `WeatherAgent` composition as the CLI, creates one JSONL trace per question, and
renders only the structured `AgentResult` and an allowlisted trace projection. The
required Bash entry point remains available and starts the UI through `--ui`.

The HTTP server binds only to the exact `127.0.0.1` address, serves embedded assets,
accepts bounded JSON requests, and exposes trace files only through validated run
IDs. No secret or provider credential crosses the browser boundary. This keeps the
extra UI within the task's locally runnable environment without broadening the
agent's functional scope.

## Error model

- Configuration and protocol failures produce controlled, descriptive user errors.
- Open-Meteo location failures can be returned per city in the tool result.
- Provider and unexpected failures produce a short public message with details in the trace.
- Partial multi-city failures preserve successful readings alongside error records.

## Security and data handling

User questions and tool data are stored locally in trace files. Treat those files as
potentially sensitive and never commit them. Secrets may exist only in environment
variables or the ignored `.env` file. User text is never executed as a command, URL,
or arbitrary tool invocation. The interactive server is not a deployment target and
must remain loopback-only.
