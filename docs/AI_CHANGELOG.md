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

## 2026-07-22 - Native PowerShell entry point

- Added `run.ps1` so Windows PowerShell users can start the agent without relying on
  the operating system's `.sh` file association.
- Kept `run.sh` as the required canonical entry point; the PowerShell wrapper locates
  Git Bash, forwards all arguments, and preserves the Bash process exit code.
- Documented and tested the PowerShell launch path.

## 2026-07-22 - Empty provider response recovery

- Added one bounded, traced retry when an OpenAI-compatible provider returns an empty
  final response immediately after a successful weather tool call.
- Preserved `MAX_AGENT_ROUNDS` as the hard upper bound and kept empty responses in
  other protocol states as errors.
- Added regression coverage for the Ollama-compatible retry path.

## 2026-07-22 - Compliance hardening and trace dashboard

- Added an application-controlled scope refusal and deterministic rendering from
  validated temperature tool data so unrestricted model text cannot reach users.
- Created traces before configuration and input validation, including terminal events
  for early failures and elapsed-time metrics for all events.
- Added structured `--json` output, readable `--show-trace` timelines, and a
  self-contained local HTML dashboard with escaped data and no remote assets.
- Added `scripts/demo.sh` for single-city, multi-city, and refusal acceptance cases.
- Fixed editable development installation under Windows Git Bash when project paths
  contain spaces.
- Expanded the network-free suite to 35 tests with 89.21% branch-aware coverage.

## 2026-07-22 - Interactive local UI

- Added an optional browser UI started by `run.sh --ui` or `run.ps1 --ui`, while
  preserving the Bash CLI as the canonical required entry point.
- Reused the exact CLI agent composition so every submitted question keeps the same
  scope enforcement, deterministic output guard, bounded loop, and JSONL trace.
- Added validated temperature cards, execution metrics, a sanitized trace timeline,
  and per-run JSONL downloads without exposing credentials or provider payloads.
- Restricted the HTTP server to `127.0.0.1`, embedded every asset, bounded request
  sizes, allowlisted public trace fields, and added restrictive browser headers.
- Added a deterministic pre-model scope gate after live Ollama browser testing showed
  that prompt-only enforcement could still tool-call on a forecast question.
- Verified that forecast, historical, mixed-weather, general-knowledge, and
  prompt-override requests are refused before any LLM or Open-Meteo call.
- Added network-free HTTP and bridge tests for routing, validation, trace isolation,
  loopback binding, controlled failures, and lifecycle cleanup.
