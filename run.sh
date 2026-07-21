#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${WEATHER_AGENT_VENV:-${PROJECT_DIR}/.venv}"

if command -v python3 >/dev/null 2>&1; then
  BOOTSTRAP_PYTHON="${PYTHON_BIN:-python3}"
elif command -v python >/dev/null 2>&1; then
  BOOTSTRAP_PYTHON="${PYTHON_BIN:-python}"
else
  echo "Python 3.11+ is required." >&2
  exit 127
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  "${BOOTSTRAP_PYTHON}" -m venv "${VENV_DIR}"
fi

if [[ -x "${VENV_DIR}/bin/python" ]]; then
  VENV_PYTHON="${VENV_DIR}/bin/python"
elif [[ -x "${VENV_DIR}/Scripts/python.exe" ]]; then
  VENV_PYTHON="${VENV_DIR}/Scripts/python.exe"
else
  echo "The virtual environment does not contain a Python executable." >&2
  exit 1
fi

if ! "${VENV_PYTHON}" -c "import httpx, openai, dotenv" >/dev/null 2>&1; then
  "${VENV_PYTHON}" -m pip install --upgrade pip
  "${VENV_PYTHON}" -m pip install -e "${PROJECT_DIR}"
fi

export PYTHONPATH="${PROJECT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec "${VENV_PYTHON}" -m weather_agent "$@"
