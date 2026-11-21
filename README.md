# Trellis (`trellis-mcp`) — Open-Source Multi-AI Engineering Standard & MCP Control Plane

**Version:** `v0.1.0` (`SPEC-001` + `SPEC-002` Public OSS Hardening)  
**Primary Tools Supported:** **Antigravity IDE**, **Claude Code**, **VS Code**, **JetBrains**, **Cursor**, and **Windsurf** (via `--emit-config`)  
**Canonical Source of Truth:** [`docs/standards/`](./docs/standards/) & [`docs/specs/001-secure-multi-ai-trellis.md`](./docs/specs/001-secure-multi-ai-trellis.md)  
**Zero-Dependency MCP Server & Installer:** [`trellis_mcp/`](./trellis_mcp/) (`python -m trellis_mcp`, optional `[knowledge]` extra for `numpy`)

---

## 1. Purpose

**Trellis** (`trellis-mcp`) is a version-controlled engineering playbook, cross-IDE skill bundle (18 unified `/pb-*` skills), and zero-dependency **Model Context Protocol (MCP)** control plane for agentic and multi-AI software engineering:

1. **Consistency:** Every project—and every **Software Engineer**—follows the same quality bar when building with **AI agents, foundation models, RAG pipelines, subagents, and MCP tools**.
2. **Skill Growth:** Working with AI agents makes engineers and architects stronger (critical review of architectural/implementation plans, failing tests first, turning mistakes into explicit rules), not weaker.
3. **Single Source of Truth Across IDEs & MCP:** Teams share one canonical set of standards (`docs/standards/`) and **18 unified `/pb-*` Agent Skills** (`.agents/skills/pb-*/SKILL.md`, synced to `.claude/skills/` & `.claude/commands/`, and served directly via MCP `prompts/list` & `prompts/get`).
4. **Structured Lifecycle & Multi-AI Governance:** Every significant change follows `Plan -> Implement -> Verify -> Review` backed by Tier 2 human approval gates, loop halts, cross-model reviewer separation, data-classification routing (`Public` / `Internal` / `Confidential` / `Restricted`), and redacted JSONL audit logs.
5. **Centralized or Loopback Hosting (Zero Git Clone):** Run `trellis-mcp` safely on localhost (`127.0.0.1` default with `Origin` allowlist & `429` auth lockout) or host centrally on a team VM with HTTPS/TLS, signed `.pyz` deploys, Admin Dashboard (`HttpOnly` cookie + CSRF), and per-key tool `scopes`.

---

## 2. Repository Folder Map

