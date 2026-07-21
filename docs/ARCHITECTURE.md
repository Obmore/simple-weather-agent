# Architecture and decisions

## System overview

```text
user -> run.sh -> CLI -> WeatherAgent -> OpenAI-compatible LLM
                           |
                           +-> get_current_temperatures
                                 |
                                 +-> Open-Meteo Geocoding API
                                 +-> Open-Meteo Forecast API

CLI + WeatherAgent + tool ---------------------------------> JSONL trace
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
- the tool accepts neither arbitrary URLs nor selectable weather fields;
- tool city arguments are bound back to words in the user question;
- the model must refuse the entire request when allowed and disallowed scopes are mixed.

Normalized conservative similarity matching handles grammatical suffixes. This is a
safety boundary rather than a general named-entity recognition system; false
rejections remain diagnosable through the trace.

## ADR-004: Execution trace, not chain-of-thought

Status: accepted.

The application logs explicit state transitions and concise execution decisions.
It neither requests nor stores hidden chain-of-thought. JSONL files are append-only,
one file is created per run, and every record includes a run ID, sequence number,
and UTC timestamp.

## Error model

- Configuration and protocol failures produce controlled, descriptive user errors.
- Open-Meteo location failures can be returned per city in the tool result.
- Provider and unexpected failures produce a short public message with details in the trace.
- Partial multi-city failures preserve successful readings alongside error records.

## Security and data handling

User questions and tool data are stored locally in trace files. Treat those files as
potentially sensitive and never commit them. Secrets may exist only in environment
variables or the ignored `.env` file. User text is never executed as a command, URL,
or arbitrary tool invocation.
