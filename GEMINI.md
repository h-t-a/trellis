# GEMINI.md - Antigravity Project Context `[VERIFY file name per Antigravity version]`

> **Verification Note `[VERIFY]`:** Confirm whether your installed Antigravity IDE version loads root `GEMINI.md`, `AGENTS.md`, or `.agents/rules/standards.md` as the primary workspace context file.

## 1. Single Source of Truth

This repository follows the **`ai-dev-playbook` (Trellis) v0.1** standard (`[DRAFT]`). All authoritative engineering policies live in `docs/standards/` (see [ADR 0001](./docs/decisions/0001-single-source-of-truth.md)):

- [Testing Standard](./docs/standards/testing-standard.md)
- [Performance Testing & SLA Standard](./docs/standards/performance-sla.md)
- [Complexity & Performance Analysis Standard](./docs/standards/complexity-and-performance.md)
- [Root Cause Analysis (RCA) Playbook](./docs/standards/rca-playbook.md)
- [Quota & Token Efficiency Standard](./docs/standards/quota-efficiency.md)
- [Definition of Done](./docs/standards/definition-of-done.md)
- [AI Boundary Standard (Tiers 1–3)](./docs/standards/ai-boundary.md)
- [Security Baseline](./docs/standards/security-baseline.md)
- [Git & Commit Convention](./docs/standards/git-convention.md)
- [Developer Onboarding Guide](./docs/onboarding.md)

## 2. Antigravity Workflow, Skills & MCP Tools

1. **Plan & Spec First:** Before writing Class M or Class L / Tier 2 code, create a Spec ([templates/spec-template.md](./templates/spec-template.md)) or **Implementation Plan artifact** ([templates/implementation-plan.md](./templates/implementation-plan.md)) and wait for human approval.
2. **Test Discipline:** Follow [testing-standard.md](./docs/standards/testing-standard.md). Never delete, skip, or weaken existing tests to make a build pass.
3. **Security & AI Boundaries:** Never include secrets, raw PANs, or real customer/production data in prompts, rules, skills, or MCP configs (see [ai-boundary.md](./docs/standards/ai-boundary.md), [security-baseline.md](./docs/standards/security-baseline.md), and [rca-playbook.md](./docs/standards/rca-playbook.md)).
4. **Git & Commit Discipline:** Follow [git-convention.md](./docs/standards/git-convention.md) (`<type>(<scope>): <imperative summary>`, max 72 chars, lowercase subject, no trailing period, semantic branches `<type>/<name>`).
5. **Walkthrough Gate:** After implementation, produce a **Walkthrough artifact** following [templates/walkthrough.md](./templates/walkthrough.md) stating what changed and where AI was used.
6. **Customizations & `trellis-mcp` Server:**
   - **Rules (`.agents/rules/*.md`):** `standards.md`, `git-convention.md`, and `quota-efficiency.md` (with `trigger: always_on` YAML frontmatter).
   - **Skills / Slash Commands (`.agents/skills/*/SKILL.md`):** `/pb-rca`, `/pb-spec`, `/pb-enhance`, `/pb-handoff`, `/pb-review`, `/pb-plan`, `/pb-release-check`, `test-writer`, `security-audit`, `code-review`, and `perf-test`.
   - **MCP Server (`trellis-mcp`):** Exposes `trellis_get_standard`, `trellis_rca`, `trellis_spec`, `trellis_enhance`, `trellis_budget`, `trellis_handoff`, `trellis_review`, and `trellis_doctor` across any workspace (`python3 -m trellis_mcp --install-global`).
