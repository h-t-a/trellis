# `ai-dev-playbook` (Trellis) — Agentic & AI-Driven Engineering Standard & MCP Server

**Version:** `v0.1.0`  
**Primary Tools Supported:** **Antigravity IDE** & **Claude Code**  
**Canonical Source of Truth:** [`docs/standards/`](./docs/standards/)  
**Zero-Dependency MCP Server & Installer:** [`trellis_mcp/`](./trellis_mcp/) (`python -m trellis_mcp`)

---

## 1. Purpose

`ai-dev-playbook` (**Trellis**) is a version-controlled engineering playbook, cross-IDE skill bundle, and zero-dependency **Model Context Protocol (MCP)** server (`trellis-mcp`) for agentic & AI-driven software engineering:

1. **Consistency:** Every project—and every **Software Engineer**—follows the same quality bar when building with **AI agents, foundation models, RAG pipelines, subagents, and MCP tools**.
2. **Skill Growth:** Working with AI agents and models makes engineers and architects stronger (critical review of architectural/implementation plans, failing tests first, turning mistakes into explicit rules), not weaker.
3. **Single Source of Truth Across IDEs:** Teams share one canonical set of standards (`docs/standards/`) and unified Agent Skills (`.agents/skills/*/SKILL.md` synced to `.claude/skills/*/SKILL.md`).
4. **Structured Lifecycle:** Every significant change follows the same lifecycle: **`Plan -> Implement -> Verify -> Review`**.
5. **Centralized Team Hosting (Zero Git Clone):** Host `trellis-mcp` on a private VM over HTTP with Administrator API Key Auto-Generation and per-user/per-team Bearer token RBAC so teammates can onboard with a single command.

---

## 2. Repository Folder Map

```text
trellis/
├── README.md                        # Project overview, MCP server guide, and VM deployment
├── NOTICE.md                        # Detailed MCP setup, API key management, and Windows notice
├── CLAUDE.md                        # < 200 lines; imports standards via @docs/standards/...
├── GEMINI.md                        # Workspace entrypoint for Antigravity IDE
├── pyproject.toml                   # Zero-dependency Python package definition (trellis-mcp)
├── .mcp.json                        # Shared workspace MCP server configuration
├── .gitignore                       # Ignores CLAUDE.local.md, settings.local.json, .env, .trellis_keys.json
├── .env.example                     # Safe environment variable placeholders
├── trellis_mcp/                     # Zero-dependency Python MCP Server & Installer
│   ├── __init__.py                  # Package version (0.1.0)
│   ├── __main__.py                  # CLI entrypoint (--serve-http, --auto-generate-key, --generate-key, etc.)
│   ├── server.py                    # JSON-RPC 2.0 MCP server over stdio
│   ├── http_server.py               # Multi-threaded HTTP MCP server, TrellisKeyStore & /admin/keys RBAC
│   ├── tools.py                     # 8 callable MCP tools with Tier 2/3 & quota guards
│   └── installer.py                 # Workspace sync, global installer, and zero-clone remote installer
├── tests/
│   └── test_trellis_mcp.py          # Requirement-linked unit & HTTP integration tests ([REQ-MCP-01..08])
├── .agents/                         # Antigravity IDE configuration
│   ├── mcp_config.json              # Workspace MCP configuration for Antigravity IDE
│   ├── skills.json                  # Skills manifest pointing to .agents/skills
│   ├── rules/                       # Modular rules with mandatory YAML trigger frontmatter
│   └── skills/                      # Canonical /pb-* and engineering skills (SKILL.md)
├── .claude/                         # Claude Code configuration
│   ├── settings.json                # Permissions baseline
│   ├── rules/                       # Modular rules pointing to docs/standards/
│   ├── commands/                    # Mirrored /pb-* slash commands for Claude Code CLI
│   ├── skills/                      # Mirrored SKILL.md bundles (synced via --sync-workspace)
│   ├── agents/                      # Read-only code-reviewer & security-auditor, plus test-writer
│   └── hooks/                       # validate-bash.sh, secret-scan.sh, run-tests.sh
├── docs/
│   ├── standards/                   # SINGLE SOURCE OF TRUTH (9 Canonical Standards)
│   │   ├── testing-standard.md
│   │   ├── performance-sla.md
│   │   ├── complexity-and-performance.md
│   │   ├── rca-playbook.md
│   │   ├── quota-efficiency.md
│   │   ├── definition-of-done.md
│   │   ├── ai-boundary.md
│   │   ├── security-baseline.md
│   │   └── git-convention.md
│   ├── knowledge/                   # Project knowledge export & research evaluation addenda
│   ├── decisions/                   # Architecture Decision Records (0001-single-source-of-truth.md)
│   ├── deployment-guide.md          # Completed milestones & recurring Windows VM deployment checklist
│   └── onboarding.md                # Developer onboarding, 3-surface command table & VM setup
├── templates/                       # Review gate templates (spec, implementation-plan, walkthrough, test-plan, PR)
└── scripts/                         # build-and-deploy.ps1 & sync-tool-configs.md
```

