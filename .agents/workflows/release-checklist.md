---
description: Verify release readiness against the Release-level Definition of Done and Performance SLA Standard.
---

# Workflow: `/release-checklist` `[VERIFY .agent/workflows vs .agents/workflows]`

**Canonical Standards:**
- [docs/standards/definition-of-done.md](../../docs/standards/definition-of-done.md) (Release Level `[DRAFT]`)
- [docs/standards/performance-sla.md](../../docs/standards/performance-sla.md)
- [docs/standards/security-baseline.md](../../docs/standards/security-baseline.md)
- [docs/standards/ai-boundary.md](../../docs/standards/ai-boundary.md) (`[DRAFT]`)
- **Template:** [templates/test-plan.md](../../templates/test-plan.md)

## Steps

1. **Regression & Security Verification (`[DRAFT]`):**
   - Confirm the regression and smoke test suite is green.
   - Confirm secret scans and dependency vulnerability scans are clean.
2. **Performance SLA Verification ([performance-sla.md](../../docs/standards/performance-sla.md)):**
   - Verify that a performance test report is attached showing sustained target load (not ramp-up only), response time percentiles (`p50`, `p95`, `p99`), error rate, and infrastructure monitoring metrics.
   - Check whether Management target definitions (`10,000` / `1,000+`) have been confirmed `[VERIFY]`.
3. **Human Migration Review & Rollback Plan (`[DRAFT]`):**
   - Confirm a human reviewed all database migrations and schema changes (Tier 2).
   - Confirm the rollback plan is documented.
4. **Monitoring & Named Owner Sign-Off (`[DRAFT]`):**
   - Confirm monitoring and alerts are active.
   - Record sign-off by the named release owner (AI is excluded from production deployment and financial/ledger sign-off per Tier 3).
