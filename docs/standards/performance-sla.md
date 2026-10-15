# Performance Testing & SLA Standard

**Status:** Working draft v0.1 `[SOURCE: Developers, with corrections]` `[DRAFT]`  
**Source:** [trellis-project-export.md](../knowledge/trellis-project-export.md) (Section 4.1)

---

## 1. Open Question: Management Targets (`10,000` and `1,000+`) `[VERIFY]`

> [!WARNING]
> **Unconfirmed Requirement - Do Not Treat as Finalized SLA**
> Meeting notes recorded Management targets of **10,000** for the **Wallet application** and **1,000+** for the **Web Portal**.
>
> During the meeting, the spoken term `"TUS"` was **assumed** to mean **TPS** (transactions per second). **This is an unverified assumption.**
>
> **Action Required Before Finalizing Architecture or Test Design:**
> Confirm with Management whether `10,000` (Wallet) and `1,000+` (Web Portal) mean:
> 1. **TPS** (completed business transactions per second),
> 2. **Concurrent users** (simultaneous active sessions / VUs), or
> 3. **Daily transaction volume** (total transactions per day).
>
> Each interpretation changes system architecture, infrastructure sizing, and load-test design completely.

---

## 2. Core Performance Terminology `[SOURCE: Developers, with corrections]`

| Term | Definition | Notes |
| :--- | :--- | :--- |
| **TPS** (Transactions Per Second) | Completed end-to-end business transactions per second. | Example: a complete `Login -> Balance -> Transfer -> Confirm` flow counts as 1 business transaction. |
| **QPS** (Queries Per Second) | Queries per second hitting the database or search layer. | One business transaction (1 TPS) typically generates multiple database queries (several QPS). |
| **RPS / HPS** (Requests or Hits Per Second) | Raw HTTP requests or hits per second reaching the web/API tier. | One user action or transaction often triggers multiple HTTP requests. |
| **VUs** (Virtual Users) | Concurrent simulated users executed by the load-testing tool. | Connected to throughput via Little's Law (see Section 3). |
| **Response Time Percentiles (`p50`, `p95`, `p99`)** | The latency below which 50%, 95%, or 99% of requests complete. | **Always report percentiles, not only averages.** Averages hide slow tail requests that hurt real users. |
| **Error Rate** | Percentage of failed or timed-out requests/transactions during the test window. | Must be explicitly defined as part of the pass/fail SLA, never treated as an afterthought. |
| **SLA / SLO** | Service Level Agreement / Objective: the formal pass/fail threshold for a performance test. | Combines throughput, sustained duration, response-time percentiles, and maximum error rate. |

---

## 3. Sizing Relationship: Little's Law `[SOURCE: Developers, with corrections]`

Use **Little's Law** to relate concurrent Virtual Users (VUs), throughput (TPS), response time, and user think time:

$$\text{Concurrent VUs} \approx \text{TPS} \times (\text{Response Time} + \text{Think Time})$$

- **$\text{TPS}$**: Target completed transactions per second.
- **$\text{Response Time}$**: Average end-to-end transaction duration (in seconds).
- **$\text{Think Time}$**: Average pause between user actions (in seconds) in realistic user journeys.

---

## 4. SLA Specification Template (With Example Numbers Only) `[DRAFT]`

> [!NOTE]
> The numbers below (`10,000 TPS sustained 30 min, p95 < 2 s, error rate < 0.1 %`) are **illustrative examples only** from the knowledge export-they are **not** agreed project targets. Replace the placeholders in [test-plan.md](../../templates/test-plan.md) once Management confirms the target metrics.

**Illustrative Example SLA Statement:**
> *"10,000 TPS sustained for 30 minutes, with p95 response time < 2.0 s, p99 < [X] s, and error rate < 0.1%."* *(Example only - not an approved target)*

### Project SLA Table Template

