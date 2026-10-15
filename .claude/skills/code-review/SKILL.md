---
name: code-review
description: >-
  Review code changes against the Story-level Definition of Done, Testing Standard,
  and AI Boundary tiers. Use before opening or approving a Pull Request.
---

# Skill: Code Review

**Canonical Sources of Truth:**
- [docs/standards/definition-of-done.md](../../../docs/standards/definition-of-done.md)
- [docs/standards/testing-standard.md](../../../docs/standards/testing-standard.md)
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)
- [docs/onboarding.md](../../../docs/onboarding.md)

## When to Use

Activate this skill when reviewing a feature branch, uncommitted diff, Walkthrough artifact, or Pull Request.

## Review Procedure (`[DRAFT]`)

1. **Plan & Tier Check:**
   - Confirm an Implementation Plan ([templates/implementation-plan.md](../../../templates/implementation-plan.md)) was reviewed by a human before significant AI-generated code.
   - Highlight all Tier 2 changes (feature logic, API contracts, DB migrations, auth/validation, dependency upgrades) requiring explicit human sign-off.
2. **Test Quality & Integrity Check:**
   - Verify tests at the required levels exist and pass.
   - Inspect AI-written tests to ensure assertions verify real behavior and cite the requirement tested.
   - Verify no existing tests were deleted, skipped, or weakened.
3. **Static Analysis, Security & Docs Check:**
   - Confirm linters, formatters, static analysis, secret scans, and dependency scans are clean.
   - Check if behavior or architecture changes require updates to `docs/` or a new ADR in `docs/decisions/`.
4. **AI Usage Disclosure:**
   - Confirm the Walkthrough ([templates/walkthrough.md](../../../templates/walkthrough.md)) or PR description ([templates/pull_request_template.md](../../../templates/pull_request_template.md)) clearly states what changed and where AI was used.
5. **"Review Comment -> Rule" Loop:**
   - If the same review comment has occurred **more than twice**, propose codifying it in `docs/standards/` and `.claude/rules/` or `.agents/rules/`.