---

## 3. `trellis-mcp` Tools, Skills & Resources

### 3.1 Callable MCP Tools (`trellis_*`)

| Tool Name | Requirement | Description |
| :--- | :--- | :--- |
| `trellis_get_standard` | `[REQ-MCP-02]` | Returns any authoritative standard from `docs/standards/` or template from `templates/`. |
| `trellis_budget` | `[REQ-MCP-02]` (`F03`) | Classifies task cost (`Class S`, `Class M`, `Class L`) and auto-upgrades 1-file Tier 2/3 changes (`auth`, `sql`, `schema`, `ledger`, `security`) to `Class M`. |
| `trellis_rca` | `[REQ-MCP-02]` (`F04`, `F10`) | Runs the 9-step Fast RCA sequence; blocks unredacted PAN/card numbers and secrets before analysis. |
| `trellis_spec` | `[REQ-MCP-02]` (`F12`) | Generates requirement-traceable `[REQ-NNN-XX]` specs (`Class M` 4-section Micro-Spec or `Class L` 10-section Full Spec). |
| `trellis_enhance` | `[REQ-MCP-02]` (`F10`) | Computes Little's Law concurrency ($\text{VUs} = \text{TPS} \times (R + Z)$), CPU/Memory Big-O, and I/O round-trip complexity. |
| `trellis_handoff` | `[REQ-MCP-02]` | Generates a compact ($\le 25$-line) session state handoff packet before `/clear` or context split. |
| `trellis_review` | `[REQ-MCP-02]` | Audits a unified git diff and commit message against Story DoD, test-weakening prohibitions, secret patterns, Conventional Commits, and `[REQ-NNN-XX]` traceability. |
| `trellis_doctor` | `[REQ-MCP-02]` (`F02`) | Validates `.agents/rules/*.md` YAML frontmatter, skill line-count budgets, and deprecated workflow files (with optional `auto_fix`). |

### 3.2 Unified Slash Skills (`/pb-*`)
Stored canonically in `.agents/skills/*/SKILL.md` and synced to `.claude/skills/*/SKILL.md`:
- `/pb-plan` — Task classification (`S/M/L` & Tier 1–3) + Implementation Plan gate before writing code.
- `/pb-spec` — Spec-Driven Development generator (`Class M` Micro-Spec or `Class L` Full Spec).
- `/pb-rca` — 9-step Root Cause Analysis & minimal bug fix workflow (absorbs `/pb-fix`).
- `/pb-enhance` — Little's Law sizing + Big-O and I/O complexity optimization (absorbs `/pb-complexity`).
- `/pb-handoff` — Compact session handoff summary generator.
- `/pb-review` — Pre-PR review check against Story DoD, AI Boundary, Security Baseline, and Git convention.
- `/pb-release-check` — Release-level Definition of Done & Performance SLA gate.
- Plus specialist skills: `test-writer`, `security-audit`, `code-review`, and `perf-test`.

---

## 4. Quick Start & Installation Modes

> **Windows Note:** On Windows PowerShell/CMD, run `python -m trellis_mcp` instead of `python3 -m trellis_mcp`.

### Mode A: Local Device Global Install (All Projects on Your Machine)
Install the `trellis` plugin, rules, `/pb-*` skills, and `trellis-mcp` stdio server globally into `~/.gemini/config/` and `~/.claude/`:
```bash
python -m trellis_mcp --install-global
python -m trellis_mcp --check
```

### Mode B: Private VM HTTP Server, Single-File `.pyz` Deploy & Admin Key Management (`[REQ-MCP-05..09]`)
See the full [Deployment & Release Progress Guide (`docs/deployment-guide.md`)](./docs/deployment-guide.md) for the completed milestones and the 5-step recurring deployment checklist.

Host `trellis-mcp` centrally on a Windows or Linux VM using the **standalone single-file bundle (`dist\trellis-mcp.pyz`, ~71 KB)** so you never need to copy the full repository folder to the VM:

0. **Build & Deploy `dist\trellis-mcp.pyz` from Your Local Machine:**
   ```powershell
   # Runs workspace doctor + 14 unit tests, builds dist\trellis-mcp.pyz, and optionally deploys to Windows VM:
   .\scripts\build-and-deploy.ps1
   .\scripts\build-and-deploy.ps1 -VmHost "<vm-ip>" -VmUser "<domain>\<vm-user>"
   ```

