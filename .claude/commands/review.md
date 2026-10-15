# Command: `/review`

Review current changes against the Story-level Definition of Done, Testing Standard, and Security Baseline.

**Canonical Standards:**
- [Definition of Done](../../docs/standards/definition-of-done.md) (`[DRAFT]`)
- [Testing Standard](../../docs/standards/testing-standard.md) (`[DRAFT]`)
- [Security Baseline](../../docs/standards/security-baseline.md)
- [AI Boundary Standard](../../docs/standards/ai-boundary.md) (`[DRAFT]`)
- **Templates:** [templates/walkthrough.md](../../templates/walkthrough.md), [templates/pull_request_template.md](../../templates/pull_request_template.md)

## Execution Steps

1. **Inspect Diff and Plan Alignment:**
   - Compare git status/diff against the approved Implementation Plan ([templates/implementation-plan.md](../../templates/implementation-plan.md)). Flag any unplanned Tier 2 changes.
2. **Verify AI-Written Tests ([testing-standard.md](../../docs/standards/testing-standard.md)):**
   - Confirm no existing tests were deleted, skipped, or weakened.
   - Confirm new or modified tests contain meaningful assertions and state the requirement they verify.
3. **Verify Security Baseline ([security-baseline.md](../../docs/standards/security-baseline.md)):**
   - Check that no secrets, credentials, or real customer data exist in code, rules, skills, or `.mcp.json`.
   - Check that `CLAUDE.local.md`, `settings.local.json`, and `.env` remain gitignored.
4. **Verify Story-Level Definition of Done ([definition-of-done.md](../../docs/standards/definition-of-done.md)):**
   - Confirm lint, format, and static analysis are clean.
   - Confirm docs or an ADR (`docs/decisions/`) were updated if behavior or architecture changed.
5. **Produce Walkthrough / PR Summary & Capture Repeated Feedback:**
   - Summarize findings using [templates/walkthrough.md](../../templates/walkthrough.md) or [templates/pull_request_template.md](../../templates/pull_request_template.md), including where AI was used.
   - If a review issue has appeared **more than twice** across reviews, recommend a rule/skill update ("review comment -> rule" loop in [onboarding.md](../../docs/onboarding.md)).
