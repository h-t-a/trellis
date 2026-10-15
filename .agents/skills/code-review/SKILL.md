---
name: code-review
description: >-
  Review code changes against the Story-level Definition of Done, Testing Standard,
  and AI Boundary tiers. Use before opening or approving a Pull Request.
---

# Skill: Code Review (Antigravity)

**Canonical Sources of Truth:**
- [docs/standards/definition-of-done.md](../../../docs/standards/definition-of-done.md)
- [docs/standards/testing-standard.md](../../../docs/standards/testing-standard.md)
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)
- [docs/onboarding.md](../../../docs/onboarding.md)

## Review Steps (`[DRAFT]`)

1. **Plan & Tier Alignment:**
   - Confirm an Implementation Plan artifact ([templates/implementation-plan.md](../../../templates/implementation-plan.md)) was approved by a human before significant AI-generated code.
   - Identify all Tier 2 changes requiring explicit human approval.
2. **Test Verification ([testing-standard.md](../../../docs/standards/testing-standard.md)):**
   - Verify tests at the right levels pass, state the requirement they test, and contain meaningful assertions (reviewed by a human).
   - Confirm no existing tests were deleted, skipped, or weakened.
3. **Quality, Security & Documentation Gates ([definition-of-done.md](../../../docs/standards/definition-of-done.md)):**
   - Confirm lint, format, static analysis, secret scan, and dependency scan are clean.
   - Confirm docs or ADRs (`docs/decisions/`) are updated if behavior or architecture changed.
   - Ensure the Walkthrough artifact ([templates/walkthrough.md](../../../templates/walkthrough.md)) discloses what changed and where AI was used.
4. **"Review Comment -> Rule" Loop ([onboarding.md](../../../docs/onboarding.md)):**
   - If the same review comment appears more than twice, propose updating `docs/standards/` and the thin rule pointers.
