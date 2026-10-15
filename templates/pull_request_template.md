## Summary of Changes

- **Ticket / Story:** `[TICKET-ID]`
- **Implementation Plan:** `[Link to approved Implementation Plan artifact or doc]`
- **Walkthrough:** `[Link to Walkthrough artifact or summary below]`
- **What Changed & Why:**
  - `[Bullet 1]`
  - `[Bullet 2]`

---

## AI Usage & Boundary Disclosure (`[DRAFT]`)

- **AI Tools Used:** `[None | Claude Code | Antigravity IDE]`
- **AI Boundary Tier ([docs/standards/ai-boundary.md](../docs/standards/ai-boundary.md)):**
  - [ ] `Tier 1` (Boilerplate, docs, lint/format, unit-test drafts, test-covered refactors)
  - [ ] `Tier 2` (Feature code, API changes, DB migrations, CI/CD, auth/input validation - **explicit human review completed**)
  - [ ] Confirmed **zero `Tier 3` actions** (no production secrets, no real customer/production data, no test weakening, no automated production deployment or financial/ledger sign-off by AI)
- **Where AI Was Used:**
  - `[Briefly state which files, tests, or plans were drafted with AI assistance]`

---

## Story-Level Definition of Done Checklist (`[DRAFT]`)

Per [docs/standards/definition-of-done.md](../docs/standards/definition-of-done.md), confirm all items before merging:

- [ ] **Plan Reviewed Before Code:** Implementation plan was reviewed and approved by a human prior to significant AI-generated code.
- [ ] **Human Code Review:** All changes have been critically reviewed by a human.
- [ ] **Tests Written & Passing in CI ([docs/standards/testing-standard.md](../docs/standards/testing-standard.md)):**
  - [ ] New behavior / bug fixes have a test that failed before the change and passes after.
  - [ ] Every AI-written test was reviewed by a human for meaningful assertions and cites the requirement it verifies.
  - [ ] No existing tests were deleted, skipped, or weakened.
- [ ] **Lint, Format & Static Analysis Clean**
- [ ] **Secret Scan & Dependency Scan Clean ([docs/standards/security-baseline.md](../docs/standards/security-baseline.md))**
- [ ] **Docs or ADR Updated:** Updated documentation or `docs/decisions/` ADR if behavior, APIs, or architecture changed.
- [ ] **Walkthrough / AI Disclosure Complete**

---

## Release-Level Checklist (If Applicable - `[DRAFT]`)

- [ ] Regression suite green
- [ ] Performance test run against agreed SLA with percentile/error-rate/monitoring report attached ([docs/standards/performance-sla.md](../docs/standards/performance-sla.md))
- [ ] Database migrations and schema changes reviewed by a human
- [ ] Rollback plan documented
- [ ] Monitoring and alerts in place
- [ ] Sign-off by named owner: `[Owner Name]`