| Application / Flow | Target Throughput (`[VERIFY: TPS vs Users vs Daily Volume]`) | Sustained Hold Duration | Latency `p50` | Latency `p95` | Latency `p99` | Max Error Rate | Sign-Off Owner |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| *Example: Wallet Transfer Flow (EXAMPLE ONLY)* | *10,000 TPS (example)* | *30 min (example)* | *< 0.5 s (example)* | *< 2.0 s (example)* | *< 5.0 s (example)* | *< 0.1% (example)* | *[Named Owner]* |
| **Wallet Application** | `TODO [VERIFY with Management]` | `TODO` | `TODO` | `TODO` | `TODO` | `TODO` | `TODO` |
| **Web Portal** | `TODO [VERIFY with Management]` | `TODO` | `TODO` | `TODO` | `TODO` | `TODO` | `TODO` |

---

## 5. Acceptance Methodology & Test Types

### 5.1 Ramp-Up vs. Acceptance Hold (Correction to Earlier Notes) `[SOURCE: Developers, with corrections]`
- **Correction:** Merely *"ramping VUs up until the target is reached"* describes only the **ramp-up phase**, not an acceptance test.
- **True Acceptance Criteria:**
  1. Ramp up to the target load.
  2. **Hold the target load steady for a defined duration** (e.g., 30–60 minutes) and verify that all SLA metrics (`p50`/`p95`/`p99`, TPS, error rate) pass throughout the sustained window.
  3. In a separate **stress phase**, push beyond the target load to identify the system's breaking point and failure mode.

### 5.2 Performance Test Types `[TO RESEARCH]`
- **Load Test:** Verify system behavior under expected peak target load held for a sustained duration.
- **Stress Test:** Push load beyond target capacity to find the breaking point and verify graceful degradation/recovery.
- **Endurance / Soak Test:** Run sustained load over an extended period to detect memory leaks, connection pool exhaustion, or storage growth.
- **Spike Test:** Subject the system to sudden, extreme bursts of traffic.
- **Additional Test Types (`TODO [TO RESEARCH]`):**
  - **Volume Testing** (behavior against large database table sizes / historical data volumes)
  - **Scalability Testing** (horizontal/vertical scaling efficiency)
  - **Capacity-Planning Testing** (determining infrastructure required for future growth)

### 5.3 Load Testing Tooling Comparison `[TO RESEARCH]`
- `TODO [TO RESEARCH]`: Compare **Apache JMeter**, **Grafana k6**, and other candidate tools against team skills, CI integration, protocol support, and reporting requirements.

---

## 6. Mandatory Checklist Items (Missing from Original Notes) `[SOURCE: Developers, with corrections]`

Every performance test plan and execution must address these seven items that were missing from the initial meeting notes:

1. **Baseline Measurement Before Changes:** Record baseline throughput, latency percentiles, and resource usage before introducing major code or architectural changes.
2. **Production-Like Test Environment and Data Volume:** Execute performance tests against an environment whose topology, sizing ratio, and database row counts reflect production-not an empty database.
3. **Realistic Test Data and Transaction Scripts:** Model multi-step user journeys (e.g., `Login -> Balance Inquiry -> Transfer -> Confirm`) with realistic think times and varied accounts rather than hitting a single cached endpoint repeatedly.
4. **System Monitoring During Tests:** Actively capture CPU, memory, disk/DB IOPS, database connection pools, thread pools, and garbage collection (GC) metrics alongside load-generator metrics.
5. **Bottleneck Analysis and Re-Test Loop:** Document identified bottlenecks, apply targeted fixes, and re-run the test against the baseline to verify improvement.
6. **Explicit Pass/Fail Criteria and Sign-Off Owner:** Define numeric SLA thresholds prior to test execution and assign a named sign-off owner.
7. **Execution Cadence:** Define when performance tests run (`TODO [TO RESEARCH]`: e.g., per release, nightly soak, or on major architectural/database changes).
