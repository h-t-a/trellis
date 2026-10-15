---
description: Review changes and generate a Walkthrough artifact against the Definition of Done.
---

# Workflow: `/review` `[VERIFY .agent/workflows vs .agents/workflows]`

**Canonical Standards:**
- [docs/standards/definition-of-done.md](../../docs/standards/definition-of-done.md) (`[DRAFT]`)
- [docs/standards/testing-standard.md](../../docs/standards/testing-standard.md) (`[DRAFT]`)
- [docs/standards/security-baseline.md](../../docs/standards/security-baseline.md)
- **Templates:** [templates/walkthrough.md](../../templates/walkthrough.md), [templates/pull_request_template.md](../../templates/pull_request_template.md)

## Steps

1. **Compare Changes Against Approved Plan:**
   - Check `git diff` against the approved Implementation Plan ([templates/implementation-plan.md](../../templates/implementation-plan.md)).
2. **Verify AI-Written Tests ([testing-standard.md](../../docs/standards/testing-standard.md)):**
   - Confirm no existing tests were deleted, skipped, or weakened.
   - Flag all AI-written test assertions for human review and confirm each test cites the requirement it verifies.
3. **Verify Security Baseline ([security-baseline.md](../../docs/standards/security-baseline.md)):**
   - Confirm no secrets or real customer data were introduced and local override files remain gitignored.
4. **Verify Story-Level Definition of Done ([definition-of-done.md](../../docs/standards/definition-of-done.md)):**
   - Confirm lint, format, and static analysis are clean, and docs/ADRs were updated if behavior or architecture changed.
5. **Produce Walkthrough Artifact & Check "Review Comment -> Rule" Loop:**
   - Generate a Walkthrough artifact using [templates/walkthrough.md](../../templates/walkthrough.md) disclosing what changed and where AI was used.
   - If a review finding has occurred more than twice, propose a rule or skill update ([docs/onboarding.md](../../docs/onboarding.md)).
