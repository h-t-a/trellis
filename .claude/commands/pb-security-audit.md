---
name: pb-security-audit
description: Use when auditing code, configurations, and hooks against the Security Baseline. Not for functional testing or performance tuning.
metadata: {pack: core, tier: 2, quota_class: M, standards: [security-baseline, ai-boundary]}
---

# Skill: `/pb-security-audit` — Security & AI Boundary Audit

**Canonical Standards:**
- [docs/standards/security-baseline.md](../../docs/standards/security-baseline.md)
- [docs/standards/ai-boundary.md](../../docs/standards/ai-boundary.md)

## Execution Steps

1. **Secret & Context Check (`trellis_scan`):**
   - Verify no secrets, tokens, or credentials exist in `GEMINI.md`, `CLAUDE.md`, `.agents/`, `.claude/`, `.mcp.json`, or source code.
   - Verify `.env.example` contains placeholders only and `.gitignore` excludes `.env`, `.trellis_keys.json`, `.trellis-audit.jsonl`, `CLAUDE.local.md`, and `settings.local.json`.
2. **AI Boundary Check ([ai-boundary.md](../../docs/standards/ai-boundary.md)):**
   - Ensure no Tier 3 boundaries were crossed (no real customer/production data, no production deployments, no ledger sign-off by AI, no weakened tests).
   - Flag all Tier 2 security-sensitive changes (auth, input validation, DB migrations, dependency upgrades, CI/CD) for human approval.
3. **Permissions, Hooks & MCP Scope Check ([security-baseline.md](../../docs/standards/security-baseline.md)):**
   - Confirm MCP configs use minimum permissions (`DB_READONLY=true`) and `.claude/settings.json` deny rules + `PreToolUse` / `Stop` hooks are intact (`trellis_mcp_registry`).
4. **Report Findings:**
   - Summarize results in [templates/walkthrough.md](../../templates/walkthrough.md) grouped by **Critical (Tier 3 / Secret Leak)**, **Human Approval Required (Tier 2)**, and **Passed Baseline Controls**.
