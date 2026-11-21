---
name: pb-enhance
description: Use when profiling workloads, I/O round-trips, and Big-O complexity. Not for basic bug fixing or documentation changes.
metadata: {pack: core, tier: 2, quota_class: M, standards: [complexity-and-performance, performance-sla, testing-standard]}
---

# Skill: `/pb-enhance` — Complexity-Aware Enhancement & Analysis

**Canonical Standards:**
- [docs/standards/complexity-and-performance.md](../../../docs/standards/complexity-and-performance.md)
- [docs/standards/performance-sla.md](../../../docs/standards/performance-sla.md)
- [docs/standards/testing-standard.md](../../../docs/standards/testing-standard.md)

## Execution Steps (absorbs `/pb-complexity`)

1. **Select Mode (`analyze` vs. `implement`) & State Workload (`[REQ-PERF-01]`):**
   - Call `trellis_enhance` on `@trellis-mcp` or state: data size ($n$), 12-month growth, TPS/QPS, `p95`/`p99` SLA budget, and Little's Law concurrency ($\text{VUs} \approx \text{TPS} \times (\text{Response Time} + \text{Think Time})$).
2. **Baseline & Bottleneck Analysis (Named Functions Only):**
   - Measure or inspect only the named `@file` / hot function (never scan the whole repo).
   - Report **both** **I/O & Lock Complexity** ($O(\text{queries})$, $O(\text{RPCs})$, lock hold duration, SQL `EXPLAIN`) and **Algorithmic Big-O** (CPU time and heap space).
3. **Options Tradeoff Table (2–3 Options):**
   - Compare candidates across I/O round-trips, Time/Space Big-O, code complexity, and migration risk. Recommend the **direct approach** (simplest option meeting the SLA) and state its revisit threshold.
4. **Mode Gate:**
   - If invoked in **`analyze` mode**, stop here and output the report.
   - If invoked in **`implement` mode**, obtain human approval on the chosen option, write failing functional + benchmark tests first, implement, and record before/after metrics in the Walkthrough artifact.
