# Rule: Code Style & Architecture Constraints

**Canonical Sources:**
- [Definition of Done](../../docs/standards/definition-of-done.md)
- [AI Boundary Standard](../../docs/standards/ai-boundary.md)
- [ADR 0001: Single Source of Truth](../../docs/decisions/0001-single-source-of-truth.md)

## Summary Checklist

1. **Plan Before Significant Code (`[DRAFT]`):**
   - For any Tier 2 change (feature logic, API changes, schema/migrations, auth/validation, CI/CD, dependency upgrades), produce an Implementation Plan ([templates/implementation-plan.md](../../templates/implementation-plan.md)) and obtain human approval before writing implementation code.
2. **Keep Context and Code Modular:**
   - Link to `docs/standards/` rather than copying documentation into rules or comments.
   - Keep `CLAUDE.md` under 200 lines `[VERIFIED]`.
3. **Avoid Known Anti-Patterns:**
   - Do not use vague instructions ("write good code"); state verifiable acceptance criteria.
   - Do not introduce silent error swallowing; ensure explicit error-handling patterns (`TODO [TO RESEARCH]: language-specific error-handling conventions`).
   - Preserve existing documentation and comments unrelated to your change.
4. **Quality Gate Before Completion (`[DRAFT]`):**
   - All linters, formatters, and static analysis checks must pass cleanly.
   - Update documentation or add an ADR in `docs/decisions/` whenever behavior or architecture changes.
   - Disclose what changed and where AI was used in the Walkthrough or PR description.
