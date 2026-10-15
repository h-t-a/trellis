# CLAUDE.md - `ai-dev-playbook` (Trellis)

## 1. Project Overview

This repository defines the team standard for AI-assisted software development in enterprise banking and government-style systems (`v0.1` `[DRAFT]`).
It supports both **Claude Code** and **Antigravity IDE** from a **single source of truth** in `docs/standards/` (see [ADR 0001](./docs/decisions/0001-single-source-of-truth.md)).

- **Core workflow:** `Plan -> Implement -> Verify -> Review`
- **Enforcement principle:** *A rule is a request; a hook is a guarantee.*
- **Local overrides:** Place personal, machine-local notes in `CLAUDE.local.md` (gitignored). Never put secrets in `CLAUDE.md`, rules, skills, or `.mcp.json`.

---

## 2. Canonical Standards (Source of Truth Imports)

All authoritative policies live in `docs/standards/`. Do not duplicate their prose into tool-specific files:

- **Testing Standard:** @docs/standards/testing-standard.md
- **Performance Testing & SLA Standard:** @docs/standards/performance-sla.md
- **Definition of Done (Story & Release):** @docs/standards/definition-of-done.md
- **AI Boundary (Tiers 1, 2, 3):** @docs/standards/ai-boundary.md
- **Security Baseline:** @docs/standards/security-baseline.md
- **Git & Commit Convention:** @docs/standards/git-convention.md

Supporting references:
- **ADR 0001 (Single Source of Truth):** @docs/decisions/0001-single-source-of-truth.md
- **Developer Onboarding & Feedback Loop:** @docs/onboarding.md

---

## 3. How the Standard Is Organized in Claude Code

1. **Modular Rules (`.claude/rules/*.md`):** Automatically discovered, concise pointers (< 60 lines each) covering [code-style.md](./.claude/rules/code-style.md), [testing.md](./.claude/rules/testing.md), [api-conventions.md](./.claude/rules/api-conventions.md), [security.md](./.claude/rules/security.md), and [git-convention.md](./.claude/rules/git-convention.md).
2. **Slash Commands (`.claude/commands/*.md`):** Explicit step sequences invoked as `/plan-feature`, `/review`, `/test-all`, and `/release-checklist`.
3. **Skills (`.claude/skills/*/SKILL.md`):** On-demand runbooks (< 80 lines each) for `test-writer`, `security-audit`, `code-review`, and `perf-test`.
4. **Subagents (`.claude/agents/*.md`):** Isolated specialist agents with minimum required tools: read-only `code-reviewer` and `security-auditor`, plus `test-writer`.
5. **Hooks (`.claude/hooks/*.sh`):** Simple, readable enforcement scripts (`validate-bash.sh`, `secret-scan.sh`, `run-tests.sh`). Hooks are **not** wired into `.claude/settings.json` until explicitly approved `[VERIFY]`.
6. **Review Gate Templates (`templates/*.md`):** Shared fill-in templates for [implementation-plan.md](./templates/implementation-plan.md), [walkthrough.md](./templates/walkthrough.md), [test-plan.md](./templates/test-plan.md), and [pull_request_template.md](./templates/pull_request_template.md).

---

## 4. Non-Negotiable Operating Rules

- **Plan Before Code:** For any Tier 2 / non-trivial change, produce an Implementation Plan using `templates/implementation-plan.md` and wait for human approval before writing feature code.
- **Test Discipline:** Never delete, skip, or weaken an existing test to make a build pass (Tier 3 prohibition). Write or require a failing test before implementing new behavior or bug fixes.
- **Respect AI Boundaries:** Never touch production secrets, real customer data, production deployments, or financial/ledger sign-off (Tier 3 in `@docs/standards/ai-boundary.md`).
- **Keep Context Lean:** Keep `CLAUDE.md` under 200 lines. Link to `docs/standards/` rather than copying policies.
