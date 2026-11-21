---
name: pb-spec
description: Use when authoring Micro-Specs or traceable functional specifications. Not for bug fixing or task planning.
metadata: {pack: core, tier: 2, quota_class: M, standards: [definition-of-done, documentation-standard, quota-efficiency, ai-boundary]}
---

# Skill: `/pb-spec` — Spec-Driven Development Workflow

**Canonical Standards & Template:**
- [templates/spec-template.md](../../templates/spec-template.md)
- [docs/standards/quota-efficiency.md](../../docs/standards/quota-efficiency.md)
- [docs/standards/ai-boundary.md](../../docs/standards/ai-boundary.md)
- [docs/standards/data-classification.md](../../docs/standards/data-classification.md)

## Execution Steps

1. **Classify Task Size & Context (`trellis_budget`, `trellis_spec`, `trellis_search_knowledge`):**
   - Call `trellis_budget` / `trellis_spec` on `@trellis-mcp` or use [quota-efficiency.md](../../docs/standards/quota-efficiency.md), and query `trellis_search_knowledge` for related prior specs/RCAs:
     - **Class M (2–5 files or 1-file Tier 2 change):** Draft **Part A (4-Section Micro-Spec)** inline inside the Implementation Plan artifact (keeps prompt cache warm in one session).
     - **Class L (cross-module, schema/architecture change, SLA impact):** Draft **Part A + Part B (Full 10-Section Spec)** in `docs/specs/NNN-<name>.md`.
2. **Assign Traceable Requirement IDs (`[REQ-NNN-XX]`):**
   - Verify prompt/context tier with `trellis_classify` and `trellis_scan`.
   - Write testable `Given / When / Then` acceptance criteria for every requirement and map each `[REQ-NNN-XX]` to a target test file and test level.
3. **Ask Only Blocking Questions & Cross-Check (`trellis_synthesize`):**
   - Ask at most 3 high-impact clarifying questions; for high-risk Class L specs, optionally compare multi-model reviews with `trellis_synthesize` to highlight architecture divergences.
4. **STOP for Tier 2 Human Approval:**
   - Wait for explicit approval from the resolved human approver (`trellis_spec` / `git config user.name` / named reviewer) before writing production code.
