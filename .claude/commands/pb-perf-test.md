---
name: pb-perf-test
description: Use when designing load tests and verifying Little's Law throughput and latency SLAs. Not for functional unit test authoring.
metadata: {pack: core, tier: 2, quota_class: M, standards: [performance-sla, complexity-and-performance]}
---

# Skill: `/pb-perf-test` — Performance Test & SLA Design

**Canonical Source of Truth:** [docs/standards/performance-sla.md](../../docs/standards/performance-sla.md)  
**Template:** [templates/test-plan.md](../../templates/test-plan.md)

## Mandatory Guidelines

1. **Do Not Assume Unconfirmed Management Targets (`[VERIFY]`):**
   - Do not treat placeholder figures (`10,000`, `1,000+`) as confirmed TPS requirements until Management clarifies whether they represent **TPS**, **concurrent users**, or **daily transaction volume** ([performance-sla.md](../../docs/standards/performance-sla.md)).
2. **Core Metrics & Little's Law (`trellis_enhance`):**
   - Clearly separate **TPS**, **QPS**, and **RPS/HPS**.
   - Size Virtual Users via Little's Law: $\text{Concurrent VUs} \approx \text{TPS} \times (\text{Response Time} + \text{Think Time})$.
   - Always report response time **percentiles (`p50`, `p95`, `p99`)** and **error rate**—never averages alone.
3. **Sustained Acceptance Hold vs. Ramp-Up:**
   - Acceptance requires **holding the target load steady for a defined duration** and checking SLA pass/fail, then pushing beyond target load (stress) to find the breaking point.
4. **Complete All 7 Mandatory Checklist Items:**
   - Use [templates/test-plan.md](../../templates/test-plan.md) to document baseline measurements, production-like environment/data volume, realistic multi-step scripts, resource monitoring (CPU, memory, DB IOPS, pools, GC), bottleneck re-test loop, pass/fail owner sign-off, and test cadence.
