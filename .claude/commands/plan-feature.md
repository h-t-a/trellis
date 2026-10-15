# Command: `/plan-feature`

Plan a new feature, change, or refactor before writing any implementation code.

**Canonical Standards:**
- [Definition of Done](../../docs/standards/definition-of-done.md) (`[DRAFT]`)
- [AI Boundary Standard](../../docs/standards/ai-boundary.md) (`[DRAFT]`)
- [Testing Standard](../../docs/standards/testing-standard.md)
- **Plan Template:** [templates/implementation-plan.md](../../templates/implementation-plan.md)

## Execution Steps

1. **Read Requirements & Check AI Boundary Tier:**
   - Classify the requested change against [ai-boundary.md](../../docs/standards/ai-boundary.md) (`Tier 1`, `Tier 2`, or `Tier 3`).
   - If the request involves any **Tier 3 (human-only)** action (production secrets, real customer data, production deployment, ledger sign-off, or weakening tests), **stop immediately** and explain why AI cannot perform it.
2. **Inspect Codebase (Read-Only):**
   - Identify affected modules, APIs, database schemas, and existing tests without modifying any source files.
3. **Draft the Implementation Plan:**
   - Using [templates/implementation-plan.md](../../templates/implementation-plan.md), document:
     - Goal and requirement traceability
     - AI Boundary tier classification (`Tier 1` / `Tier 2`)
     - Exact files to create or modify (one-line summary each)
     - Failing tests to write first (per [testing-standard.md](../../docs/standards/testing-standard.md))
     - Security and performance considerations (per [security-baseline.md](../../docs/standards/security-baseline.md) and [performance-sla.md](../../docs/standards/performance-sla.md))
     - Open questions or `[VERIFY]` items
4. **STOP for Human Approval (Mandatory Gate):**
   - Present the completed Implementation Plan to the developer.
   - **Do NOT write or edit implementation code until the human explicitly approves the plan.**
