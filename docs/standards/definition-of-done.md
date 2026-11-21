# Definition of Done (DoD) `[DRAFT]`

**Status:** Working draft v0.1 `[DRAFT, to research and finalize]`  
**Source:** Canonical Trellis engineering standard (`docs/standards/`)

> [!NOTE]
> Both checklists below are tagged `[DRAFT]` and must be reviewed and finalized with the engineering team during Phase 1 research.

---

## 1. Story / Change Level Checklist `[DRAFT]`

Every feature story, bug fix, or pull request must satisfy all of the following before merge:

- [ ] **Implementation Plan Reviewed Before Code `[DRAFT]`:** An Implementation Plan (Antigravity artifact or [implementation-plan.md](../../templates/implementation-plan.md)) was reviewed and approved by a human before significant AI-generated code was written.
- [ ] **Human Code Review `[DRAFT]`:** All code changes have been critically reviewed by a human developer.
- [ ] **Tests Written and Passing in CI `[DRAFT]`:** Tests at the appropriate levels (see [testing-standard.md](./testing-standard.md)) are written, verify meaningful assertions, and pass in CI.
- [ ] **Lint, Format, and Static Analysis Clean `[DRAFT]`:** All linters, code formatters, and static analysis checks pass with zero unapproved warnings or errors.
- [ ] **Secret Scan and Dependency Scan Clean `[DRAFT]`:** Pre-commit/CI secret detection and dependency vulnerability scans pass cleanly (see [security-baseline.md](./security-baseline.md)).
- [ ] **Documentation or ADR Updated `[DRAFT]`:** Project documentation or an Architecture Decision Record (`docs/decisions/`) is updated whenever system behavior, public APIs, or architecture changed.
- [ ] **Walkthrough / PR Disclosure of AI Usage `[DRAFT]`:** The Walkthrough artifact ([walkthrough.md](../../templates/walkthrough.md)) or Pull Request description ([pull_request_template.md](../../templates/pull_request_template.md)) clearly states what changed and where AI assistance was used.

---

## 2. Release Level Checklist `[DRAFT]`

Every production release candidate must satisfy all of the following before deployment sign-off:

- [ ] **Regression Suite Green `[DRAFT]`:** The full automated regression and smoke test suite passes cleanly.
- [ ] **Performance SLA Verified with Report Attached `[DRAFT]`:** Performance testing has been executed against the agreed SLA (see [performance-sla.md](./performance-sla.md)), and the full report (percentiles, error rate, resource monitoring) is attached to the release record.
- [ ] **Migrations and Schema Changes Reviewed by a Human `[DRAFT]`:** All database schema changes, migration scripts, and data backfills have been explicitly reviewed and approved by a human (Tier 2 in [ai-boundary.md](./ai-boundary.md)).
- [ ] **Rollback Plan Documented `[DRAFT]`:** A tested or verified step-by-step rollback procedure (including database/state compatibility) is documented.
- [ ] **Monitoring and Alerts in Place `[DRAFT]`:** Application metrics, logs, dashboards, and operational alerts for new or modified flows are active.
- [ ] **Sign-Off by Named Owner `[DRAFT]`:** Explicit release approval is recorded by the designated release/product owner.

---

## 3. Open Items to Research and Finalize `[TO RESEARCH]`

- `TODO [TO RESEARCH]`: Define what constitutes "significant AI-generated code" requiring a formal plan artifact vs. small Tier 1 fixes.
- `TODO [TO RESEARCH]`: Define role-based sign-off owners (Tech Lead, QA Lead, Security Reviewer, Release Owner) for enterprise banking / government releases.
