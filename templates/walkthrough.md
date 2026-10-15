# Walkthrough: `[Feature / Change Title]`

- **Author / Developer:** `[Name]`
- **Date:** `[YYYY-MM-DD]`
- **Ticket / Requirement ID:** `[TICKET-ID]`
- **Approved Implementation Plan:** `[Link to Implementation Plan artifact or file]`

> [!NOTE]
> **Story-Level Definition of Done Gate (`[DRAFT]`):**
> Per [docs/standards/definition-of-done.md](../docs/standards/definition-of-done.md), every completed change must document what changed, how it was verified, and where AI assistance was used.

---

## 1. Summary of Changes

| File Path | Summary of Change | AI Role (`Drafted by AI` / `Human-Written` / `Co-Edited`) |
| :--- | :--- | :--- |
| `[path/to/file]` | `[Concise summary of implementation change]` | `[Drafted by AI / Human-reviewed]` |
| `[path/to/test_file]` | `[Requirement-linked test cases]` | `[Written by Human / Drafted by AI]` |

---

## 2. AI Usage Disclosure (`[DRAFT]`)

- **Tools & Skills Used:** `[e.g., Antigravity IDE / Claude Code, /plan-feature, test-writer skill]`
- **Where AI Was Used:** `[Describe which boilerplate, implementation drafts, or test drafts were generated with AI]`
- **Human Review & Corrections Made:** `[Describe assertions verified, edge cases corrected, or Tier 2 logic reviewed by human]`

---

## 3. Verification & Test Evidence ([docs/standards/testing-standard.md](../docs/standards/testing-standard.md))

- [ ] **Failing-First (Red -> Green) Verified:** New tests failed prior to the implementation change and pass now.
- [ ] **Human Assertion Review Completed:** Every AI-written test was checked by a human for meaningful assertions and requirement traceability.
- [ ] **Zero Weakened Tests:** No existing tests were deleted, skipped, or weakened.
- [ ] **Lint, Format & Static Analysis Clean:** `[Command run & output summary]`
- [ ] **Secret Scan & Dependency Scan Clean:** `[Command run & output summary]`

---

## 4. Documentation, Unresolved `[VERIFY]` Items & Feedback Loop

- **Docs / ADR Updated:** `[Link to updated doc or docs/decisions/ADR, or N/A]`
- **Unresolved `[VERIFY]` or `TODO` Items:**
  - `[List any remaining items or N/A]`
- **"Review Comment -> Rule" Candidate ([docs/onboarding.md](../docs/onboarding.md)):**
  - `[Did any review comment or AI mistake happen > 2 times? If so, note the proposed rule/skill update]`