```text
trellis/
├── README.md                        # Project overview, MCP/A2A reference, multi-AI router, dashboard & VM deployment
├── LICENSE                          # MIT license
├── CHANGELOG.md                     # Release history and notable changes
├── CONTRIBUTING.md                  # Development workflow, tests, and PR checklist
├── SECURITY.md                      # Vulnerability reporting and security expectations
├── CLAUDE.md                        # < 200 lines; imports standards via @docs/standards/...
├── GEMINI.md                        # Workspace entrypoint for Antigravity IDE
├── pyproject.toml                   # Stdlib-only package + optional [knowledge] numpy extra
├── .mcp.json                        # Shared workspace MCP server configuration
├── .gitignore                       # Ignores CLAUDE.local.md, settings.local.json, .env, .trellis_keys.json, .trellis-audit.jsonl
├── .env.example                     # Safe environment variable placeholders
├── trellis_mcp/                     # Zero-dependency Python MCP Control Plane & Installer
│   ├── __init__.py                  # Package version (0.1.0)
│   ├── __main__.py                  # CLI (--serve-http, --emit-config, --sync-cache, --usage-report, --scopes, --rotate-key, etc.)
│   ├── server.py                    # JSON-RPC 2.0 MCP server (18 tools, 18 /pb-* prompts, protocolVersion negotiation)
│   ├── http_server.py               # Multi-threaded HTTP MCP/A2A server, hashed key store, Origin check, lockout, sessions
│   ├── ui.py                        # Admin Dashboard SPA HTML/CSS/JS (dark/light themes, filters, pagination, key modals)
│   ├── branding.py                  # Embedded Trellis favicon asset for the Admin Dashboard
│   ├── editors.py                   # MCP config generator for VS Code, JetBrains, Cursor, Windsurf & Claude Code
│   ├── tools.py                     # Core governance tools + Luhn PAN, JWT, Myanmar NRC/phone, IBAN, prompt-wrap guards
│   ├── audit.py                     # Redacted JSONL request/tool audit logger (TrellisAuditLogger)
│   ├── knowledge.py                 # vMF hyperspherical search, (cosine, kappa) confidence, anomaly gate, drift, Canary, RCA dedup
│   ├── router.py                    # Tier & data-classification multi-AI model router + LiteLLM config generator
│   ├── pipeline.py                  # pb-pipeline state machine, loop detection, trellis_synthesize & A2A agent card
│   └── installer.py                 # Workspace sync, global installer, zero-clone remote installer, single-file .pyz builder
├── tests/
│   ├── test_trellis_mcp.py          # Core MCP, HTTP, RBAC, P2/P3 requirement tests ([REQ-MCP-01..10], [REQ-P2/P3-*])
│   └── test_spec_001_upgrades.py    # SPEC-001 hardening, vMF, router, pipeline, synthesis & skill sync tests ([REQ-TRL-01..15])
├── .agents/                         # Antigravity IDE configuration
│   ├── mcp_config.json              # Workspace MCP configuration for Antigravity IDE
│   ├── skills.json                  # Skills manifest pointing to .agents/skills
│   ├── rules/                       # Modular rules with YAML trigger frontmatter
│   └── skills/                      # 18 canonical /pb-* skills (SKILL.md) synced across platforms & MCP prompts
├── .claude/                         # Claude Code configuration
│   ├── settings.json                # Hardened deny baseline (.trellis_keys.json, ~/.ssh, exfil) + wired PreToolUse/Stop hooks
│   ├── rules/                       # Modular rules pointing to docs/standards/
│   ├── commands/                    # 18 mirrored /pb-* slash commands for Claude Code CLI
│   ├── skills/                      # 18 mirrored SKILL.md bundles (synced via --sync-workspace)
│   ├── agents/                      # Read-only code-reviewer & security-auditor, plus test-writer
│   └── hooks/                       # validate-bash.sh, secret-scan.sh, run-tests.sh
├── docs/
│   ├── specs/                       # Approved feature specs (001-secure-multi-ai-trellis.md)
│   ├── standards/                   # SINGLE SOURCE OF TRUTH (Canonical Standards & Registries)
│   │   ├── testing-standard.md
│   │   ├── performance-sla.md
│   │   ├── complexity-and-performance.md
│   │   ├── rca-playbook.md
│   │   ├── quota-efficiency.md
│   │   ├── definition-of-done.md
│   │   ├── ai-boundary.md
│   │   ├── security-baseline.md
│   │   ├── git-convention.md
│   │   ├── data-classification.md
│   │   ├── documentation-standard.md
│   │   ├── approved-mcp-servers.json
│   │   ├── ai-bom.json              # Commercial & open-weight model catalog + excluded license classes
│   │   └── standards.json           # Versioned standards manifest & provenance hashes
│   ├── knowledge/                   # Project knowledge export & research evaluation addenda
│   ├── decisions/                   # Architecture Decision Records (0001-single-source-of-truth.md)
│   ├── integrations/                # Multi-IDE integration matrix (ide-matrix.md)
│   ├── deployment-guide.md          # Completed milestones & recurring Windows/Linux VM deployment checklist
│   ├── how-to-use.md                # Practical scenario guide: when & how to use each /pb-* skill, MCP tool & CLI flag
│   └── onboarding.md                # Developer onboarding, 3-surface command table & VM setup
├── templates/                       # Review gate templates (spec, implementation-plan, walkthrough, test-plan, PR)
└── scripts/                         # setup-vm-once.ps1, build-and-deploy.ps1 & sync-tool-configs.md
```

---

## 3. `trellis-mcp` Tools, Skills, Prompts & A2A Endpoints

### 3.1 Callable MCP Tools (`18` tools)

