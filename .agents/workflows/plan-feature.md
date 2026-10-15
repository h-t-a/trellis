---
description: Create an Implementation Plan artifact and obtain human approval before writing code.
---

# Workflow: `/plan-feature` `[VERIFY .agent/workflows vs .agents/workflows]`

**Canonical Standards:**
- [docs/standards/definition-of-done.md](../../docs/standards/definition-of-done.md) (`[DRAFT]`)
- [docs/standards/ai-boundary.md](../../docs/standards/ai-boundary.md) (`[DRAFT]`)
- [docs/standards/testing-standard.md](../../docs/standards/testing-standard.md)
- **Template:** [templates/implementation-plan.md](../../templates/implementation-plan.md)

## Steps

1. **Check AI Boundary Tier ([ai-boundary.md](../../docs/standards/ai-boundary.md)):**
   - Classify the task into `Tier 1` (autonomous), `Tier 2` (AI drafts, human approves), or `Tier 3` (human-only).
   - Refuse any `Tier 3` request (production secrets, real customer data, production deployments, financial/ledger sign-off, or weakening tests).
2. **Explore Read-Only:**
   - Inspect relevant files and existing tests without making code edits.
3. **Create Implementation Plan Artifact:**
   - Draft the plan following [templates/implementation-plan.md](../../templates/implementation-plan.md), listing exact files to touch, failing tests to write first, security/performance impacts, and any `[VERIFY]` questions.
4. **STOP for Human Approval:**
   - Request human review on the Implementation Plan artifact and wait for explicit approval before modifying project code.
