---
name: perf-test
description: >-
  Design, size, and evaluate performance tests using the Performance SLA Standard
  (Little's Law, percentiles, error rates, and sustained load acceptance).
---

# Skill: Performance Test & SLA Design

**Canonical Source of Truth:** [docs/standards/performance-sla.md](../../../docs/standards/performance-sla.md)  
**Template:** [templates/test-plan.md](../../../templates/test-plan.md)

## When to Use

Activate this skill when planning load/stress/soak/spike tests, sizing Virtual Users (VUs), reviewing performance test results, or preparing release-level SLA evidence.

## Mandatory Guidelines

1. **Do Not Assume Unconfirmed Management Targets (`[VERIFY]`):**
   - Never treat the meeting numbers (`10,000` for Wallet, `1,000+` for Web Portal) as confirmed TPS requirements until Management confirms whether they mean **TPS**, **concurrent users**, or **daily transaction volume** (see Section 1 of [performance-sla.md](../../../docs/standards/performance-sla.md)).
2. **Use Correct Metrics & Little's Law:**
   - Distinguish **TPS** (business transactions/sec), **QPS** (DB queries/sec), and **RPS/HPS** (HTTP requests/sec).
   - Size VUs using Little's Law: $\text{Concurrent VUs} \approx \text{TPS} \times (\text{Response Time} + \text{Think Time})$.
   - Report latency using **percentiles (`p50`, `p95`, `p99`)** and **error rate**-never averages alone.
3. **Acceptance Hold vs. Ramp-Up:**
   - Ramp-up alone is not acceptance. Acceptance requires **holding the target load steady for a defined duration** (e.g., 30 min) and checking SLA pass/fail, followed by a separate stress phase to find the breaking point.
4. **Verify All 7 Mandatory Checklist Items ([performance-sla.md](../../../docs/standards/performance-sla.md)):**
   - Baseline measurement before changes
   - Production-like test environment and data volume
   - Realistic test data and multi-step scripts (e.g., `Login -> Balance -> Transfer -> Confirm`)
   - System monitoring during tests (CPU, memory, DB IOPS, connection pools, GC)
   - Bottleneck analysis and re-test loop
   - Explicit pass/fail criteria and named sign-off owner
   - Defined execution schedule (per release, nightly, or major change)