| Tool Name | Requirement | Description |
| :--- | :--- | :--- |
| `trellis_get_standard` | `[REQ-MCP-02]`, `[REQ-P3-03]` | Returns any authoritative standard from `docs/standards/` (including historical versions) or template from `templates/`. |
| `trellis_budget` | `[REQ-MCP-02]` (`F03`) | Classifies task cost (`Class S`, `Class M`, `Class L`) and auto-upgrades 1-file Tier 2/3 changes (`auth`, `sql`, `schema`, `ledger`, `security`) to `Class M`. |
| `trellis_rca` | `[REQ-MCP-02]` (`F04`, `F10`), `[REQ-TRL-10]` | Runs the 9-step Fast RCA sequence, blocks unredacted secrets/PANs/PII, and surfaces `Similar Prior RCAs` via vMF search. |
| `trellis_spec` | `[REQ-MCP-02]` (`F12`) | Generates requirement-traceable `[REQ-NNN-XX]` specs (`Class M` 4-section Micro-Spec or `Class L` 10-section Full Spec). |
| `trellis_enhance` | `[REQ-MCP-02]` (`F10`) | Computes Little's Law concurrency ($\text{VUs} = \text{TPS} \times (R + Z)$), CPU/Memory Big-O, and I/O round-trip complexity. |
| `trellis_handoff` | `[REQ-MCP-02]` | Generates a compact ($\le 25$-line) session state handoff packet before `/clear` or context split. |
| `trellis_review` | `[REQ-MCP-02]` | Audits a unified git diff and commit message against Story DoD, test-weakening prohibitions, secret patterns, Conventional Commits, and `[REQ-NNN-XX]` traceability. |
| `trellis_doctor` | `[REQ-MCP-02]` (`F02`), `[REQ-P2-06]` | Validates rules, skill budgets, JSON configs, skill mirror parity, and broken links (with `auto_fix` / `dry_run`). |
| `trellis_test` | `[REQ-P2-01]` | Generates failing `[REQ-NNN-XX]` test skeletons for Python, TypeScript, Java, and C#. |
| `trellis_scan` | `[REQ-P2-02]`, `[REQ-TRL-05]` | Scans for Luhn-valid PANs, JWTs, Myanmar NRCs, regional phones, IBANs, and credentials (plus optional `pip-audit`). |
| `trellis_classify` | `[REQ-P2-03]` | Classifies content into `Public` / `Internal` / `Confidential` / `Restricted` and gates AI prompts/logs. |
| `trellis_mcp_registry` | `[REQ-P2-04]` | Enforces `docs/standards/approved-mcp-servers.json`, least-privilege DB flags, and transport safety. |
| `trellis_verify` | `[REQ-P3-05]` | Verifies a standard's SHA-256 hash and optional HMAC-SHA256 provenance signature. |
| `trellis_analytics` | `[REQ-P3-04]` | Reports token usage, estimated cost, and quota utilization from `.trellis_usage.json`. |
| `trellis_search_knowledge` | `[REQ-TRL-08..09]`, `[REQ-TRL-14]` | Performs vMF hyperspherical search with `(cosine, kappa)` confidence, clearance-level filtering, compression, and anomaly gating. |
| `trellis_route_model` | `[REQ-TRL-11]` | Selects legally usable cloud vs strict on-prem open-weight models by tier & data classification (and emits LiteLLM config). |
| `trellis_pipeline` | `[REQ-TRL-12]` | Enforces stage transitions (`discover` -> `done`), Tier 2 human approval gates, 3-strike loop halts, and cross-model reviewer separation. |
| `trellis_synthesize` | `[REQ-TRL-13]` | Compares multi-AI responses into explicit **Agreements** and **Divergences** without silent majority voting. |

### 3.2 Unified Slash Skills & MCP Prompts (`18` canonical `/pb-*` skills)
Every workflow playbook is stored canonically in `.agents/skills/pb-*/SKILL.md`, automatically mirrored to `.claude/skills/` and `.claude/commands/pb-*.md` (`--sync-workspace`), **and exposed directly through the MCP server (`prompts/list` & `prompts/get`)**:
- **Core Lifecycle:** `/pb-plan`, `/pb-spec`, `/pb-pipeline`, `/pb-rca`, `/pb-enhance`, `/pb-handoff`, `/pb-review` (unified Pre-PR & Code Review), `/pb-release-check`
- **Multi-AI & Knowledge:** `/pb-route`, `/pb-synthesize`, `/pb-knowledge`
- **Engineering, Git, Docs & Governance:** `/pb-git-convention`, `/pb-doc`, `/pb-data-classification`, `/pb-mcp-audit`, `/pb-test-writer`, `/pb-security-audit`, `/pb-perf-test`

