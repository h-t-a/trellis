# Tool Configuration Sync, Global Installer & VM HTTP Server (`trellis-mcp`)

**Status:** Implemented in `trellis_mcp/` (`v0.1.0`)  
**Related Decision:** [ADR 0001: Single Source of Truth](../docs/decisions/0001-single-source-of-truth.md)  
**Source:** [trellis-project-export.md](../docs/knowledge/trellis-project-export.md) (Sections 8, 10) & [evaluation-addendum-01.md](../docs/knowledge/evaluation-addendum-01.md) (`F01`, `F02`, `F09`, `[REQ-MCP-01..08]`)

---

## 1. Purpose

To support both **Claude Code** (`.claude/`, `CLAUDE.md`) and **Antigravity IDE** (`.agents/`, `GEMINI.md`, `~/.gemini/config/plugins/trellis/`) without maintaining two diverging sets of skill files by hand, `docs/standards/` and `.agents/skills/` serve as the canonical source of truth, synchronized, served, and validated via `python -m trellis_mcp`.

---

## 2. CLI Commands (`python -m trellis_mcp`)

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

3. **Host Private VM HTTP Server & Auto-Generate Admin Key (`--serve-http` & `--auto-generate-key`):**
   ```bash
   python3 -m trellis_mcp --serve-http --auto-generate-key --host 0.0.0.0 --port 8080
   ```
   - Hosts `GET /healthz`, `POST /mcp`, `GET /bundle.json`, `GET /install.sh`, and `/admin/keys` (`GET`, `POST`, `DELETE`).
   - Automatically generates and persists an administrator API key (`trl_admin_<random>`) in `.trellis_keys.json` (`0600`) when `TRELLIS_API_KEY` is not set (`[REQ-MCP-08-01]`).

4. **Administrator API Key Management for Users & Teams (`--generate-key`, `--list-keys`, `--revoke-key`):**
   ```bash
   # Issue a new member or admin key for another user or team
   python3 -m trellis_mcp --generate-key team-ibanking --role member

   # List all keys (masked prefix, label, role, created_at, revoked)
   python3 -m trellis_mcp --list-keys

   # Revoke a key immediately by key_id or label
   python3 -m trellis_mcp --revoke-key team-ibanking
   ```

5. **Zero-Clone Remote Client Setup (`--install-remote`):**
   ```bash
   python3 -m trellis_mcp --install-remote http://<vm-ip>:8080 --api-key "<team-member-api-key>"
   ```
   - Fetches `/bundle.json` from the remote VM, installs `/pb-*` skills and rules locally, and configures `~/.gemini/config/mcp_config.json` to point to `http://<vm-ip>:8080/mcp`.

6. **Workspace Doctor & CI Check (`--check` / `--doctor` / `--fix`):**
   ```bash
   python3 -m trellis_mcp --check
   python3 -m trellis_mcp --check --fix
   ```
   - Verifies that every `.agents/rules/*.md` file has valid YAML frontmatter (`trigger:` and `description:`) (`F02`).
   - Verifies line-count budgets (`CLAUDE.md` < 200 lines; `SKILL.md` files < 80 lines).
   - Flags any lingering deprecated `.agents/workflows/*.md` files.
