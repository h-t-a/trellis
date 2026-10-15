# Design Note: Tool Configuration Sync (`sync-tool-configs`)

**Status:** Design concept only - **not implemented yet** (`v0.1` `[DRAFT]`)  
**Related Decision:** [ADR 0001: Single Source of Truth](../docs/decisions/0001-single-source-of-truth.md)  
**Source:** [trellis-project-export.md](../docs/knowledge/trellis-project-export.md) (Sections 8, 10)

---

## 1. Purpose

To support both **Claude Code** (`.claude/`, `CLAUDE.md`) and **Antigravity IDE** (`.agents/`, `GEMINI.md`) without maintaining two diverging sets of files by hand, `docs/standards/` serves as the single source of truth.

This document describes how a future synchronization and validation utility in `scripts/` will keep the thin tool-specific pointers aligned whenever `docs/standards/` evolves.

---

## 2. What the Future Script Will Do (Design Only)

When implemented in a future iteration, the sync utility will perform three non-destructive tasks:

1. **Validate Reference Integrity (Read-Only Check for CI):**
   - Parse `CLAUDE.md`, `GEMINI.md`, `.claude/rules/*.md`, `.claude/commands/*.md`, `.claude/skills/*/SKILL.md`, `.claude/agents/*.md`, and `.agents/**`.
   - Verify that every `@docs/standards/...` import and relative Markdown link resolves to an existing file and heading in `docs/standards/` or `templates/`.
   - Verify line-count budgets (`CLAUDE.md` < 200 lines; `.claude/rules/*.md` < 60 lines; `SKILL.md` files < 80 lines).
2. **Sync Shared Skills & Workflows Across `.claude/` and `.agents/`:**
   - Because Skills (`skills/<name>/SKILL.md`) follow the same open-standard frontmatter (`name`, `description`) and Markdown body across both Claude Code and Antigravity IDE, the script can generate or synchronize `.agents/skills/<name>/SKILL.md` and `.claude/skills/<name>/SKILL.md` from a single canonical skill definition.
   - Similarly, keep `.claude/commands/*.md` and `.agents/workflows/*.md` aligned on step sequences and template references.
3. **Guard Against Unapproved Drift or Secrets:**
   - Fail CI if a tool-specific file copies large blocks of prose from `docs/standards/` instead of linking to it, or if any secret-like token pattern appears in any rule, skill, or config file.

---

## 3. Prerequisites Before Implementation (`[VERIFY]` / `[TO RESEARCH]`)

Before writing executable code for this script, confirm:
- [ ] `[VERIFY]`: Exact Antigravity workspace folder convention (`.agents/` vs `.agent/`) and context filename (`GEMINI.md` vs `AGENTS.md`) across all developer machines.
- [ ] `[VERIFY]`: Whether Antigravity IDE workflows in `.agents/workflows/` will be retained alongside `.agents/skills/` slash-command invocation.
- [ ] `TODO [TO RESEARCH]`: Choose the scripting runtime (e.g., POSIX shell / Python 3 standard library with zero external dependencies) so it runs in CI without extra package installations.