### 3.3 How to Use Trellis (Task-to-Tool Quick Guide)
See the full workflow & JSON/CLI examples in **[How to Use Trellis (`docs/how-to-use.md`)](./docs/how-to-use.md)**:

| Goal | Use Slash Skill / IDE Mode | Calls MCP Tool(s) |
| :--- | :--- | :--- |
| **Deep Research & Multi-AI Analysis** | `/pb-knowledge`, `/pb-route`, `/pb-synthesize` + IDE `/boost` | `trellis_search_knowledge`, `trellis_route_model`, `trellis_synthesize` |
| **Plan & Spec a Feature (`Class M/L`)** | `/grill-me` -> `/pb-plan` -> `/pb-spec` | `trellis_budget`, `trellis_spec`, `trellis_pipeline` |
| **Debug Bugs & Slow Endpoints** | `/pb-rca`, `/pb-enhance`, `/pb-perf-test` | `trellis_rca`, `trellis_enhance` |
| **Write `[REQ-NNN-XX]` Tests First** | `/pb-test-writer` | `trellis_test` |
| **Check PII, Secrets & Supply Chain** | `/pb-data-classification`, `/pb-security-audit`, `/pb-mcp-audit` | `trellis_classify`, `trellis_scan`, `trellis_mcp_registry`, `trellis_verify`, `trellis_analytics` |
| **Audit / Scaffold Docs, Commit, Review & Handoff** | `/pb-doc`, `/pb-git-convention`, `/pb-review`, `/pb-release-check`, `/pb-handoff` | `trellis_get_standard`, `trellis_review`, `trellis_doctor`, `trellis_handoff` |

### 3.4 HTTP Security, Protocol, Discovery & Admin Dashboard (`[REQ-TRL-01..06]`, `[REQ-TRL-12]`, `[REQ-P3-02..07]`)
- **Safe Loopback Binding & Origin Check:** `--serve-http` defaults to `127.0.0.1` (`--host 0.0.0.0` explicit for VMs). Disallowed `Origin` headers on `/mcp` or `/admin/*` return `403 Forbidden` (configurable via `--allowed-origin` / `TRELLIS_ALLOWED_ORIGINS`).
- **Brute-Force Lockout, Hashed Keys & Scoped Access:** Repeated `401` failures trigger temporary `429 Too Many Requests` lockouts per IP. Keys are stored as salted SHA-256 hashes (`.trellis_keys.json`), support optional `--expires-days`, atomic `--rotate-key`, and `--scopes` (or `scopes` JSON array in `POST /admin/keys`) to restrict callable MCP tools (`403 Forbidden`).
- **Redacted JSONL Audit Trail:** Every HTTP/MCP call writes a structured event to `.trellis-audit.jsonl` (`--audit-log` / `TRELLIS_AUDIT_LOG`) with bearer auth tokens and Luhn PANs redacted and request bodies hashed via SHA-256.
- **MCP Protocol Negotiation & A2A Agent Card:** `initialize` negotiates `2025-06-18` / `2025-03-26` / `2024-11-05`; `POST /mcp` validates `MCP-Protocol-Version` (`400` if invalid); unauthenticated `GET /.well-known/agent.json` publishes the A2A agent card.
- **Admin Key Dashboard UI (`GET /admin/dashboard` in `trellis_mcp/ui.py`):** Provides an authenticated browser console with dark/light mode toggle, collapsible sidebar, live KPI summary cards (`Active Keys`, `Needs attention keys`, `Administrators`), search + role/status filtering + pagination, and modals to generate, edit (`PATCH /admin/keys/<id>`), or revoke keys. Admin keys are exchanged via `POST /admin/session` for a 15-minute `HttpOnly`, `SameSite=Strict` cookie protected by `X-Trellis-CSRF: 1` and a per-request nonce CSP (raw keys are never stored in browser storage).

