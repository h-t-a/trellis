# `ai-dev-playbook` (Trellis) — Enterprise Multi-AI Engineering Standard & MCP Control Plane

**Version:** `v0.1.0` (`SPEC-001` Enterprise Multi-AI & Security Upgrade)  
**Primary Tools Supported:** **Antigravity IDE**, **Claude Code**, **VS Code**, **JetBrains**, **Cursor**, and **Windsurf** (via `--emit-config`)  
**Canonical Source of Truth:** [`docs/standards/`](./docs/standards/) & [`docs/specs/001-secure-multi-ai-trellis.md`](./docs/specs/001-secure-multi-ai-trellis.md)  
**Zero-Dependency MCP Server & Installer:** [`trellis_mcp/`](./trellis_mcp/) (`python -m trellis_mcp`, optional `[knowledge]` extra for `numpy`)

---

## 1. Purpose

`ai-dev-playbook` (**Trellis**) is a version-controlled engineering playbook, cross-IDE skill bundle (18 skills), and zero-dependency **Model Context Protocol (MCP)** control plane (`trellis-mcp`) for agentic and multi-AI software engineering:

1. **Consistency:** Every project—and every **Software Engineer**—follows the same quality bar when building with **AI agents, foundation models, RAG pipelines, subagents, and MCP tools**.
2. **Skill Growth:** Working with AI agents makes engineers and architects stronger (critical review of architectural/implementation plans, failing tests first, turning mistakes into explicit rules), not weaker.
3. **Single Source of Truth Across IDEs:** Teams share one canonical set of standards (`docs/standards/`) and unified Agent Skills (`.agents/skills/*/SKILL.md` synced to `.claude/skills/*/SKILL.md`).
4. **Structured Lifecycle & Multi-AI Governance:** Every significant change follows `Plan -> Implement -> Verify -> Review` backed by Tier 2 human approval gates, loop halts, cross-model reviewer separation, data-classification routing (`Public` / `Internal` / `Confidential` / `Restricted`), and redacted JSONL audit logs.
5. **Centralized or Loopback Hosting (Zero Git Clone):** Run `trellis-mcp` safely on localhost (`127.0.0.1` default with `Origin` allowlist & `429` auth lockout) or host centrally on a team VM with HTTPS/TLS, signed `.pyz` deploys, Admin Dashboard (`HttpOnly` cookie + CSRF), and per-key tool `scopes`.

---

## 2. Repository Folder Map

```text
trellis/
├── README.md                        # Project overview, MCP/A2A reference, multi-AI router, and VM deployment
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
│   ├── __main__.py                  # CLI (--serve-http, --host 127.0.0.1 default, --scopes, --allowed-origin, --audit-log, etc.)
│   ├── server.py                    # JSON-RPC 2.0 MCP server (18 tools, 14 prompts, protocolVersion negotiation)
│   ├── http_server.py               # Multi-threaded HTTP MCP/A2A server, mtime key cache, Origin check, lockout, dashboard
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
│   └── skills/                      # 18 canonical skills (SKILL.md) synced across platforms
├── .claude/                         # Claude Code configuration
│   ├── settings.json                # Hardened deny baseline (.trellis_keys.json, ~/.ssh, exfil) + wired PreToolUse/Stop hooks
│   ├── rules/                       # Modular rules pointing to docs/standards/
│   ├── commands/                    # 18 mirrored slash commands for Claude Code CLI
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
│   │   ├── approved-mcp-servers.json
│   │   ├── ai-bom.json              # Commercial & open-weight model catalog + excluded license classes
│   │   └── standards.json           # Versioned standards manifest & provenance hashes
│   ├── knowledge/                   # Project knowledge export & research evaluation addenda
│   ├── decisions/                   # Architecture Decision Records (0001-single-source-of-truth.md)
│   ├── integrations/                # Multi-IDE integration matrix (ide-matrix.md)
│   ├── deployment-guide.md          # Completed milestones & recurring Windows/Linux VM deployment checklist
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

### 3.2 Unified Slash Skills (`18` canonical skills)
Stored canonically in `.agents/skills/*/SKILL.md` and synced to `.claude/skills/*/SKILL.md` (and mirrored under `.claude/commands/*.md`):
- **Core Lifecycle:** `/pb-plan`, `/pb-spec`, `/pb-pipeline`, `/pb-rca`, `/pb-enhance`, `/pb-handoff`, `/pb-review`, `/pb-release-check`
- **Multi-AI & Knowledge:** `/pb-route`, `/pb-synthesize`, `/pb-knowledge`
- **Engineering, Git & Governance:** `/git-convention`, `/data-classification`, `/mcp-registry-audit`, `/test-writer`, `/security-audit`, `/code-review`, `/perf-test`

### 3.3 HTTP Security, Protocol & Discovery Features (`[REQ-TRL-01..06]`, `[REQ-TRL-12]`)
- **Safe Loopback Binding & Origin Check:** `--serve-http` defaults to `127.0.0.1` (`--host 0.0.0.0` explicit for VMs). Disallowed `Origin` headers on `/mcp` or `/admin/*` return `403 Forbidden` (configurable via `--allowed-origin` / `TRELLIS_ALLOWED_ORIGINS`).
- **Brute-Force Lockout & Scoped Keys:** Repeated `401` failures trigger temporary `429 Too Many Requests` lockouts per IP. API keys accept `--scopes` (or `scopes` JSON array in `POST /admin/keys`) to restrict callable MCP tools (`403 Forbidden`).
- **Redacted JSONL Audit Trail:** Every HTTP/MCP call writes a structured event to `.trellis-audit.jsonl` (`--audit-log`) with Bearer tokens and Luhn PANs redacted and request bodies hashed via SHA-256.
- **MCP Protocol Negotiation & A2A Agent Card:** `initialize` negotiates `2025-06-18` / `2025-03-26` / `2024-11-05`; `POST /mcp` validates `MCP-Protocol-Version` (`400` if invalid); unauthenticated `GET /.well-known/agent.json` publishes the A2A agent card.

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

   # Shared VM / LAN (pass --host 0.0.0.0 explicitly + TLS in production)
   python -m trellis_mcp --serve-http --auto-generate-key --host 0.0.0.0 --port 8443 \
     --tls-cert /path/server.crt --tls-key /path/server.key \
     --allowed-origin https://dashboard.internal
   ```
2. **Issue Scoped or Role-Based API Keys:**
   ```bash
   python -m trellis_mcp --generate-key team-ibanking --role member --expires-days 90 \
     --scopes trellis_get_standard,trellis_search_knowledge,trellis_classify,trellis_scan
   python -m trellis_mcp --list-keys
   python -m trellis_mcp --rotate-key team-ibanking
   python -m trellis_mcp --revoke-key team-ibanking
   ```
3. **Zero-Clone Client Onboarding:**
   ```bash
   # macOS / Linux / WSL / Git Bash
   export TRELLIS_API_KEY="<member-api-key>"
   curl -fsSL -H "Authorization: Bearer $TRELLIS_API_KEY" http://<vm-ip>:8080/install.sh | sh
   ```
   ```powershell
   # Windows PowerShell
   python -m trellis_mcp --install-remote http://<vm-ip>:8080 --api-key "<member-api-key>"
   ```

---

## 6. Verification & Automated Tests

Run the full requirement-linked test suite (`[REQ-MCP-01..10]`, `[REQ-P2-*]`, `[REQ-P3-*]`, `[REQ-TRL-01..15]`):
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
