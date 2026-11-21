# Security Baseline

**Status:** Working draft v0.1 `[SOURCE: Developers + images + docs]`  
**Source:** Canonical Trellis engineering standard (`docs/standards/`)

---

## 1. Mandatory Security Controls `[SOURCE: Developers + images + docs]`

Every repository and developer workstation adopting this playbook must enforce the following seven baseline controls:

1. **Zero Secrets in AI Context or Config Files:**
   - Never place secrets, API keys, tokens, or credentials in `CLAUDE.md`, `GEMINI.md`, `.claude/rules/`, `.agents/rules/`, skills, commands, or `.mcp.json`.
   - Commit `.env.example` with safe placeholder values only; keep real `.env` files strictly gitignored.
2. **Gitignore Local AI Overrides:**
   - Always gitignore `CLAUDE.local.md`, `settings.local.json`, and `.claude/settings.local.json` so machine-local experiments or personal notes are never committed.
3. **Pre-Commit Secret Detection Hook:**
   - Run automated secret scanning (`.claude/hooks/secret-scan.sh` or pre-commit equivalent) to block accidental commits of tokens, private keys, or credentials.
4. **Minimum-Permission MCP Scope:**
   - Configure MCP servers (`.mcp.json`) with least privilege.
   - Use **read-only database access** (`DB_READONLY=true` / read-only DB role) wherever possible.
   - Never connect MCP servers to production databases or real customer data (Tier 3 in [ai-boundary.md](./ai-boundary.md)).
5. **Pre-Configure Tool Permissions and Browser Allowlist/Denylist:**
   - Before first use on a real project, explicitly configure tool permissions (`/permissions` in Antigravity IDE, `.claude/settings.json` in Claude Code) and browser allowlist/denylist rules (using a separate Chrome profile in Antigravity).
6. **Block Unsafe Shell Operations via Hooks:**
   - Remember the core principle: **a rule is a request; a hook is a guarantee.**
   - Use pre-execution command validation hooks (`.claude/hooks/validate-bash.sh`) to block destructive or unsafe shell commands (e.g., recursive deletions, force pushes, or outbound data exfiltration).
7. **Dedicated Security Auditor Subagent:**
   - Maintain a read-only `security-auditor` subagent (`.claude/agents/security-auditor.md`) and `/pb-security-audit` skill to review authentication, authorization, input validation, dependency changes, and AI boundary compliance prior to merge.

---

## 2. Runtime Hardening, Scanning & Browser Controls (`[REQ-TRL-01]..[REQ-TRL-07]`)

1. **HTTP / MCP Origin & Lockout Hardening:** Default local server bind is `127.0.0.1` (`--host 0.0.0.0` explicit for VM/LAN), `Origin` allowlist enforced on `/mcp` and `/admin/*` (`403`), and repeated `401` failures trigger temporary `429` lockout (`[REQ-TRL-01]`, `[REQ-TRL-03]`).
2. **SAST, Secret & Redaction Scanning Baseline:** `.claude/hooks/secret-scan.sh`, `.claude/hooks/validate-bash.sh`, and `.claude/settings.json` enforce local secret/exfiltration denials (`[REQ-TRL-07]`). `trellis_scan` / `trellis_rca` run Luhn PAN, JWT, Myanmar NRC, regional phone, and IBAN checks (`[REQ-TRL-05]`).
3. **Banking Archetype Permission Baseline & Browser Controls:** Standard deny rules forbid reading `.env*`, `.trellis_keys.json`, `~/.ssh/*`, `~/.aws/*` and outbound exfiltration (`scp`, `nc`, `curl -d`, `wget --post`). Browser automation must use an isolated profile restricted to approved localhost and corporate documentation/issue-tracker domains; raw banking/core-ledger origins are denied (`Tier 3`).
