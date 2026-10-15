# GEMINI.md - Antigravity Project Context `[VERIFY file name per Antigravity version]`

> **Verification Note `[VERIFY]`:** Confirm whether your installed Antigravity IDE version loads root `GEMINI.md`, `AGENTS.md`, or `.agents/rules/standards.md` as the primary workspace context file.

## 1. Single Source of Truth

This repository follows the **`ai-dev-playbook` (Trellis) v0.1** standard (`[DRAFT]`). All authoritative engineering policies live in `docs/standards/` (see [ADR 0001](./docs/decisions/0001-single-source-of-truth.md)):

- [Testing Standard](./docs/standards/testing-standard.md)
- [Performance Testing & SLA Standard](./docs/standards/performance-sla.md)
- [Definition of Done](./docs/standards/definition-of-done.md)
- [AI Boundary Standard (Tiers 1–3)](./docs/standards/ai-boundary.md)
- [Security Baseline](./docs/standards/security-baseline.md)
- [Git & Commit Convention](./docs/standards/git-convention.md)
- [Developer Onboarding Guide](./docs/onboarding.md)

## 2. Antigravity Workflow & Review Gates

1. **Plan First:** Before writing significant feature or Tier 2 code, create an **Implementation Plan artifact** following [templates/implementation-plan.md](./templates/implementation-plan.md) and wait for human approval.
2. **Test Discipline:** Follow [testing-standard.md](./docs/standards/testing-standard.md). Never delete, skip, or weaken existing tests to make a build pass.
3. **Security & AI Boundaries:** Never include secrets or real customer/production data in prompts, rules, skills, or MCP configs (see [ai-boundary.md](./docs/standards/ai-boundary.md) and [security-baseline.md](./docs/standards/security-baseline.md)).
4. **Git & Commit Discipline:** Follow [git-convention.md](./docs/standards/git-convention.md) (`<type>(<scope>): <imperative summary>`, max 72 chars, lowercase subject, no trailing period, semantic branches `<type>/<name>`).
5. **Walkthrough Gate:** After implementation, produce a **Walkthrough artifact** following [templates/walkthrough.md](./templates/walkthrough.md) stating what changed and where AI was used.
6. **Customizations (`[VERIFY .agent vs .agents]`):** Use `.agents/rules/standards.md`, `.agents/rules/git-convention.md`, `.agents/workflows/` (`/plan-feature`, `/review`, `/release-checklist`), and `.agents/skills/` (`test-writer`, `security-audit`, `code-review`, `perf-test`).
