#!/usr/bin/env bash
# ==============================================================================
# .claude/hooks/secret-scan.sh
# ==============================================================================
# Purpose:
#   Wired PreToolUse (Bash) defense-in-depth hook in .claude/settings.json
#   ([REQ-TRL-07, REQ-TRL-26]). Performs a read-only check on staged git changes
#   to prevent accidental commits of local secret/keystore files or private keys
#   per docs/standards/security-baseline.md.
#
# Safety Guarantee:
#   Strictly read-only. Never deletes, overwrites, or transmits data.
# ==============================================================================

set -euo pipefail

# 1. Ensure forbidden local files (.env, .trellis_keys.json, CLAUDE.local.md, settings.local.json) are not staged
STAGED_FILES="$(git diff --cached --name-only 2>/dev/null || true)"
FILTERED_STAGED="$(printf '%s\n' "${STAGED_FILES}" | grep -v '\.env\.example$' || true)"
if printf '%s\n' "${FILTERED_STAGED}" | grep -Eq '(^|/)\.env($|\.)|\.trellis_keys\.json$|CLAUDE\.local\.md$|settings\.local\.json$'; then
  echo "[secret-scan] BLOCKED: Local environment, keystore, or override file is staged for commit. See docs/standards/security-baseline.md." >&2
  exit 2
fi

# 2. Scan staged diff lines for private key headers (read-only check)
if git diff --cached 2>/dev/null | grep -Eq '^\+.*BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY'; then
  echo "[secret-scan] BLOCKED: Private key header detected in staged changes. See docs/standards/security-baseline.md." >&2
  exit 2
fi

exit 0
