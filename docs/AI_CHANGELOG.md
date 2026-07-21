# AI development changelog

## 2026-07-21 - Initial implementation

- Converted the requirements into executable milestones and quality gates.
- Selected `current.temperature_2m` from the official Open-Meteo OpenAPI schema.
- Implemented an OpenAI-compatible Chat Completions tool-calling architecture with
  configurable provider URL and model.
- Added a bounded agent loop, city-to-question binding, and append-only JSONL tracing.
- Added Bash setup and execution scripts, Cursor project configuration, and separate
  user and developer documentation.
- Verified Ruff, mypy, and 24 tests with 87.12% branch-aware coverage.
- Validated the Bash entry point with Git Bash and ran a live Open-Meteo smoke test.
- Private GitHub publication was initially pending until GitHub CLI became available.
  Inviting the collaborator remains the project owner's responsibility.

## 2026-07-21 - English-only repository

- Converted all documentation, CLI text, examples, tests, and AI handoff instructions
  to English.
- Renamed language-specific documentation files to language-neutral English names.
- Changed the default Open-Meteo geocoding language to English while keeping it configurable.

Before the next implementation change, run `scripts/check.sh`. Modify behavior only
for a verified defect or a new requirement.

## 2026-07-21 - Private repository publication

- Initialized the repository on the `main` branch with an intentional initial commit.
- Published the project as the private `Obmore/simple-weather-agent` GitHub repository.
- Preserved the owner-only collaborator invitation step outside the repository.
- Updated official GitHub Actions dependencies to their current Node 24-based major
  versions after the first remote CI run reported Node 20 deprecation warnings.

## 2026-07-21 - Submission compliance and cleanup

- Re-audited every functional and delivery requirement against source, tests,
  documentation, local state, and the private GitHub repository.
- Removed the redundant GitHub handoff document and unused pytest live-test marker.
- Confirmed that local generated environments, caches, coverage data, bytecode, and
  editable-install metadata are ignored and safe to regenerate.