| Endpoint | Auth Required | Purpose |
| :--- | :--- | :--- |
| `GET /healthz`, `GET /readyz` | None | Liveness probe and readiness status (TLS, uptime, active keys, bundle SHA-256) |
| `GET /.well-known/agent.json` | None | A2A discovery agent card for `trellis-mcp` |
| `GET /favicon.ico` | None | Embedded Trellis dashboard icon ([branding.py](./trellis_mcp/branding.py)) |
| `GET /admin`, `GET /admin/dashboard` | None (HTML shell) | Nonce-CSP Admin Key Dashboard UI ([ui.py](./trellis_mcp/ui.py)) |
| `GET/POST/DELETE /admin/session` | Admin key on `POST` | Inspect, create (`HttpOnly` cookie), or revoke browser admin session |
| `POST /mcp` | `member` or `admin` API key | JSON-RPC 2.0 MCP endpoint (enforces per-key tool `scopes` & `Origin`) |
| `GET /bundle.json`, `GET /install.sh` | `member` or `admin` API key | Signed/verified standards, rules, and `/pb-*` skill bundle + remote installer |
| `GET /metrics` | `admin` API key / cookie | Request, latency, status, path, and per-key usage counters |
| `GET/POST /admin/keys` | `admin` API key / cookie | List keys (masked prefixes) or generate new scoped member/admin keys |
| `PATCH/DELETE /admin/keys/<id>` | `admin` API key / cookie | Update key label/role (`PATCH`) or immediately revoke (`DELETE`) |
| `POST /admin/deploy` | `admin` API key + HMAC sig | Hot-reload standalone `trellis-mcp.pyz` (`X-Trellis-Signature`) |

---

## 4. Legally Usable Multi-AI Catalog (`docs/standards/ai-bom.json`)

Every model configured in [`docs/standards/ai-bom.json`](./docs/standards/ai-bom.json) and [`trellis_mcp/router.py`](./trellis_mcp/router.py) carries commercial API rights or permissive/commercial open-weight licensing (`non-commercial`, `research-only`, `CC-BY-NC`, and `AGPL-without-exception` are excluded):

- **`Public` (Commercial Cloud + Web Grounding):** `perplexity/sonar-pro`, `perplexity/sonar-reasoning-pro`, `perplexity/sonar`, `xai/grok-4`, `xai/grok-4-fast`, `xai/grok-3`, `gemini/gemini-2.5-pro`, `gemini/gemini-2.5-flash`, `anthropic/claude-sonnet-4`, `anthropic/claude-opus-4`, `openai/gpt-5`, `openai/gpt-5-codex`, `mistral/mistral-large-latest`
- **`Internal` (Commercial Non-Search Cloud):** Excludes live web-search endpoints (`perplexity/*`) automatically while routing across `anthropic/*`, `openai/*`, `gemini/*`, `xai/*`, `mistral/*` with on-prem fallbacks.
- **`Confidential` / `Restricted` / `Tier >= 3` (Strict On-Prem Only):** Blocks all cloud APIs and routes exclusively to commercial open-weight local models (`on_prem/qwen2.5-coder:32b`, `on_prem/qwen2.5:32b`, `on_prem/qwen2.5:7b`, `on_prem/mistral-nemo:12b`, `on_prem/nomic-embed-text` under **Apache-2.0**, and `on_prem/llama-3.3-70b-instruct` under **Meta Llama 3.3 Community License**).

---

## 5. Quick Start & Installation Modes

> **Windows Note:** On Windows PowerShell/CMD, run `python -m trellis_mcp` instead of `python3 -m trellis_mcp`.

### Mode A: Local Device Global Install & IDE Configs
```bash
python -m trellis_mcp --install-global
python -m trellis_mcp --sync-workspace
python -m trellis_mcp --check
python -m trellis_mcp --emit-config vscode --config-out .vscode/mcp.json
python -m trellis_mcp --sync-cache
python -m trellis_mcp --usage-report --budget-tokens 2000000
```

