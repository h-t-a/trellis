---
name: pb-review
description: Unified Pre-PR & Code Review check against Story Definition of Done, Testing Standard, AI Boundary Tiers 1-3, Security Baseline, Git Convention, and the Review Comment -> Rule loop (replaces standalone code-review). Invoke as /pb-review.
---

# Skill: `/pb-review` — Unified Pre-PR & Code Review Gate

**Canonical Standards:**
- [docs/standards/definition-of-done.md](../../../docs/standards/definition-of-done.md)
- [docs/standards/testing-standard.md](../../../docs/standards/testing-standard.md)
- [docs/standards/security-baseline.md](../../../docs/standards/security-baseline.md)
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)
- [docs/standards/git-convention.md](../../../docs/standards/git-convention.md)
- [docs/onboarding.md](../../../docs/onboarding.md)
- **Templates:** [templates/walkthrough.md](../../../templates/walkthrough.md), [templates/pull_request_template.md](../../../templates/pull_request_template.md)

## Execution Steps (Quota Guard: Read `git diff`, Never Scan the Whole Repo)

1. **Plan Alignment & Current Diff (`trellis_review`, `trellis_pipeline`):**
   - Confirm an Implementation Plan artifact ([templates/implementation-plan.md](../../../templates/implementation-plan.md)) was approved before significant AI-generated Tier 2 code, and check cross-model reviewer separation (`reviewer_model != writer_model`).
   - Run `git diff HEAD` (`git status --short`) or pass the diff to the `trellis_review` MCP tool.
2. **Test Verification & Integrity ([testing-standard.md](../../../docs/standards/testing-standard.md)):**
   - Verify **zero** existing tests were deleted, skipped (`@Disabled`, `.skip`, `xit`, `unittest.skip`), or weakened (Tier 3 block).
   - Verify every new test cites its `[REQ-NNN-XX]` requirement ID and has meaningful assertions reviewed by a human.
3. **Security, Git Convention & Docs Gates ([definition-of-done.md](../../../docs/standards/definition-of-done.md)):**
   - Confirm no secrets, tokens, Luhn PANs, or real customer data appear in the diff, and local config files remain gitignored (`trellis_scan`).
   - Verify commit headers follow `<type>(<scope>): <lowercase imperative summary>` (≤ 72 chars, no trailing period) per `/pb-git-convention`.
   - Confirm docs, ADRs (`docs/decisions/`), and [templates/walkthrough.md](../../../templates/walkthrough.md) disclose what changed and where AI was used.
4. **"Review Comment -> Rule" Loop ([onboarding.md](../../../docs/onboarding.md)):**
   - If the same review comment appears more than twice, propose updating `docs/standards/` and `/pb-*` skills so standards evolve continuously.
