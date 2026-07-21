# AI and Cursor development guide

## Read first

At the beginning of every development session, read these in order:

1. `docs/AI_IMPLEMENTATION_PLAN.md`
2. `docs/ARCHITECTURE.md`
3. `docs/DEVELOPMENT.md`
4. `git status -sb`

## Non-negotiable invariants

- The application answers only current-temperature questions for explicitly named cities.
- The Open-Meteo forecast request uses only `current=temperature_2m` weather data.
- Do not expose general HTTP, shell, filesystem, or search tools to the LLM.
- Bind every city requested by the tool back to the current user question.
- Every agent run must write a trace, including failed runs.
- Never log secrets, authorization headers, or complete provider payloads.
- Every agent loop must have a hard upper bound.
- Never display or store private chain-of-thought; log concise execution decisions instead.

## Workflow

Add or update a test for the requested behavior, make the smallest coherent change,
then run:

```bash
./scripts/check.sh
```

When Bash is unavailable:

```powershell
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m mypy
.venv\Scripts\python.exe -m pytest --cov=weather_agent --cov-report=term-missing
```

At the end of the session, update the checkboxes in `AI_IMPLEMENTATION_PLAN.md`
and add an entry to `AI_CHANGELOG.md`. Never overwrite unrelated worktree changes.

## Code style

- Use Python 3.11+ and complete type annotations.
- Prefer small deterministic functions and dependency injection at network boundaries.
- Use descriptive domain errors; do not expose raw stack traces in normal CLI output.
- Any new runtime dependency requires a documented reason and test coverage.
