#!/usr/bin/env bash
# ==============================================================================
# .claude/hooks/validate-bash.sh
# ==============================================================================
# Purpose:
#   Inspect a proposed shell command and block unsafe or destructive operations
#   per docs/standards/security-baseline.md ("A rule is a request; a hook is a guarantee").
#
# Safety Guarantee (Working Agreement 6):
#   This script is strictly read-only. It never deletes, overwrites, or sends
#   data anywhere.
#
# Intended Wiring in .claude/settings.json [VERIFY hook schema in installed Claude Code version]:
#   Do NOT wire automatically until approved by the project owner.
#   Example configuration to verify against your installed Claude Code version:
#   {
#     "hooks": {
#       "PreToolUse": [
#         {
#           "matcher": "Bash",
#           "hooks": [
#             {
#               "type": "command",
#               "command": "./.claude/hooks/validate-bash.sh"
#             }
#           ]
#         }
#       ]
#     }
#   }
# ==============================================================================

set -euo pipefail

# Read the proposed payload or command string from stdin (if piped by the hook runner)
INPUT_PAYLOAD="$(cat || true)"

# Block clearly destructive patterns (read-only string check)
if printf '%s\n' "${INPUT_PAYLOAD}" | grep -Eiq '(rm[[:space:]]+-rf[[:space:]]+/|git[[:space:]]+push[[:space:]]+--force|mkfs|dd[[:space:]]+if=)'; then
  echo "[validate-bash] BLOCKED: Command matches a restricted destructive pattern. See docs/standards/security-baseline.md." >&2
  exit 2
fi

exit 0
