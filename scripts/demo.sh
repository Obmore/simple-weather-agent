#!/usr/bin/env bash
set -u -o pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_TRACE_DIR="${DEMO_TRACE_DIR:-${PROJECT_DIR}/traces/demo}"

run_case() {
  local title="$1"
  local question="$2"

  echo
  echo "=== ${title} ==="
  "${PROJECT_DIR}/run.sh" --trace --trace-dir "${DEMO_TRACE_DIR}" "${question}"
  local exit_code=$?
  echo
  "${PROJECT_DIR}/run.sh" --trace-dir "${DEMO_TRACE_DIR}" --show-trace latest
  return "${exit_code}"
}

overall_exit=0
run_case \
  "Allowed single-city request" \
  "What is the current temperature in Budapest?" || overall_exit=$?
run_case \
  "Allowed multi-city request" \
  "What is the current temperature in Budapest and Paris?" || overall_exit=$?
run_case \
  "Rejected out-of-scope request" \
  "What will the temperature in Budapest be tomorrow?" || overall_exit=$?

echo
echo "Demo traces: ${DEMO_TRACE_DIR}"
exit "${overall_exit}"
