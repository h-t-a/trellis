# CLAUDE.md - `ai-dev-playbook` (Trellis)

## 1. Project Overview

This repository defines the team standard for **Software Engineers** building enterprise banking and government-style systems using **AI agents, foundation models, RAG, subagents, and MCP integrations** (`v0.1` `[DRAFT]`).
It supports both **Claude Code** and **Antigravity IDE** from a **single source of truth** in `docs/standards/` (see [ADR 0001](./docs/decisions/0001-single-source-of-truth.md)).

- **Core workflow:** `Plan -> Implement -> Verify -> Review`
- **Enforcement principle:** *A rule is a request; a hook is a guarantee.*
- **Local overrides:** Place personal, machine-local notes in `CLAUDE.local.md` (gitignored). Never put secrets in `CLAUDE.md`, rules, skills, or `.mcp.json`.

---

## 2. Canonical Standards (Source of Truth Imports)

All authoritative policies live in `docs/standards/`. Do not duplicate their prose into tool-specific files:

- **Testing Standard:** @docs/standards/testing-standard.md
- **Performance Testing & SLA Standard:** @docs/standards/performance-sla.md
- **Complexity & Performance Analysis Standard:** @docs/standards/complexity-and-performance.md
- **Root Cause Analysis (RCA) Playbook:** @docs/standards/rca-playbook.md
- **Quota & Token Efficiency Standard:** @docs/standards/quota-efficiency.md
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
2. **Slash Commands & Unified Skills (`.claude/skills/*/SKILL.md` & `.claude/commands/*.md`):** On-demand runbooks (< 80 lines each) synced from `.agents/skills/` via `python3 -m trellis_mcp --sync-workspace`: `/pb-rca`, `/pb-spec`, `/pb-enhance`, `/pb-handoff`, `/pb-review`, `/pb-plan`, `/pb-release-check`, `test-writer`, `security-audit`, `code-review`, and `perf-test`.
3. **MCP Server (`trellis-mcp` in `.mcp.json`):** Zero-dependency Python MCP server providing `trellis_get_standard`, `trellis_rca`, `trellis_spec`, `trellis_enhance`, `trellis_budget`, `trellis_handoff`, `trellis_review`, `trellis_doctor`, `trellis_test`, `trellis_scan`, `trellis_classify`, `trellis_mcp_registry`, `trellis_verify`, and `trellis_analytics`.
4. **Subagents (`.claude/agents/*.md`):** Isolated specialist agents with minimum required tools: read-only `code-reviewer` and `security-auditor`, plus `test-writer`.
5. **Hooks (`.claude/hooks/*.sh`):** Simple, readable enforcement scripts (`validate-bash.sh`, `secret-scan.sh`, `run-tests.sh`). Hooks are **not** wired into `.claude/settings.json` until explicitly approved `[VERIFY]`.
6. **Review Gate Templates (`templates/*.md`):** Shared fill-in templates for [spec-template.md](./templates/spec-template.md), [implementation-plan.md](./templates/implementation-plan.md), [walkthrough.md](./templates/walkthrough.md), [test-plan.md](./templates/test-plan.md), and [pull_request_template.md](./templates/pull_request_template.md).

---

## 4. Non-Negotiable Operating Rules

- **Plan Before Code:** For any Tier 2 / non-trivial change, produce an Implementation Plan using `templates/implementation-plan.md` and wait for human approval before writing feature code.
- **Test Discipline:** Never delete, skip, or weaken an existing test to make a build pass (Tier 3 prohibition). Write or require a failing test before implementing new behavior or bug fixes.
- **Respect AI Boundaries:** Never touch production secrets, real customer data, production deployments, or financial/ledger sign-off (Tier 3 in `@docs/standards/ai-boundary.md`).
- **Keep Context Lean:** Keep `CLAUDE.md` under 200 lines. Link to `docs/standards/` rather than copying policies.
