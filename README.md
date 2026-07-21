# Simple Weather Agent

A locally runnable Python agent powered by an OpenAI-compatible LLM. It answers
only current-temperature questions for cities explicitly named in the user request,
using the public Open-Meteo API. Every run produces a structured JSONL trace.

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
