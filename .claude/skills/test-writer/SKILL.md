---
name: test-writer
description: >-
  Write and review requirement-linked automated tests following the project
  Testing Standard. Use when adding new behavior, fixing bugs, or expanding test coverage.
---

# Skill: Test Writer (Antigravity)

**Canonical Source of Truth:** [docs/standards/testing-standard.md](../../../docs/standards/testing-standard.md)  
**Related Standard:** [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)

## Mandatory Rules (`[DRAFT]`)

1. **Requirement Traceability:** State the exact requirement or defect scenario verified by each test.
2. **Failing Test First (Red -> Green):** Ensure new behavior and bug-fix tests fail before the production change and pass after.
3. **Meaningful Assertions:** Assert specific outputs, state transitions, and error handling. Highlight all AI-written tests for **human review** in the Walkthrough artifact.
4. **Never Delete, Skip, or Weaken Tests (Tier 3 Prohibition):** Never remove, mute, or weaken an existing test to make a build pass.
5. **Synthetic Data Only (Tier 3 Prohibition):** Never use real customer or production data in test fixtures.

## Steps

1. Consult [docs/standards/testing-standard.md](../../../docs/standards/testing-standard.md) for the target test level (`TODO [TO RESEARCH]: level-specific CI gates`).
2. Write the failing test referencing the requirement.
3. Run the test suite to verify the Red -> Green transition.
4. Document the new tests in the Walkthrough artifact ([templates/walkthrough.md](../../../templates/walkthrough.md)) for human assertion review.