1. **Start the HTTP Server with Auto-Generated Administrator Key:**
   ```bash
   # Local/loopback (recommended for development)
   python -m trellis_mcp --serve-http --auto-generate-key --host 127.0.0.1 --port 8080

   # Production: terminate TLS in the server (requires a PEM cert + key)
   python -m trellis_mcp --serve-http --auto-generate-key --host 0.0.0.0 --port 8443 \
     --tls-cert /path/server.crt --tls-key /path/server.key
   ```
   - Automatically generates an `admin` key (`trl_admin_<random>`) on first boot and persists it to `.trellis_keys.json` (gitignored). Only a salted SHA-256 hash is stored; the raw key is printed **once to stderr** and cannot be recovered from disk.
   - Hardening defaults: keys are hashed at rest, support `--expires-days` and `--rotate-key`, HTTP requests are limited to `--max-body-bytes` (default 1 MiB), per-client rate limited (`--rate-limit`, default 120/window), and socket reads time out (`--request-timeout`).

2. **Issue, List, and Revoke User or Team API Keys (As Administrator):**
   - **Via CLI on the VM (takes effect immediately without restarting the server):**
     ```bash
     # Generate a member key for another user or team
     python -m trellis_mcp --generate-key team-ibanking --role member

     # List all issued keys (masked prefixes, roles, timestamps, status)
     python -m trellis_mcp --list-keys

     # Immediately revoke a key by key_id or label
     python -m trellis_mcp --revoke-key team-ibanking
     ```
   - **Remotely via HTTP Admin Endpoints (`Authorization: Bearer <ADMIN_KEY>`):**
     ```bash
     # Issue a new team member key (returns api_key, key_id, and ready-to-share install_command)
     curl -s -X POST http://<vm-ip>:8080/admin/keys \
       -H "Authorization: Bearer <ADMIN_API_KEY>" \
       -H "Content-Type: application/json" \
       -d '{"label": "team-ibanking", "role": "member"}'

     # List issued keys
     curl -s http://<vm-ip>:8080/admin/keys \
       -H "Authorization: Bearer <ADMIN_API_KEY>"

     # Revoke a key by key_id or label
     curl -s -X DELETE http://<vm-ip>:8080/admin/keys/team-ibanking \
       -H "Authorization: Bearer <ADMIN_API_KEY>"
     ```
   - **RBAC Enforcement:** Keys issued with `"role": "member"` can access `POST /mcp`, `GET /bundle.json`, and `GET /install.sh`, but receive `403 Forbidden` on `/admin/keys`.
   - **Bundle signing (optional):** Set `TRELLIS_BUNDLE_SIGNING_KEY` on the server to emit an `X-Trellis-Bundle-Signature` HMAC header on `/bundle.json` and `/install.sh`. Clients that set the same env var (or `--signing-key`) will refuse unsigned or tampered bundles.
   - **Signed deploys:** `POST /admin/deploy` now requires `X-Trellis-Signature: HMAC-SHA256(payload, admin_bearer_token)`; `scripts/build-and-deploy.ps1` computes it automatically.

3. **Zero-Clone Client Onboarding (for Teammates):**
   - **macOS / Linux / WSL / Git Bash:**
     ```bash
     export TRELLIS_API_KEY="<member-api-key>"
     curl -fsSL -H "Authorization: Bearer $TRELLIS_API_KEY" http://<vm-ip>:8080/install.sh | sh
     ```
   - **Windows PowerShell:**
     ```powershell
     python -m trellis_mcp --install-remote http://<vm-ip>:8080 --api-key "<member-api-key>"
     ```

---

## 5. Verification & Automated Tests

Run the full requirement-linked unit and HTTP integration test suite (`[REQ-MCP-01]` through `[REQ-MCP-08]`):
```bash
python -m unittest tests/test_trellis_mcp.py -v
```

---

## 6. Contribution Model

- **Single Source of Truth:** Edit canonical policies in `docs/standards/` and canonical skills in `.agents/skills/` first (see [ADR 0001](./docs/decisions/0001-single-source-of-truth.md)), then run `python -m trellis_mcp --sync-workspace`.
- **Record Rationale:** Every change to a rule, hook, or AI-boundary tier records a short reason in `docs/decisions/` (ADR) or the changelog.
- **"Review Comment -> Rule" Loop:** If the same code-review comment appears **more than twice**, propose a rule or skill so the standard evolves from real project feedback ([docs/onboarding.md](./docs/onboarding.md)).