- **Editors:** Generate MCP configs for VS Code, JetBrains, Cursor, Windsurf, or Claude with `--emit-config` (see [IDE Integration Matrix](./docs/integrations/ide-matrix.md)).
- **Key dashboard:** Browse to `http://<host>:<port>/admin/dashboard` and sign in with an admin key (exchanged for a 15-minute `HttpOnly`, `SameSite=Strict`, CSRF-protected session cookie).
- **Optional vectorized retrieval extra:** Core `trellis-mcp` runs on pure Python stdlib; install `pip install -e ".[knowledge]"` if you want optional NumPy acceleration.

### Mode B: Private VM HTTP Server, Single-File `.pyz` Deploy & Key Operations
See the full [Deployment & Release Progress Guide (`docs/deployment-guide.md`)](./docs/deployment-guide.md) for the Windows/Linux VM bootstrap (`scripts/setup-vm-once.ps1`) and recurring 5-step deploy workflow (`scripts/build-and-deploy.ps1`).

1. **Start the HTTP Server:**
   ```bash
   # Localhost development (default --host 127.0.0.1)
   python -m trellis_mcp --serve-http --auto-generate-key --port 8080

   # Shared Host / Production (TLS required for non-loopback unless --insecure-http)
   python -m trellis_mcp --serve-http --auto-generate-key --host 0.0.0.0 --port 8443 \
     --tls-cert /path/server.crt --tls-key /path/server.key \
     --public-url https://trellis.example.com \
     --bundle-signing-key "$TRELLIS_BUNDLE_SIGNING_KEY" \
     --allowed-origin https://trellis.example.com
   ```
   - **With TLS & HMAC Bundle Signing (Production):** Pass `--tls-cert`, `--tls-key`, `--public-url`, `--bundle-signing-key`, `--allowed-origin`, `--trust-proxy`, and `--audit-log` (see [`.env.example`](./.env.example) for all supported variables).
2. **Issue, Rotate, or Revoke API Keys:**
   ```bash
   python -m trellis_mcp --generate-key team-alpha --role member --expires-days 90 \
     --scopes trellis_get_standard,trellis_search_knowledge,trellis_classify,trellis_review
   python -m trellis_mcp --list-keys
   python -m trellis_mcp --rotate-key team-alpha --expires-days 90
   python -m trellis_mcp --revoke-key team-alpha
   ```
   Or manage keys interactively in your browser at `http://127.0.0.1:8080/admin/dashboard` (generate, edit label/role, filter, or revoke).
3. **Zero-Clone Client Onboarding (Signed Bundles Over HTTPS):**
   ```bash
   # macOS / Linux / WSL / Git Bash
   export TRELLIS_API_KEY="<member-api-key>"
   export TRELLIS_BUNDLE_SIGNING_KEY="<bundle-signing-key>"
   curl -fsSL -H "Authorization: Bearer $TRELLIS_API_KEY" https://trellis.example.com/install.sh | sh
   ```
   ```powershell
   # Windows PowerShell
   python -m trellis_mcp --install-remote https://trellis.example.com --api-key "<member-api-key>" --bundle-signing-key "<bundle-signing-key>"
   ```

---

## 6. Verification & Automated Tests

Run the full requirement-linked test suite (`56` tests covering `[REQ-MCP-01..10]`, `[REQ-P2-01..06]`, `[REQ-P3-01..07]`, `[REQ-TRL-01..25]`, `[REQ-DOC-01..06]`):
```bash
python -m unittest discover -s tests -v
python -m trellis_mcp --sync-workspace
python -m trellis_mcp --check
```

---

## 7. Contribution Model

- **Single Source of Truth:** Edit canonical policies in `docs/standards/` and canonical skills in `.agents/skills/` first (see [ADR 0001](./docs/decisions/0001-single-source-of-truth.md)), then run `python -m trellis_mcp --sync-workspace`.
- **Conventional Commits & AI Disclosure:** Follow [`git-convention.md`](./docs/standards/git-convention.md) (`/git-convention`) and record rationale in `docs/decisions/` or `CHANGELOG.md`.
- **"Review Comment -> Rule" Loop:** If the same code-review comment appears **more than twice**, promote it into a Trellis rule or skill ([docs/onboarding.md](./docs/onboarding.md)).
