# Command: `/release-checklist`

Verify a release candidate against the Release-level Definition of Done and Performance SLA Standard.

**Canonical Standards:**
- [Definition of Done](../../docs/standards/definition-of-done.md) (Section 2: Release Level `[DRAFT]`)
- [Performance Testing & SLA Standard](../../docs/standards/performance-sla.md)
- [Security Baseline](../../docs/standards/security-baseline.md)
- [AI Boundary Standard](../../docs/standards/ai-boundary.md) (`[DRAFT]`)
- **Template:** [templates/test-plan.md](../../templates/test-plan.md)

## Execution Steps

1. **Check Regression & Security Gates (`[DRAFT]`):**
   - Confirm the full regression/smoke suite is green.
   - Confirm secret scanning and dependency vulnerability scans are clean ([security-baseline.md](../../docs/standards/security-baseline.md)).
2. **Verify Performance SLA Report ([performance-sla.md](../../docs/standards/performance-sla.md)):**
   - Confirm a performance test was executed in a production-like environment holding target load for the sustained SLA window (not ramp-up only).
   - Confirm the attached report includes **response time percentiles (`p50`, `p95`, `p99`)**, **error rate**, and **system resource monitoring** (CPU, memory, DB IOPS, connection pools, GC).
   - Check if Management target definitions (`10,000` / `1,000+` TPS vs concurrent users vs daily volume) have been confirmed `[VERIFY]`.
3. **Verify Human Review of Migrations & Rollback Plan (`[DRAFT]`):**
   - Confirm a human has reviewed all database schema changes and migration scripts (Tier 2).
   - Confirm a step-by-step rollback plan is documented.
4. **Verify Operational Readiness & Sign-Off (`[DRAFT]`):**
   - Confirm monitoring dashboards and alerts are in place.
   - Confirm sign-off by the named release owner (note: AI is strictly excluded from production deployment and financial/ledger sign-off per Tier 3 of [ai-boundary.md](../../docs/standards/ai-boundary.md)).
