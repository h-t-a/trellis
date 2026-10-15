---
name: security-audit
description: >-
  Audit code, configuration, and AI customizations against the Security Baseline
  and AI Boundary tiers. Use before commits, during PR reviews, or when touching auth, validation, or MCP configs.
---

# Skill: Security Audit (Antigravity)

**Canonical Sources of Truth:**
- [docs/standards/security-baseline.md](../../../docs/standards/security-baseline.md)
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)

## Audit Steps

1. **Secret & Context Check:**
   - Verify no secrets, tokens, or credentials exist in `GEMINI.md`, `CLAUDE.md`, `.agents/`, `.claude/`, `.mcp.json`, or source code.
   - Verify `.env.example` contains placeholders only and `.gitignore` excludes `.env`, `CLAUDE.local.md`, and `settings.local.json`.
2. **AI Boundary Check ([ai-boundary.md](../../../docs/standards/ai-boundary.md)):**
   - Ensure no Tier 3 boundaries were crossed (no real customer/production data, no production deployments, no ledger sign-off by AI, no weakened tests).
   - Flag all Tier 2 security-sensitive changes (auth, input validation, DB migrations, dependency upgrades, CI/CD) for human approval.
3. **Permissions & MCP Scope Check ([security-baseline.md](../../../docs/standards/security-baseline.md)):**
   - Confirm MCP configs use minimum permissions (`DB_READONLY=true`) and Antigravity `/permissions` + browser allowlist/denylist are configured before project use.
4. **Report Findings:**
   - Summarize results in the Walkthrough artifact grouped by **Critical (Tier 3 / Secret Leak)**, **Human Approval Required (Tier 2)**, and **Passed Baseline Controls**.
