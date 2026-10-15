# ADR 0001: Single Source of Truth for AI-Assisted Development Standards

- **Status:** Accepted (v0.1) `[DRAFT]`
- **Date:** 2026-10-15
- **Source:** [trellis-project-export.md](../knowledge/trellis-project-export.md) (Sections 2.2, 2.3, 8, 10)

---

## Context

Developers across our teams use two AI-assisted development environments in daily work:
1. **Antigravity IDE** (which uses workspace rules such as `GEMINI.md` / `.agents/rules/`, skills in `.agents/skills/`, workflows in `.agents/workflows/`, and artifacts).
2. **Claude Code** (which uses `CLAUDE.md`, modular rules in `.claude/rules/*.md`, slash commands in `.claude/commands/*.md`, skills in `.claude/skills/`, subagents in `.claude/agents/*.md`, and hooks in `.claude/hooks/`).

If we write our engineering standards directly inside `CLAUDE.md` and duplicate them into `GEMINI.md` or `.agents/`, several problems arise:
- **Standard Drift:** Updating a testing or security rule in one tool's folder quickly falls out of sync with the other tool.
- **Context Bloat:** Claude Code documentation recommends keeping `CLAUDE.md` under roughly **200 lines** for reliability `[VERIFIED]`, and Antigravity caps individual rule files as well. Copying full policies into root context files degrades model adherence.
- **Anti-Pattern Duplication:** Copying documentation instead of linking is an explicit project-structure anti-pattern identified in our knowledge export.

---

## Decision

1. **Single Source of Truth in `docs/standards/`:**
   All canonical engineering standards—[testing-standard.md](../standards/testing-standard.md), [performance-sla.md](../standards/performance-sla.md), [definition-of-done.md](../standards/definition-of-done.md), [ai-boundary.md](../standards/ai-boundary.md), [security-baseline.md](../standards/security-baseline.md), and [git-convention.md](../standards/git-convention.md)—are authored and maintained once in plain, tool-agnostic Markdown inside `docs/standards/`.
2. **Thin Tool-Specific Pointers:**
   - `CLAUDE.md` stays under 200 lines and imports the canonical standards using `@docs/standards/...` references.
   - `GEMINI.md` (`[VERIFY]` filename per Antigravity version) and `.agents/rules/standards.md` stay concise and link directly to `docs/standards/*.md`.
   - Rules, commands, workflows, skills, and subagent prompts in `.claude/` and `.agents/` summarize only the immediate action checklist and point to `docs/standards/` for authoritative policies.
3. **Shared Review Gates via `templates/`:**
   Both tools enforce the same human review gates (Implementation Plan before code, Walkthrough/PR description after implementation, Test Plan for SLAs) using shared Markdown templates in `templates/`.

---

## Consequences

- **Positive:**
  - Every change to a team standard happens in one place (`docs/standards/`) and goes through a single Pull Request review with `CODEOWNERS`.
  - Both Claude Code and Antigravity IDE developers follow identical quality bars, AI boundaries, and security baselines.
  - Root context files (`CLAUDE.md`, `GEMINI.md`) remain short, fast to load, and reliable.
- **Trade-offs / Next Steps:**
  - Tool-specific wrapper files in `.claude/` and `.agents/` still require occasional structural updates when a new skill or workflow is added. To reduce manual maintenance further, [sync-tool-configs.md](../../scripts/sync-tool-configs.md) outlines a future sync/validation script.
