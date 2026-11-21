#!/usr/bin/env bash
# ==============================================================================
# .claude/hooks/run-tests.sh
# ==============================================================================
# Purpose:
#   Wired Stop hook in .claude/settings.json ([REQ-TRL-07, REQ-TRL-26]).
#   Executes the project's automated test suite at task completion to enforce
#   docs/standards/testing-standard.md and docs/standards/definition-of-done.md.
#
# Safety Guarantee:
#   Runs read-only test verification without modifying tracked source files.
# ==============================================================================

set -euo pipefail

PY_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PY_BIN="python"
fi

if [ -d "tests" ] && [ -n "${PY_BIN}" ]; then
  echo "[run-tests] Running Python unittest suite (${PY_BIN} -m unittest discover -s tests)..."
  "${PY_BIN}" -m unittest discover -s tests
  exit $?
fi

if [ -f "package.json" ] && command -v npm >/dev/null 2>&1; then
  echo "[run-tests] Running npm test..."
  npm test
  exit $?
fi

if [ -f "go.mod" ] && command -v go >/dev/null 2>&1; then
  echo "[run-tests] Running go test ./..."
  go test ./...
  exit $?
fi

echo "[run-tests] No supported test runner detected in $(pwd); configure .claude/hooks/run-tests.sh for this repository." >&2
exit 0
