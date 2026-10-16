# Fast Root-Cause Analysis (RCA) & Incident Playbook (`rca-playbook`)

**Status:** Working draft v0.1 `[DRAFT]`  
**Owner:** HTA  
**Sources:** [trellis-project-research-addendum-01_2026-10-16.md](../knowledge/trellis-project-research-addendum-01_2026-10-16.md) (§18), [evaluation-addendum-01.md](../knowledge/evaluation-addendum-01.md) (`F04`, `F10`)

---

## 1. Objective

Find the shortest path from a reported symptom to a **proven root cause** with the fewest tokens and minutes—never guessing a fix before reproducing or proving the fault.

---

## 2. Mandatory Tier 3 Log & Context Redaction Gate (`[REQ-RCA-01]`)

Before attaching `@terminal`, `@logfile`, stack traces, or database query outputs to any AI prompt or `trellis_rca` tool call (see [ai-boundary.md](./ai-boundary.md) and [security-baseline.md](./security-baseline.md)):

1. **Zero Unredacted Customer or Production Data:** Never include real customer PII, primary account numbers (PAN / 13–19 digit card numbers), national IDs, account balances, or session tokens. Replace sensitive values with synthetic placeholders (`<REDACTED_PAN>`, `<USER_ID_1>`, `<REDACTED_TOKEN>`).
2. **Zero Credentials:** Never paste `.env` contents, connection strings with passwords, private keys, or API keys (`Bearer ...`, `sk-...`, `AIza...`).
3. **Production Incident Boundary (Tier 3):** During live production incidents, AI operates strictly in **read-only hypothesis mode**. A human engineer executes all production diagnostic queries, rollbacks, and mitigations.

---

## 3. The 9-Step Fast RCA Sequence (`[REQ-RCA-02]`)

1. **Restate the Symptom (One Line):** State *expected vs. actual*, *where* (module/endpoint/environment), *since when* (commit/release/timestamp), and *how often* (deterministic, intermittent, load-dependent).
2. **Reproduce First:** Reproduce via a failing test, local request, or deterministic replay. If it cannot be reproduced yet, state that explicitly and gather evidence—**do not guess a fix**.
3. **Collect Cheap Evidence First:** Inspect the stack trace, failing test output, sanitized logs around the failure window, last known good version, and recent commits (`/diff`, `git log -n 5`, `git blame`) before scanning source files.
4. **Narrow the Search Space (Bisect):** Use `git bisect`, input minimization, component isolation, or environment diffing (working vs. failing config) to cut the fault domain in half at each step.
5. **Form at Most 3 Ranked Hypotheses:** For each hypothesis, state:
   - The suspected mechanism, and
   - The **single cheapest discriminating check** that would **disprove** it.
6. **Run the Cheapest Discriminating Check First:** Execute one targeted check at a time (a single assertion, unit test, `EXPLAIN (ANALYZE, BUFFERS)` query plan, or log line). Stop after **3 failed hypotheses** and re-plan (`/grill-me`).
7. **Prove the Cause with a Failing Test (Red):** Write an automated test referencing the requirement/bug ID that fails strictly because of the proven root cause.
8. **Apply the Minimal Fix (Green) & Prevent Recurrence:** Ask *"Why did this reach us?"* (missing test case, weak boundary validation, ambiguous spec) and codify a test or rule (`/learn`).
9. **Structured RCA Report:** Output *Symptom*, *Proven Root Cause*, *Discriminating Evidence*, *Minimal Fix Diff*, *Risk/Blast Radius*, and *Regression Test Added*.

---

## 4. Enterprise Banking & Concurrency Fault Checklist (`[REQ-RCA-03]`)

Check these high-frequency enterprise backend causes early:

- **Database & Query Path:** N+1 queries, missing composite indexes (`Seq Scan` on large tables), unbounded result sets without pagination, stale read-replica lag.
- **Concurrency, Locks & Idempotency:** Race conditions under concurrent requests, inconsistent lock acquisition order (deadlocks), long transactions holding row/table locks during external HTTP calls, missing idempotency keys on payment/transfer retries, wrong transaction isolation level (`READ COMMITTED` vs. `REPEATABLE READ` / `SERIALIZABLE`).
- **Resource & Pool Exhaustion:** Database connection pool starvation, thread pool / event-loop blocking, unclosed streams/cursors, chatty synchronous RPCs inside loops.

---

## 5. Anti-Patterns (Prohibited)

- Proposing code edits before reproducing or isolating the fault.
- Scanning the entire repository instead of starting from the stack trace or `git diff`.
- Changing multiple unrelated variables at once.
- Deleting, skipping, or weakening an existing test to make the build pass (Tier 3 violation).
- Looping past 3 failed fix attempts without stopping to re-plan.
