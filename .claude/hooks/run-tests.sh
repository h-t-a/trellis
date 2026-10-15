#!/usr/bin/env bash
# ==============================================================================
# .claude/hooks/run-tests.sh
# ==============================================================================
# Purpose:
#   Run the project's automated test suite at task completion to enforce
#   docs/standards/testing-standard.md and docs/standards/definition-of-done.md.
#
# Safety Guarantee (Working Agreement 6):
#   This script is simple, readable, and never deletes, overwrites, or sends
#   data anywhere.
#
# Intended Wiring in .claude/settings.json [VERIFY hook schema in installed Claude Code version]:
#   Do NOT wire automatically until approved by the project owner.
#   Example configuration to verify against your installed Claude Code version:
#   {
#     "hooks": {
#       "Stop": [
#         {
#           "hooks": [
#             {
#               "type": "command",
#               "command": "./.claude/hooks/run-tests.sh"
#             }
#           ]
#         }
#       ]
#     }
#   }
# ==============================================================================

set -euo pipefail

# TODO [TO RESEARCH]: Replace the echo below with the project's actual test runner
# (e.g., `npm test`, `pytest`, `./gradlew test`, or `go test ./...`) when adopting
# this starter kit in a target repository.
echo "[run-tests] Starter kit placeholder: configure project test command in .claude/hooks/run-tests.sh (see docs/standards/testing-standard.md)."

exit 0
