# Tool Configuration Sync, Multi-IDE Bridge & VM HTTP Server (`trellis-mcp`)

**Status:** Implemented in `trellis_mcp/` (`v0.1.0` + `SPEC-001`)  
**Related Decision:** [ADR 0001: Single Source of Truth](../docs/decisions/0001-single-source-of-truth.md)  
**Source:** [trellis-project-export.md](../docs/knowledge/trellis-project-export.md) (Sections 8, 10) & [001-secure-multi-ai-trellis.md](../docs/specs/001-secure-multi-ai-trellis.md)

---

## 1. Purpose

To support **Antigravity IDE** (`.agents/`, `GEMINI.md`, `~/.gemini/config/plugins/trellis/`), **Claude Code** (`.claude/`, `CLAUDE.md`), **VS Code**, **JetBrains**, **Cursor**, and **Windsurf** without maintaining diverging copies of skill files by hand, `docs/standards/` and `.agents/skills/pb-*/SKILL.md` serve as the single source of truth — synchronized, served over MCP `prompts/list`, and validated via `python -m trellis_mcp`.

---

## 2. CLI Commands (`python -m trellis_mcp`)

> **Windows Note:** Use `python -m trellis_mcp` instead of `python3 -m trellis_mcp` on Windows PowerShell/CMD.

1. **Sync Workspace (`--sync-workspace`):**
   ```bash
   python -m trellis_mcp --sync-workspace
   ```
   - Copies all **17 canonical `.agents/skills/pb-*/SKILL.md`** files into `.claude/skills/pb-*/SKILL.md` and `.claude/commands/pb-*.md`, pruning stale non-`/pb-*` mirrors.
   - Updates `.mcp.json` and `.agents/mcp_config.json` with the `trellis-mcp` stdio server entry (`prompts/list` dynamically serves all 17 `/pb-*` skills).
   - Removes deprecated `.agents/workflows/*.md` files (`F01`).

2. **Install Globally (`--install-global`) & Emit Editor Configs (`--emit-config`):**
   ```bash
   python -m trellis_mcp --install-global
   python -m trellis_mcp --emit-config vscode --config-out .vscode/mcp.json
   ```
   - Installs the `trellis` plugin into `~/.gemini/config/plugins/trellis/` and `~/.claude/skills/`.
   - `--emit-config` supports `vscode`, `jetbrains`, `cursor`, `windsurf`, and `claude` (with optional `--remote-url https://<vm-ip>:8443`).

3. **Offline Standards Cache & Analytics (`--sync-cache`, `--usage-report`):**
   ```bash
   python -m trellis_mcp --sync-cache
   python -m trellis_mcp --usage-report --budget-tokens 2000000
   ```
   - Caches versioned standards with `.sha256` sidecar digests into `.trellis_cache/standards/` and reports token/cost quota utilization.

4. **Host HTTP Server & Admin Dashboard (`--serve-http`):**
   ```bash
   # Loopback development (default --host 127.0.0.1)
   python -m trellis_mcp --serve-http --auto-generate-key --port 8080

   # Shared VM hosting (pass --host 0.0.0.0 + TLS + Origin allowlist)
   python -m trellis_mcp --serve-http --auto-generate-key --host 0.0.0.0 --port 8443 \
     --tls-cert /path/server.crt --tls-key /path/server.key \
     --allowed-origin https://dashboard.internal
   ```
   - Serves `GET /healthz`, `GET /readyz`, `GET /.well-known/agent.json`, `GET /admin/dashboard` (`HttpOnly` + `X-Trellis-CSRF` + nonce-CSP UI), `/admin/session`, `GET /metrics`, `POST /mcp`, `GET /bundle.json`, `GET /install.sh`, `GET/POST/PATCH/DELETE /admin/keys`, and signed `POST /admin/deploy`.

5. **Administrator API Key Lifecycle (`--generate-key`, `--list-keys`, `--rotate-key`, `--revoke-key`):**
   ```bash
   python -m trellis_mcp --generate-key team-ibanking --role member --expires-days 90 \
     --scopes trellis_get_standard,trellis_search_knowledge,trellis_classify,trellis_scan
   python -m trellis_mcp --list-keys
   python -m trellis_mcp --rotate-key team-ibanking --expires-days 90
   python -m trellis_mcp --revoke-key team-ibanking
   ```

6. **Zero-Clone Remote Client Setup (`--install-remote`):**
   ```bash
   python -m trellis_mcp --install-remote http://<vm-ip>:8080 --api-key "<team-member-api-key>"
   ```

7. **Workspace Doctor & CI Check (`--check` / `--doctor` / `--fix` / `--dry-run`):**
   ```bash
   python -m trellis_mcp --check
   python -m trellis_mcp --check --fix --dry-run
   ```
   - Validates rule YAML frontmatter, skill line budgets, JSON config validity, `.agents`/`.claude` parity, and broken relative Markdown links.
