---
name: pb-plan
description: Classify task cost/risk (S/M/L & AI Boundary Tier 1-3), draft an Implementation Plan artifact, and pause for human approval before writing code. Invoke as /pb-plan.
---

# Skill: `/pb-plan` — Implementation Plan & Tier 2 Approval Gate

**Canonical Standards:**
- [docs/standards/definition-of-done.md](../../../docs/standards/definition-of-done.md)
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)
- [docs/standards/quota-efficiency.md](../../../docs/standards/quota-efficiency.md)
- [docs/standards/testing-standard.md](../../../docs/standards/testing-standard.md)
- **Template:** [templates/implementation-plan.md](../../../templates/implementation-plan.md)

## Execution Steps

1. **Classify AI Boundary Tier & Cost Class (`trellis_budget`):**
   - Determine whether the request is `Tier 1` (autonomous), `Tier 2` (AI drafts, human approves), or `Tier 3` (human-only). Refuse any `Tier 3` delegation (production secrets, real customer PII/PAN data, prod deployments, ledger sign-off, or weakening tests).
   - Classify as **Class S** (1 file, Tier 1 only), **Class M** (2–5 files or any 1-file Tier 2 change), or **Class L** (cross-module/schema/SLA).
2. **Targeted Read-Only Inspection:**
   - Read only the specific `@file`s relevant to the task without making code edits.
3. **Create Implementation Plan Artifact:**
   - Draft the plan following [templates/implementation-plan.md](../../../templates/implementation-plan.md) (including an inline 4-section Micro-Spec for Class M tasks), listing exact files to touch and failing tests (`[REQ-NNN-XX]`) to write first.
4. **STOP for Human Approval:**
   - Request human review (`HTA` / reviewer) on the Implementation Plan artifact before modifying project code.
