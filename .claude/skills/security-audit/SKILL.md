---
name: security-audit
description: >-
  Audit code, configuration, and AI customizations against the Security Baseline
  and AI Boundary tiers. Use before commits, during PR reviews, or when touching auth, validation, or MCP configs.
---

# Skill: Security Audit

**Canonical Sources of Truth:**
- [docs/standards/security-baseline.md](../../../docs/standards/security-baseline.md)
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)

## When to Use

Activate this skill when auditing pull requests, reviewing authentication/authorization or input-validation code (Tier 2), checking `.mcp.json` or `.claude/settings.json`, or verifying pre-commit readiness.

## Audit Checklist

1. **Zero Secrets in Context or Tracked Files:**
   - Scan `CLAUDE.md`, `GEMINI.md`, `.claude/`, `.agents/`, `.mcp.json`, and source files for hardcoded keys, tokens, passwords, or private keys.
   - Verify `.env.example` contains only safe placeholders.
2. **Gitignore Verification:**
   - Confirm `.gitignore` excludes `CLAUDE.local.md`, `settings.local.json`, `.claude/settings.local.json`, and `.env` / `.env.*` (except `.env.example`).
3. **MCP Least Privilege:**
   - Confirm `.mcp.json` enables only approved servers with minimum permissions and read-only database access (`DB_READONLY=true`) where applicable.
4. **AI Boundary Compliance ([ai-boundary.md](../../../docs/standards/ai-boundary.md)):**
   - Confirm no Tier 3 boundaries were crossed (no production data in prompts/tests, no automated production deployment, no ledger sign-off by AI, no weakened tests).
   - Confirm all Tier 2 changes (auth, input validation, schema migrations, CI/CD, dependency upgrades) are flagged for explicit human approval.
5. **Hook & Permission Readiness:**
   - Check that `.claude/settings.json` permissions and `.claude/hooks/` (`validate-bash.sh`, `secret-scan.sh`) are present and reviewed `[VERIFY]`.

## Output Format

Report findings grouped by: **Critical (Tier 3 / Secret Leak)**, **Human Approval Required (Tier 2)**, and **Passed Baseline Controls**.
