# Complexity-Aware Enhancement & Performance Standard (`complexity-and-performance`)

**Status:** Working draft v0.1 `[DRAFT]`  
**Owner:** HTA  
**Sources:** [trellis-project-research-addendum-01_2026-10-16.md](../knowledge/trellis-project-research-addendum-01_2026-10-16.md) (§20), [performance-sla.md](./performance-sla.md), [evaluation-addendum-01.md](../knowledge/evaluation-addendum-01.md) (`F10`)

---

## 1. Core Principle

Time and space complexity claims are meaningless without a stated workload and baseline measurement. Always prefer the **direct approach**—the simplest data structure, query, and control flow that meets the [Performance SLA Standard](./performance-sla.md)—over clever or speculative optimizations.

---

## 2. The 7-Step Complexity & Enhancement Workflow (`[REQ-PERF-01]`)

1. **State the Workload Explicitly:**
   - Input size ($n$), expected 12-month growth factor, request frequency (TPS/QPS), latency SLA budget (`p50`, `p95`, `p99`), and memory ceiling.
   - Size concurrency using **Little's Law** ([performance-sla.md](./performance-sla.md)):
     $$\text{Concurrent VUs} \approx \text{TPS} \times (\text{Response Time} + \text{Think Time})$$
2. **Measure Before Optimizing (Baseline):**
   - Profile or benchmark the current hot path (`p50`/`p95`/`p99` latency, DB query count, memory allocation, and SQL `EXPLAIN (ANALYZE, BUFFERS)`). Do not optimize cold paths.
3. **Analyze Both I/O Complexity and Algorithmic Big-O (`F10`):**
   - **I/O & Lock Complexity (Dominant in Banking Backends):** Count database queries ($O(\text{queries})$), network RPC round-trips ($O(\text{RPCs})$), payload serialization size, and transaction lock hold duration. Eliminate $O(n)$ N+1 query/RPC loops first.
   - **Algorithmic Time & Space Big-O:** State current CPU time complexity (e.g., $O(n^2) \to O(n)$ via hash index/map) and auxiliary heap space complexity.
4. **Compare 2–3 Options in a Tradeoff Table:**
   - Evaluate each candidate on: *I/O Round-Trips*, *Time Big-O*, *Space Big-O*, *Code/Operational Complexity*, *Migration Risk*, and *Why Pick/Reject*.
5. **Select the Direct Approach:**
   - Pick the simplest option that satisfies the SLA target, and state the explicit threshold (e.g., *"revisit if $n > 10^6$ rows or `p95` exceeds 400 ms"*) that would justify a more complex design.
6. **Implement Behind Tests & Benchmark:**
   - Write functional unit/integration tests first (Red -> Green) plus a repeatable benchmark or load script verifying the hot path.
7. **Re-Measure & Record Before/After Evidence:**
   - Record before/after `p50`/`p95`/`p99`, query counts, and throughput numbers in the Walkthrough artifact ([templates/walkthrough.md](../../templates/walkthrough.md)).

---

## 3. Standard Agent Output Format (`pb-enhance` / `trellis_enhance`)

Every complexity analysis or enhancement plan must include:
1. **Workload & SLA Target** ($n$, TPS, `p95`/`p99` budget, Little's Law VUs)
2. **Baseline bottlenecks** (I/O round-trips, SQL plan / lock contention, CPU/memory Big-O)
3. **Options Tradeoff Table** (2–3 options)
4. **Recommended Direct Option & Revisit Condition**
5. **Verification & Benchmark Plan**
