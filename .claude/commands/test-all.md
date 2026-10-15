# Command: `/test-all`

Execute the project test suite and verify compliance with the Testing Standard.

**Canonical Standards:**
- [Testing Standard](../../docs/standards/testing-standard.md) (`[DRAFT]`)
- [AI Boundary Standard](../../docs/standards/ai-boundary.md) (`[DRAFT]`)

## Execution Steps

1. **Enforce Test Integrity Before Running:**
   - Verify via `git diff` that no existing tests have been deleted, skipped (`.skip`, `@Ignore`, `@Disabled`), or weakened (Tier 3 prohibition in [ai-boundary.md](../../docs/standards/ai-boundary.md)).
2. **Run Configured Test Levels:**
   - Execute the project's unit, integration, contract, and lint/static-analysis commands (`TODO [TO RESEARCH]: configure project-specific test runner command in .claude/hooks/run-tests.sh`).
3. **Evaluate Failures Honesty:**
   - If any test fails, diagnose the root cause in the implementation code or fixture setup.
   - **Never** modify an assertion or mute a test solely to make the suite pass.
4. **Verify AI-Written Test Rules ([testing-standard.md](../../docs/standards/testing-standard.md)):**
   - Confirm every new test states the requirement it verifies and tests a real behavior that fails when the production change is reverted.
5. **Report Summary:**
   - Output executed test levels, pass/fail counts, any remaining `TODO [TO RESEARCH]` test gates, and items requiring human review of assertions.
