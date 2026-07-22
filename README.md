# Simple Weather Agent

A small Python agent that answers current-temperature questions for named cities.
It uses an OpenAI-compatible model for tool calling and Open-Meteo for the actual
weather reading. Every run writes a JSONL trace.

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

The browser UI uses the same agent as the CLI. It shows the result and run trace,
and is available only on `127.0.0.1`.

Run the three sample cases with:

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
