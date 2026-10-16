---
name: pb-review
description: Pre-PR review check against Story Definition of Done, AI Boundary Tiers 1-3, Security Baseline, Conventional Commits, and [REQ-NNN] test traceability. Invoke as /pb-review.
---

# Skill: `/pb-review` — Pre-PR Verification & Walkthrough Gate

**Canonical Standards:**
- [docs/standards/definition-of-done.md](../../../docs/standards/definition-of-done.md)
- [docs/standards/testing-standard.md](../../../docs/standards/testing-standard.md)
- [docs/standards/security-baseline.md](../../../docs/standards/security-baseline.md)
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)
- [docs/standards/git-convention.md](../../../docs/standards/git-convention.md)
- **Templates:** [templates/walkthrough.md](../../../templates/walkthrough.md), [templates/pull_request_template.md](../../../templates/pull_request_template.md)

## Execution Steps (Quota Guard: Read `git diff`, Never Scan the Whole Repo)

1. **Inspect Only the Current Diff:**
   - Run `git diff HEAD` (and `git status --short`) or pass the diff to the `trellis_review` MCP tool.
2. **Check AI Boundary & Test Integrity ([testing-standard.md](../../../docs/standards/testing-standard.md)):**
   - Verify **zero** existing tests were deleted, skipped (`@Disabled`, `.skip`, `xit`, `unittest.skip`), or weakened (Tier 3 block).
   - Verify every new test cites its `[REQ-NNN-XX]` requirement ID and has meaningful assertions.
3. **Check Security Baseline & Git Convention:**
   - Confirm no secrets, tokens, or real customer data appear in the diff, and local config files remain gitignored.
   - Verify the proposed commit message follows `<type>(<scope>): <lowercase imperative summary>` (≤ 72 chars, no trailing period).
4. **Produce Walkthrough Artifact:**
   - Generate or update the Walkthrough artifact ([templates/walkthrough.md](../../../templates/walkthrough.md)) stating what changed, verification evidence, and where AI was used.
