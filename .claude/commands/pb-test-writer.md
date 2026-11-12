---
name: pb-test-writer
description: Write failing [REQ-NNN-XX] tests first, execute full test verification suites, and enforce zero weakened assertions. Invoke as /pb-test-writer.
---

# Skill: `/pb-test-writer` — Requirement-Linked Test Authoring & Verification

**Canonical Standards:**
- [docs/standards/testing-standard.md](../../docs/standards/testing-standard.md)
- [docs/standards/ai-boundary.md](../../docs/standards/ai-boundary.md)

## Mandatory Rules

1. **Requirement Traceability:** State the exact `[REQ-NNN-XX]` requirement or defect scenario verified by each test.
2. **Failing Test First (Red -> Green):** Ensure new behavior and bug-fix tests fail before the production change and pass after (scaffold via `trellis_test` when helpful).
3. **Meaningful Assertions:** Assert specific outputs, state transitions, and error handling. Highlight all AI-written tests for **human review** in the Walkthrough artifact.
4. **Never Delete, Skip, or Weaken Tests (Tier 3 Prohibition):** Never remove, mute, or weaken an existing test to make a build pass.
5. **Synthetic Data Only (Tier 3 Prohibition):** Never use real customer or production data in test fixtures.

## Execution Steps

1. Consult [docs/standards/testing-standard.md](../../docs/standards/testing-standard.md) for the target test level (`unit`, `integration`, `contract`).
2. Write the failing `[REQ-NNN-XX]` test (or run `trellis_test`), then run the targeted suite to confirm Red -> Green after implementation.
3. Execute the full project test suite and confirm zero skipped or weakened tests.
4. Document all new tests in [templates/walkthrough.md](../../templates/walkthrough.md) for human assertion review.
