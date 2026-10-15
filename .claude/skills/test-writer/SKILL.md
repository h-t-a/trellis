---
name: test-writer
description: >-
  Write and review requirement-linked automated tests following the project
  Testing Standard. Use when adding new behavior, fixing bugs, or expanding test coverage.
---

# Skill: Test Writer

**Canonical Source of Truth:** [docs/standards/testing-standard.md](../../../docs/standards/testing-standard.md)  
**Related Standard:** [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)

## When to Use

Activate this skill whenever drafting unit, integration, contract, E2E, or regression tests, or when writing a reproducing test for a bug fix.

## Mandatory Rules (`[DRAFT]`)

1. **State the Requirement:**
   - Every test must explicitly name or comment the requirement, acceptance criterion, or bug scenario it verifies.
2. **Failing Test First (Red -> Green):**
   - For new behavior or bug fixes, write the test so that it **fails before the implementation change** and **passes after the change**.
3. **Write Meaningful Assertions:**
   - Assert specific outputs, state transitions, and error conditions.
   - Never write tautological or assertion-free tests that merely execute lines for coverage.
   - Flag every AI-written test for **human review of assertions** before merge.
4. **Never Delete, Skip, or Weaken Existing Tests (Tier 3 Prohibition):**
   - Do not delete tests, add `.skip` / `@Ignore` / `@Disabled`, or loosen assertions to make a failing build pass.
5. **Synthetic Test Data Only (Tier 3 Prohibition):**
   - Use synthetic fixtures only. Never include real customer PII, production account numbers, or real credentials in test files.

## Execution Workflow

1. Read [docs/standards/testing-standard.md](../../../docs/standards/testing-standard.md) to check the target test level (`TODO [TO RESEARCH]: verify project-specific level gates`).
2. Identify the exact requirement or defect being tested.
3. Draft the test with clear Arrange / Act / Assert sections and requirement documentation.
4. Run the test to confirm the expected Red -> Green transition.
5. In the Walkthrough or PR description, highlight all AI-written tests so the human reviewer can inspect their assertions.
