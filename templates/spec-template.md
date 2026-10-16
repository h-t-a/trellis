# Specification Template (`pb-spec` / `trellis_spec`)

- **Spec ID:** `SPEC-[NNN]`
- **Title:** `[Feature or Enhancement Title]`
- **Author:** `[HTA / Developer Name]`
- **Date:** `[YYYY-MM-DD]`
- **Task Cost Class ([docs/standards/quota-efficiency.md](../docs/standards/quota-efficiency.md)):** `[Class M: Micro-Spec | Class L: Full Spec]`
- **AI Boundary Tier ([docs/standards/ai-boundary.md](../docs/standards/ai-boundary.md)):** `[Tier 1 | Tier 2: Human Approval Required]`
- **Status:** `[DRAFT | APPROVED | IMPLEMENTED]`

> [!IMPORTANT]
> **Dual-Tier Spec Rule (`F12`):**
> - **For Class M Tasks (2–5 files, single module):** Fill out **Part A (4-Section Micro-Spec)** only (either standalone or inline inside your Implementation Plan artifact).
> - **For Class L Tasks (cross-module, architecture/schema changes, high SLA impact):** Complete **Part A + Part B (Full 10-Section Spec)** in `docs/specs/NNN-<name>.md` and obtain human approval before planning/coding.

---

## Part A: Core Micro-Spec (Required for Both Class M and Class L)

### 1. Problem & Goal ( Non-Goals)
- **Problem Statement:** `[What is broken, missing, or slow, and who is impacted?]`
- **Goals:**
  - `[Goal 1]`
- **Non-Goals (Out of Scope):**
  - `[Explicitly excluded item 1]`

### 2. Numbered Requirements & Testable Acceptance Criteria (`Given / When / Then`)
Every requirement must carry a unique `[REQ-NNN-XX]` ID that will be cited in automated test names/docstrings:

- **`[REQ-NNN-01]`:** `[Requirement statement]`
  - **Given** `[precondition / state]`
  - **When** `[action / input]`
  - **Then** `[expected observable outcome]`
- **`[REQ-NNN-02]`:** `[Requirement statement]`
  - **Given** `[precondition / state]`
  - **When** `[action / error condition]`
  - **Then** `[expected error handling / rollback]`

### 3. Security, Privacy & AI-Boundary Check ([ai-boundary.md](../docs/standards/ai-boundary.md))
- [ ] **No Tier 3 Violations:** No production secrets, unredacted customer PII/PAN data, production DB mutations, or financial/ledger sign-off delegated to AI.
- **Tier 2 Human Review Areas Touched:** `[Auth / Input Validation / DB Schema / API Contract / CI-CD / None]`

### 4. Traceability & Test Plan ([testing-standard.md](../docs/standards/testing-standard.md))
| Requirement ID | Test Level (`Unit`/`Integration`/`Contract`/`Perf`) | Target Test File & Test Name |
| :--- | :--- | :--- |
| `[REQ-NNN-01]` | `[Unit / Integration]` | `[path/to/test_file :: test_req_nnn_01_...]` |
| `[REQ-NNN-02]` | `[Unit / Integration]` | `[path/to/test_file :: test_req_nnn_02_...]` |

---

## Part B: Extended Sections (Required for Class L Tasks Only)

### 5. Context & Architecture Background
- `[Current system behavior, upstream/downstream dependencies, and relevant ADRs]`

### 6. Edge Cases, Concurrency & Failure Modes
- **Idempotency & Retries:** `[How duplicate requests or network timeouts are handled]`
- **Concurrency & Locking:** `[Isolation level, optimistic/pessimistic locks, race condition guards]`
- **Boundary Inputs:** `[Null/empty, max payload size, malformed input, rate limits]`

### 7. Performance SLA & Complexity Constraints ([performance-sla.md](../docs/standards/performance-sla.md))
- **Target Workload ($n$, TPS, Concurrency):** `[e.g., 10,000 TPS Wallet / 1,000+ TPS Web Portal]`
- **Latency & Error Budget:** `[e.g., p95 < 500 ms, p99 < 1.5 s, error rate < 0.1%]`
- **I/O & Algorithmic Complexity Target:** `[Max DB queries/request, index requirements, Big-O ceiling]`

### 8. Design Notes & Alternatives Considered
- **Chosen Direct Approach:** `[Summary of design]`
- **Alternatives Rejected:** `[Option B and why it was rejected]`

### 9. Rollout, Migration & Rollback Plan
- **Database / Config Migrations:** `[Backward-compatible steps]`
- **Feature Flag / Canary Strategy:** `[How to enable safely]`
- **Rollback Procedure:** `[Exact steps to revert within SLA if errors spike]`

### 10. Open Questions & Human Sign-Off
- **Open Questions:** `[Must be resolved before implementation starts]`
- **Human Approval:**
  - [ ] Approved by `HTA` on `[YYYY-MM-DD]`
