# Testing Standard

**Status:** Working draft v0.1 `[DRAFT]`  
**Source:** Canonical Trellis engineering standard (`docs/standards/`)  
**Domain Context:** Enterprise banking / government-style systems where testing discipline and auditability are first-class concerns.

---

## 1. Test Levels `[TO RESEARCH]`

For each test level below, the standard must define: **what it verifies**, **who writes it**, **where it runs**, and **what blocks a merge**.

| Test Level | What It Verifies | Who Writes It | Where It Runs | Merge-Blocking Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Unit** | `TODO [TO RESEARCH]` | `TODO [TO RESEARCH]` | `TODO [TO RESEARCH]` | `TODO [TO RESEARCH]` |
| **Integration** | `TODO [TO RESEARCH]` | `TODO [TO RESEARCH]` | `TODO [TO RESEARCH]` | `TODO [TO RESEARCH]` |
| **Contract (API)** | `TODO [TO RESEARCH]` | `TODO [TO RESEARCH]` | `TODO [TO RESEARCH]` | `TODO [TO RESEARCH]` |
| **End-to-End (E2E)** | `TODO [TO RESEARCH]` | `TODO [TO RESEARCH]` | `TODO [TO RESEARCH]` | `TODO [TO RESEARCH]` |
| **Performance** | Throughput, latency percentiles, and error rate against SLA (see [performance-sla.md](./performance-sla.md)) | `TODO [TO RESEARCH]` | Production-like test environment (`TODO [TO RESEARCH]`) | Required at Release level `[DRAFT]`; per-PR gate `TODO [TO RESEARCH]` |
| **Security (SAST, Dependency Scan, DAST)** | Static code vulnerabilities, vulnerable dependencies, dynamic runtime issues | `TODO [TO RESEARCH]` | CI pipeline / pre-commit (see [security-baseline.md](./security-baseline.md)) | Secret scan and dependency scan clean at Story level `[DRAFT]`; DAST/SAST details `TODO [TO RESEARCH]` |
| **Regression / Smoke** | Critical user journeys and release stability | `TODO [TO RESEARCH]` | CI / pre-release environment (`TODO [TO RESEARCH]`) | Regression suite green at Release level `[DRAFT]` |

---

## 2. Testing Policy `[TO RESEARCH]`

The following cross-cutting policies are open research topics to be finalized with the engineering team:

- **Test Data Management (`TODO [TO RESEARCH]`):** Define how realistic synthetic test data is generated, seeded, and isolated without ever using real customer or production data (which is strictly prohibited under Tier 3 of [ai-boundary.md](./ai-boundary.md)).
- **Environment Strategy (`TODO [TO RESEARCH]`):** Define local, CI, staging, and production-like performance test environments.
- **Coverage Policy (`TODO [TO RESEARCH]`):** Define a **risk-based coverage policy** rather than relying on a single arbitrary percentage across all modules.
- **Flaky-Test Policy (`TODO [TO RESEARCH]`):** Define detection, quarantine, SLA for fixing, and escalation rules for non-deterministic tests.

---

## 3. Rules for AI-Written Tests `[DRAFT, to research]`

When AI tools (Claude Code or Antigravity IDE) generate or modify tests, the following rules apply:

1. **Human Review for Meaningful Assertions `[DRAFT]`:** A human must review every AI-written test to confirm it makes meaningful assertions about behavior-not superficial tests that execute lines of code and pass without checking anything.
2. **Never Delete, Skip, or Weaken Tests `[DRAFT]`:** AI must **never** delete, skip (e.g., `.skip`, `@Disabled`, `@Ignore`), or weaken an existing test or assertion just to make a build pass. Removing or weakening tests to get a green build is a **Tier 3 (human-only / prohibited)** action in [ai-boundary.md](./ai-boundary.md).
3. **Failing Test First (Red -> Green) `[DRAFT]`:** New behavior and bug fixes must come with a test that **fails before the code change** and **passes after the change**.
4. **Traceability to Requirements `[DRAFT]`:** Every test must clearly state the requirement, acceptance criterion, or bug scenario it verifies (in the test name, docstring, or comment).
5. **Mutation Testing (`TODO [TO RESEARCH]`) `[DRAFT]`:** Evaluate mutation testing tools to verify the effectiveness of AI-written and human-written test suites.

---

## 4. CI Gates `[DRAFT / TO RESEARCH]`

Baseline gates from the [definition-of-done.md](./definition-of-done.md) `[DRAFT]`:

- **Story / Change Gate `[DRAFT]`:**
  - Tests at the appropriate levels are written and passing in CI.
  - Lint, formatting, and static analysis checks are clean.
  - Secret scan and dependency scan are clean.
- **Release Gate `[DRAFT]`:**
  - Full regression suite is green.
  - Performance test has been executed against the agreed SLA with the report attached (see [performance-sla.md](./performance-sla.md)).
- **Detailed Per-Stage Pipeline Enforcement (`TODO [TO RESEARCH]`):**
  - `TODO [TO RESEARCH]`: Define exact CI stage timeouts, required status checks per branch, and automatic hook enforcement (`run-tests.sh`).
