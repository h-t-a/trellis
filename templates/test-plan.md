# Test Plan & Performance SLA Specification: `[Application / Release Name]`

- **Application / Service:** `[e.g., Primary API Service / Web Portal]`
- **Author / QA Lead:** `[Name]`
- **Sign-Off Owner:** `[Named Owner]`
- **Date:** `[YYYY-MM-DD]`
- **Canonical Standards:** [docs/standards/testing-standard.md](../docs/standards/testing-standard.md) & [docs/standards/performance-sla.md](../docs/standards/performance-sla.md)

> [!WARNING]
> **Throughput Unit Clarification (`[VERIFY]`):**
> Do **not** enter raw stakeholder load numbers as confirmed TPS requirements unless stakeholders have explicitly confirmed whether those figures represent **TPS**, **concurrent users**, or **daily transaction volume** (see [docs/standards/performance-sla.md](../docs/standards/performance-sla.md)).

---

## 1. Functional Test Levels Scope (`TODO [TO RESEARCH]`)

| Test Level | Scope / Flows Covered | Owner | Environment | Merge / Release Gate Status |
| :--- | :--- | :--- | :--- | :--- |
| **Unit** | `[Modules / classes]` | `[Owner]` | `[Local / CI]` | `[Pass / Fail]` |
| **Integration** | `[DB / service boundaries]` | `[Owner]` | `[CI / Staging]` | `[Pass / Fail]` |
| **Contract (API)** | `[Endpoints / schemas]` | `[Owner]` | `[CI]` | `[Pass / Fail]` |
| **End-to-End (E2E)** | `[Critical user journeys]` | `[Owner]` | `[Staging]` | `[Pass / Fail]` |
| **Security (SAST / Deps / DAST)** | `[Scans executed]` | `[Owner]` | `[CI / Pre-Release]` | `[Pass / Fail]` |
| **Regression / Smoke** | `[Full regression suite]` | `[Owner]` | `[Pre-Release]` | `[Pass / Fail]` |

---

## 2. Performance SLA Targets & Little's Law Sizing

### 2.1 Little's Law Sizing Calculation
$$\text{Concurrent VUs} \approx \text{TPS} \times (\text{Response Time} + \text{Think Time})$$

- **Target Throughput ($\text{TPS}$):** `[Value]` `[VERIFY: confirmed with Management?]`
- **Expected Average Response Time (s):** `[Value]`
- **User Think Time (s):** `[Value]`
- **Calculated Concurrent Virtual Users ($\text{VUs}$):** `[Value]`

### 2.2 Agreed SLA Thresholds (Pass/Fail Criteria)

| Business Transaction Flow | Target TPS / Load | Sustained Hold Duration | `p50` Latency | `p95` Latency | `p99` Latency | Max Error Rate | Result (`PASS`/`FAIL`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| *Illustrative Example Only* | *10,000 TPS (example)* | *30 min (example)* | *< 0.5 s* | *< 2.0 s* | *< 5.0 s* | *< 0.1%* | *EXAMPLE* |
| `[e.g., Login -> Balance -> Transfer -> Confirm]` | `[Target]` | `[e.g., 30 min]` | `[< X s]` | `[< Y s]` | `[< Z s]` | `[< E %]` | `[Pending]` |

---

## 3. Performance Test Types & Execution Phases (`[TO RESEARCH]`)

- [ ] **Ramp-Up Phase:** Ramp VUs gradually to target load (`[Duration]`).
- [ ] **Sustained Acceptance Load Phase:** Hold target load steady for `[Duration]` and verify SLA percentiles and error rate.
- [ ] **Stress Phase (Breaking Point):** Push beyond target load until SLA breach to record the breaking point and failure mode.
- [ ] **Endurance / Soak Test:** Sustained run over `[Duration]` to check for memory leaks or connection pool exhaustion.
- [ ] **Spike Test:** Sudden burst from `[Baseline]` to `[Peak]` VUs.
- [ ] **Load Testing Tool Used (`TODO [TO RESEARCH: JMeter vs Grafana k6]`):** `[Tool & version]`

---

## 4. Mandatory 7-Item Performance Checklist ([docs/standards/performance-sla.md](../docs/standards/performance-sla.md))

- [ ] **1. Baseline Measurement Recorded:** Baseline metrics captured prior to change (`[Link to baseline report]`).
- [ ] **2. Production-Like Environment & Data Volume:** Test environment topology and DB row counts documented (`[Details]`).
- [ ] **3. Realistic Test Data & Multi-Step Scripts:** Synthetic accounts and realistic transaction flow used (no real customer data per Tier 3).
- [ ] **4. System Monitoring Active During Test:** CPU, memory, DB IOPS, connection pools, and GC metrics captured (`[Dashboard link]`).
- [ ] **5. Bottleneck Analysis & Re-Test Loop:** Bottlenecks identified, remediated, and re-tested (`[Notes]`).
- [ ] **6. Explicit Pass/Fail Criteria & Sign-Off Owner:** SLA table completed and signed off by `[Named Owner]`.
- [ ] **7. Execution Schedule Defined:** Test cadence recorded (`[Per release / Nightly / On major change]`).
