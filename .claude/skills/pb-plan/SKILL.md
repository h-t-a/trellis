---
name: pb-plan
description: Use when scoping tasks, estimating cost, and requesting Tier 2 human approval. Not for bug diagnosis or writing production code.
metadata: {pack: core, tier: 2, quota_class: M, standards: [definition-of-done, ai-boundary, quota-efficiency, testing-standard]}
---

# Skill: `/pb-plan` — Implementation Plan & Tier 2 Approval Gate

**Canonical Standards:**
- [docs/standards/definition-of-done.md](../../../docs/standards/definition-of-done.md)
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)
- [docs/standards/quota-efficiency.md](../../../docs/standards/quota-efficiency.md)
- [docs/standards/testing-standard.md](../../../docs/standards/testing-standard.md)
- [docs/standards/data-classification.md](../../../docs/standards/data-classification.md)
- [docs/standards/git-convention.md](../../../docs/standards/git-convention.md)
- **Template:** [templates/implementation-plan.md](../../../templates/implementation-plan.md)

## Execution Steps

1. **Classify AI Boundary Tier, Data Tier & Cost Class (`trellis_budget`, `trellis_classify`, `trellis_route_model`):**
   - Determine whether the request is `Tier 1` (autonomous), `Tier 2` (AI drafts, human approves), or `Tier 3` (human-only). Refuse any `Tier 3` delegation (production secrets, real customer PII/PAN data, prod deployments, ledger sign-off, or weakening tests).
   - Classify as **Class S** (1 file, Tier 1 only), **Class M** (2–5 files or any 1-file Tier 2 change), or **Class L** (cross-module/schema/SLA).
   - Verify data classification (`trellis_classify`) and select an approved commercial/on-prem model (`trellis_route_model`).
2. **Targeted Read-Only & Semantic Context Inspection (`trellis_search_knowledge`):**
   - Query `trellis_search_knowledge` for matching standards or prior RCAs, then read only the specific `@file`s relevant to the task without making code edits.
3. **Create Implementation Plan Artifact:**
   - Resolve the human author/approver ethically (`trellis_pipeline` / `git config user.name` / OS display name, falling back to asking the user — never hardcode a single author) and draft the plan following [templates/implementation-plan.md](../../../templates/implementation-plan.md) (including an inline 4-section Micro-Spec for Class M tasks), listing branch name (`<type>/<slug>` per `/pb-git-convention`), exact files to touch, cross-model reviewer assignment (`trellis_pipeline`), and failing tests (`[REQ-NNN-XX]`) to write first.
4. **STOP for Human Approval (`trellis_pipeline`):**
   - Request human review from the resolved approver on the Implementation Plan artifact (`PAUSED_FOR_APPROVAL`) before modifying project code.
