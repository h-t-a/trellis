#!/usr/bin/env bash
# ==============================================================================
# .claude/hooks/validate-bash.sh
# ==============================================================================
# Purpose:
#   Wired PreToolUse (Bash) defense-in-depth hook in .claude/settings.json
#   ([REQ-TRL-07, REQ-TRL-26]). Inspects proposed shell commands and blocks
#   destructive patterns per docs/standards/security-baseline.md.
#   Note: Pattern checks are a safety net; rely on OS/container sandboxing
#   and command allowlists for hard isolation.
#
# Safety Guarantee:
#   Strictly read-only. Never deletes, overwrites, or transmits data.
# ==============================================================================

set -euo pipefail

INPUT_PAYLOAD="$(cat || true)"

# Normalize whitespace for matching common destructive patterns and flag orders
if printf '%s\n' "${INPUT_PAYLOAD}" | grep -Eiq \
  '(^|[[:space:];|&])rm[[:space:]]+((-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|--recursive[[:space:]]+--force|--force[[:space:]]+--recursive|-r[[:space:]]+-f|-f[[:space:]]+-r)[[:space:]]+(/|~|\$HOME|\.\.?(/|$|[[:space:]])|\*|[./]))'; then
  echo "[validate-bash] BLOCKED: Destructive recursive rm pattern detected. See docs/standards/security-baseline.md." >&2
  exit 2
fi

if printf '%s\n' "${INPUT_PAYLOAD}" | grep -Eiq \
  '(git[[:space:]]+push[[:space:]]+.*(--force|-f\b)|mkfs\.|mkfs[[:space:]]|dd[[:space:]]+if=)'; then
  echo "[validate-bash] BLOCKED: Command matches a restricted destructive pattern. See docs/standards/security-baseline.md." >&2
  exit 2
fi

exit 0
