#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "${PROJECT_DIR}/.venv/bin/python" ]]; then
  PYTHON="${PROJECT_DIR}/.venv/bin/python"
elif [[ -x "${PROJECT_DIR}/.venv/Scripts/python.exe" ]]; then
  PYTHON="${PROJECT_DIR}/.venv/Scripts/python.exe"
else
  echo "Run ./scripts/setup.sh first." >&2
  exit 1
fi

"${PYTHON}" -m ruff format --check .
"${PYTHON}" -m ruff check .
"${PYTHON}" -m mypy
"${PYTHON}" -m pytest --cov=weather_agent --cov-report=term-missing
