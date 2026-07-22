# Simple Weather Agent

A locally runnable Python agent powered by an OpenAI-compatible LLM. It answers
only current-temperature questions for cities explicitly named in the user request,
using the public Open-Meteo API. Every run produces a structured JSONL trace, and
validated tool data—not unrestricted model text—controls the public answer.

## Quick start

```bash
cp .env.example .env
# Set OPENAI_API_KEY and, if necessary, OPENAI_MODEL.
./run.sh "What is the current temperature in Budapest and Paris?"
```

To mirror trace events to the console:

```bash
./run.sh --trace "What is the current temperature in Vienna?"
```

From Windows PowerShell, use the native wrapper. It locates Git Bash and delegates
to the required Bash entry point:

```powershell
./run.ps1 --trace "What is the current temperature in Vienna?"
```

Machine-readable output and the local trace dashboard are also available:

```bash
./run.sh --json "What is the current temperature in Budapest?"
./run.sh --show-trace latest
./run.sh --show-trace latest --html trace-report.html
```

Start the optional interactive UI on the loopback interface:

```bash
./run.sh --ui
```

```powershell
./run.ps1 --ui
```

The browser UI runs the same constrained agent as the CLI, displays the validated
temperature result and sanitized execution timeline, and lets you download the
run's JSONL trace. It binds only to `127.0.0.1` and loads no remote web assets.

Run the evaluator-friendly acceptance demonstration with:

```bash
./scripts/demo.sh
```

Detailed documentation:

- [User guide](docs/USER_GUIDE.md)
- [Developer guide](docs/DEVELOPMENT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [AI implementation plan](docs/AI_IMPLEMENTATION_PLAN.md)

The weather integration uses the `current=temperature_2m` field defined by the
official [Open-Meteo forecast OpenAPI specification](https://github.com/open-meteo/open-meteo/blob/main/openapi/forecast.yml).
The tool-calling loop follows the
[OpenAI function-calling guide](https://developers.openai.com/api/docs/guides/function-calling),
while keeping the provider base URL and model configurable.
