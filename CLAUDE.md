# CLAUDE.md - `ai-dev-playbook` (Trellis)

## 1. Project Overview

This repository defines the team standard for **Software Engineers** building enterprise systems using **AI agents, multi-AI orchestration, vMF RAG pipelines, subagents, and MCP integrations** (`v0.1` + `SPEC-001`).
It supports **Claude Code**, **Antigravity IDE**, and major editors from a **single source of truth** in `docs/standards/` (see [ADR 0001](./docs/decisions/0001-single-source-of-truth.md)).

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
- **Data Classification:** @docs/standards/data-classification.md

Supporting references:
- **Approved Model AI-BOM:** @docs/standards/ai-bom.json
- **SPEC-001 (Security & Multi-AI Upgrade):** @docs/specs/001-secure-multi-ai-trellis.md
- **ADR 0001 (Single Source of Truth):** @docs/decisions/0001-single-source-of-truth.md
- **Developer Onboarding & Feedback Loop:** @docs/onboarding.md

---

## 3. How the Standard Is Organized in Claude Code

1. **Modular Rules (`.claude/rules/*.md`):** Automatically discovered, concise pointers (< 60 lines each) covering [code-style.md](./.claude/rules/code-style.md), [testing.md](./.claude/rules/testing.md), [api-conventions.md](./.claude/rules/api-conventions.md), [security.md](./.claude/rules/security.md), and [git-convention.md](./.claude/rules/git-convention.md).
2. **Slash Commands & Unified Skills (`.claude/skills/*/SKILL.md` & `.claude/commands/*.md`):** 18 runbooks synced from `.agents/skills/` via `python -m trellis_mcp --sync-workspace`: `/pb-plan`, `/pb-spec`, `/pb-pipeline`, `/pb-rca`, `/pb-enhance`, `/pb-handoff`, `/pb-review`, `/pb-release-check`, `/pb-route`, `/pb-synthesize`, `/pb-knowledge`, `/git-convention`, `/data-classification`, `/mcp-registry-audit`, `/test-writer`, `/security-audit`, `/code-review`, and `/perf-test`.
3. **MCP Server (`trellis-mcp` in `.mcp.json`):** Zero-dependency Python MCP server exposing 18 tools (`trellis_get_standard`, `trellis_rca`, `trellis_spec`, `trellis_enhance`, `trellis_budget`, `trellis_handoff`, `trellis_review`, `trellis_doctor`, `trellis_test`, `trellis_scan`, `trellis_classify`, `trellis_mcp_registry`, `trellis_verify`, `trellis_analytics`, `trellis_search_knowledge`, `trellis_route_model`, `trellis_pipeline`, `trellis_synthesize`) and A2A discovery (`/.well-known/agent.json`).
4. **Subagents (`.claude/agents/*.md`):** Isolated specialist agents with minimum required tools: read-only `code-reviewer` and `security-auditor`, plus `test-writer`.
5. **Security Permissions & Hooks (`.claude/settings.json` & `.claude/hooks/*.sh`):** Deny rules block `.env*`, `.trellis_keys.json`, `~/.ssh/*`, `~/.aws/*`, and exfiltration commands (`scp`, `nc`, `curl -d`, `wget --post`); `PreToolUse` (`validate-bash.sh`, `secret-scan.sh`) and `Stop` (`run-tests.sh`) hooks are wired in `.claude/settings.json`.
6. **Review Gate Templates (`templates/*.md`):** Shared fill-in templates for [spec-template.md](./templates/spec-template.md), [implementation-plan.md](./templates/implementation-plan.md), [walkthrough.md](./templates/walkthrough.md), [test-plan.md](./templates/test-plan.md), and [pull_request_template.md](./templates/pull_request_template.md).

---

## 4. Non-Negotiable Operating Rules

- **Plan & Approve Before Code:** For any Tier 2 / non-trivial change, produce an Implementation Plan using `templates/implementation-plan.md` and wait for human approval (`trellis_pipeline` Tier 2 gate) before writing feature code.
- **Test Discipline:** Never delete, skip, or weaken an existing test to make a build pass (Tier 3 prohibition). Write or require a failing test before implementing new behavior or bug fixes.
- **Respect AI Boundaries & Model Routing:** Never send `Confidential` or `Restricted` data/secrets/PANs to external cloud models (`trellis_route_model`, `trellis_classify`, `@docs/standards/ai-boundary.md`).
- **Keep Context Lean:** Keep `CLAUDE.md` under 200 lines. Link to `docs/standards/` rather than copying policies.
