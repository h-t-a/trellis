---
name: pb-pipeline
description: Orchestrate the end-to-end Trellis stage state machine (discover -> spec -> approve -> plan -> implement -> verify -> review -> done) with Tier 2 approval gates, loop halts, and cross-model review. Invoke as /pb-pipeline.
---

# Skill: `/pb-pipeline` — Multi-Stage Governance Pipeline

**Canonical Standards:**
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)
- [docs/standards/definition-of-done.md](../../../docs/standards/definition-of-done.md)
- [docs/standards/security-baseline.md](../../../docs/standards/security-baseline.md)

## Execution Steps

1. **Check Stage Transition via `trellis_pipeline`:**
   - Pass `current_stage`, `target_stage`, `tier` (`1`–`3`), `human_approved`, optional `approver` (auto-resolved ethically from `git config user.name` / API key label if omitted), `writer_model`, `reviewer_model`, `cross_model_review`, and recent `history`.
2. **Enforce Fail-Closed Governance Gates:**
   - **Tier 2/3 Approval Gate:** Do not enter `implement` on Tier 2+ work without explicit human approval (`PAUSED_FOR_APPROVAL`).
   - **Loop Breaker (`LOOP_DETECTED`):** If 3 consecutive retries share the same error signature or edited block, halt edits and escalate to `/pb-rca` or human guidance.
   - **Cross-Model Review:** Require `reviewer_model != writer_model` on Tier 2/3 `review` transitions so the author model never self-certifies.
3. **Record Audit & Readiness:**
   - Confirm tests and `trellis_review` pass before transitioning to `done`.
