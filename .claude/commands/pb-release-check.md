---
name: pb-release-check
description: Verify release readiness against the Release-level Definition of Done, Performance SLA Standard, migration review, and rollback plan. Invoke as /pb-release-check.
---

# Skill: `/pb-release-check` — Release-Level Readiness Gate

**Canonical Standards:**
- [docs/standards/definition-of-done.md](../../docs/standards/definition-of-done.md) (Release Level)
- [docs/standards/performance-sla.md](../../docs/standards/performance-sla.md)
- [docs/standards/security-baseline.md](../../docs/standards/security-baseline.md)
- [docs/standards/ai-boundary.md](../../docs/standards/ai-boundary.md)
- **Template:** [templates/test-plan.md](../../templates/test-plan.md)

## Execution Steps

1. **Regression & Security Verification:**
   - Confirm the regression and smoke test suites are green and secret/dependency vulnerability scans are clean.
2. **Performance SLA Verification ([performance-sla.md](../../docs/standards/performance-sla.md)):**
   - Verify a performance test report is attached showing sustained target load (not ramp-up only), response time percentiles (`p50`, `p95`, `p99`), error rate, and infrastructure monitoring metrics.
3. **Human Migration Review & Rollback Plan (Tier 2):**
   - Confirm a human engineer reviewed all database migrations and schema changes and that the rollback procedure is documented and tested.
4. **Monitoring & Named Owner Sign-Off (Tier 3 Boundary):**
   - Confirm monitoring and alerts are active and record sign-off by the named release owner (`HTA` / release lead; AI is excluded from prod deployment and financial/ledger sign-off per Tier 3).
