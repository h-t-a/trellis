# Implementation Plan: `[Feature / Change Title]`

- **Author / Developer:** `[Name]`
- **Date:** `[YYYY-MM-DD]`
- **Ticket / Requirement ID:** `[TICKET-ID]`
- **AI Tool Used:** `[Claude Code / Antigravity IDE]`
- **AI Boundary Tier ([docs/standards/ai-boundary.md](../docs/standards/ai-boundary.md)):** `[Tier 1: Autonomous | Tier 2: Human Approval Required]`

> [!IMPORTANT]
> **Human Review Gate (`[DRAFT]`):**
> Per [docs/standards/definition-of-done.md](../docs/standards/definition-of-done.md), a human developer must critically review and approve this Implementation Plan **before** significant AI-generated code is written. Confirm no **Tier 3 (Human-Only)** boundaries are crossed.

---

## 1. Objective & Problem Statement

- **Goal:** `[Concise summary of what this change accomplishes and why]`
- **Acceptance Criteria:**
  1. `[Criterion 1]`
  2. `[Criterion 2]`

---

## 2. AI Boundary & Risk Classification

- [ ] **No Tier 3 Violations:** Confirmed this task does **not** touch production secrets, real customer/production data, production deployments, financial/ledger sign-off, security exceptions, or test weakening ([docs/standards/ai-boundary.md](../docs/standards/ai-boundary.md)).
- [ ] **Tier 2 Areas Highlighted for Human Review:**
  - `[ ] Feature / business logic`
  - `[ ] API contract changes`
  - `[ ] Database schema / migration scripts`
  - `[ ] Authentication / authorization / input validation`
  - `[ ] Dependency upgrades or CI/CD configuration`

---

## 3. Proposed Changes (File-by-File)

| File Path | Action (`NEW` / `MODIFY` / `DELETE`) | One-Line Description of Change |
| :--- | :--- | :--- |
| `[path/to/file]` | `[MODIFY]` | `[What will change and why]` |
| `[path/to/test_file]` | `[NEW]` | `[Failing test verifying Requirement X]` |

---

## 4. Verification & Test Plan ([docs/standards/testing-standard.md](../docs/standards/testing-standard.md))

- **Failing Tests to Write First (Red -> Green):**
  - `[Test name / file]`: Verifies `[Requirement / Bug scenario]`
- **Test Levels Covered:** `[Unit / Integration / Contract / E2E / Performance / Security]`
- **Performance & Security Impact:**
  - `[Note any impact on latency/TPS SLAs or security controls]`

---

## 5. Open Questions, `[VERIFY]` Items & Human Critique

- **Open Questions / `[VERIFY]` Items:**
  - `[List any unconfirmed assumptions or items needing human decision]`
- **Developer Critique Notes (Skill-Growth Practice):**
  - *What I changed or corrected in the AI's initial plan before approving:* `[Notes]`
- **Human Plan Approval:**
  - [ ] Approved by `[Reviewer Name]` on `[YYYY-MM-DD]`
