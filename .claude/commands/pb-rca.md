---
name: pb-rca
description: Fast 9-step Root-Cause Analysis and minimal bug fix workflow with Tier 3 PII/secret redaction gate. Invoke as /pb-rca when diagnosing exceptions, failing tests, latency regressions, or deadlocks.
---

# Skill: `/pb-rca` — Fast Root-Cause Analysis & Minimal Fix

**Canonical Standards:**
- [docs/standards/rca-playbook.md](../../../docs/standards/rca-playbook.md)
- [docs/standards/testing-standard.md](../../../docs/standards/testing-standard.md)
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)

## Execution Steps

1. **Tier 3 Redaction Gate (`[REQ-RCA-01]`):**
   - Call the MCP tool `trellis_rca` (if `@trellis-mcp` is active) or manually verify that attached `@terminal` / `@logfile` inputs contain **no unredacted customer PII, PAN/card numbers, or credentials**. Stop and ask the developer to sanitize if detected.
2. **Phase 1 — Diagnose & Prove Root Cause (`[REQ-RCA-02]`):**
   - **Restate symptom** in one line (expected vs. actual, where, since when, frequency).
   - **Reproduce** or state why reproduction is blocked; never guess a fix.
   - **Collect cheap evidence first:** stack trace, failing test, sanitized logs, and `git diff` / `git log -n 5` on suspect `@file`s (no repo-wide scan).
   - **Form at most 3 ranked hypotheses** (including banking concurrency, lock ordering, idempotency, and SQL `EXPLAIN` checks per `[REQ-RCA-03]`) and state the single cheapest check to **disprove** each.
   - **Run the cheapest discriminating check first.** Stop and pause for human confirmation once the cause is proven (or re-plan via `/grill-me` after 3 failed attempts).
3. **Phase 2 — Failing Test & Minimal Fix (absorbs `/pb-fix`):**
   - Write a failing test (`Red`) citing the bug/requirement ID, apply the minimal diff (`Green`), run the test suite once, and produce a Walkthrough ([templates/walkthrough.md](../../../templates/walkthrough.md)).
