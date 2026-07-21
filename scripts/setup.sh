#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON="${PYTHON_BIN:-python3}"
elif command -v python >/dev/null 2>&1; then
  PYTHON="${PYTHON_BIN:-python}"
else
  echo "Python 3.11+ is required." >&2
  exit 127
fi

"${PYTHON}" -m venv "${PROJECT_DIR}/.venv"

if [[ -x "${PROJECT_DIR}/.venv/bin/python" ]]; then
  VENV_PYTHON="${PROJECT_DIR}/.venv/bin/python"
else
  VENV_PYTHON="${PROJECT_DIR}/.venv/Scripts/python.exe"
fi

"${VENV_PYTHON}" -m pip install --upgrade pip
"${VENV_PYTHON}" -m pip install -e "${PROJECT_DIR}[dev]"
echo "Development environment is ready."
