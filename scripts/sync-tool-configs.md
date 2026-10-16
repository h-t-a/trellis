# Tool Configuration Sync & Global Installer (`trellis-mcp`)

**Status:** Implemented in `trellis_mcp/` (`v0.1`)  
**Related Decision:** [ADR 0001: Single Source of Truth](../docs/decisions/0001-single-source-of-truth.md)  
**Source:** [trellis-project-export.md](../docs/knowledge/trellis-project-export.md) (Sections 8, 10) & [evaluation-addendum-01.md](../docs/knowledge/evaluation-addendum-01.md) (`F01`, `F02`, `F09`)

---

## 1. Purpose

To support both **Claude Code** (`.claude/`, `CLAUDE.md`) and **Antigravity IDE** (`.agents/`, `GEMINI.md`, `~/.gemini/config/plugins/trellis/`) without maintaining two diverging sets of skill files by hand, `docs/standards/` and `.agents/skills/` serve as the canonical source of truth, synchronized and validated via `python3 -m trellis_mcp`.

---

## 2. CLI Commands (`python3 -m trellis_mcp`)

1. **Sync Workspace (`--sync-workspace`):**
   ```bash
   python3 -m trellis_mcp --sync-workspace
   ```
   - Copies canonical `.agents/skills/*/SKILL.md` into `.claude/skills/*/SKILL.md` (and mirrors `/pb-*` skills into `.claude/commands/*.md`).
   - Updates `.mcp.json` and `.agents/mcp_config.json` with the `trellis-mcp` stdio server entry.
   - Removes deprecated `.agents/workflows/*.md` files (`F01`).

2. **Install Globally on Any User's Device (`--install-global`):**
   ```bash
   python3 -m trellis_mcp --install-global
   ```
   - Installs the `trellis` plugin into `~/.gemini/config/plugins/trellis/` (`plugin.json`, `rules/AGENTS.md`, `skills/*/SKILL.md`, `.mcp.json`).
   - Registers `trellis-mcp` in `~/.gemini/config/mcp_config.json`.
   - Installs all `/pb-*` and engineering skills into `~/.claude/skills/`.

3. **Workspace Doctor & CI Check (`--check` / `--doctor` / `--fix`):**
   ```bash
   python3 -m trellis_mcp --check
   python3 -m trellis_mcp --check --fix
   ```
   - Verifies that every `.agents/rules/*.md` file has valid YAML frontmatter (`trigger:` and `description:`) (`F02`).
   - Verifies line-count budgets (`CLAUDE.md` < 200 lines; `SKILL.md` files < 80 lines).
   - Flags any lingering deprecated `.agents/workflows/*.md` files.
