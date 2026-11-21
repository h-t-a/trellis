# How to Use Trellis (`ai-dev-playbook` & `trellis-mcp`)

This guide explains **how to use Trellis in daily work** and **which slash skill (`/pb-*`), MCP tool (`trellis_*`), or CLI command to pick** for each engineering, research, security, or team administration task.

---

## 1. How Trellis Fits Together (The 3 Layers)

| Layer | What You Type / Run | What It Does |
| :--- | :--- | :--- |
| **1. Slash Skills (`/pb-*`) & IDE Modes** | `/pb-plan`, `/pb-spec`, `/pb-rca`, `/pb-review`, plus IDE commands like `/boost`, `/grill-me`, `/plan` | Guides the AI agent step-by-step through a curated engineering workflow (also exposed via MCP `prompts/list` & `prompts/get`). |
| **2. Callable MCP Tools (`18` `trellis_*` tools)** | Automatically invoked by your AI assistant (or called over JSON-RPC `/mcp`) | Runs deterministic checks, redaction scans, Little's Law sizing, vMF semantic search, model routing, and spec/test skeleton generators. |
| **3. CLI & Admin Control Plane (`python -m trellis_mcp`)** | Run in terminal (`--sync-workspace`, `--check`, `--emit-config`, `--serve-http`, `--generate-key`) or open `/admin/dashboard` | Installs skills/rules across IDEs, validates repo hygiene, hosts centralized HTTP MCP/A2A endpoints, and manages team RBAC API keys. |

---

## 2. Quick Cheat Sheet: When to Use Which Tool

| What You Are Trying to Do | Start With (Slash Skill / IDE) | Backing MCP Tool(s) |
| :--- | :--- | :--- |
| **Scope a task & avoid under/over-engineering** | `/pb-plan` | `trellis_budget`, `trellis_get_standard` |
| **Write testable `[REQ-NNN-XX]` specs before coding** | `/pb-spec` (pair with `/grill-me` first if design is unclear) | `trellis_spec` |
| **Enforce multi-stage approvals & reviewer separation** | `/pb-pipeline` | `trellis_pipeline` |
| **Do deep research & architecture analysis** | `/pb-knowledge`, `/pb-route`, `/pb-synthesize` + IDE `/boost` | `trellis_search_knowledge`, `trellis_route_model`, `trellis_synthesize` |
| **Debug a bug, exception, or deadlock** | `/pb-rca` | `trellis_rca`, `trellis_search_knowledge` |
| **Analyze latency, DB I/O round-trips, or Big-O** | `/pb-enhance` | `trellis_enhance` |
| **Write failing `[REQ-NNN-XX]` tests first (TDD)** | `/pb-test-writer` | `trellis_test` |
| **Design SLA / load tests (Little's Law)** | `/pb-perf-test` | `trellis_enhance`, `trellis_get_standard` (`performance-sla`) |
| **Check secrets, Luhn PANs, NRC, JWTs, or data tiers** | `/pb-data-classification` | `trellis_classify`, `trellis_scan` |
| **Audit MCP servers, standard hashes & token cost** | `/pb-mcp-audit` | `trellis_mcp_registry`, `trellis_verify`, `trellis_analytics` |
| **Audit security & AI boundary compliance** | `/pb-security-audit` | `trellis_scan`, `trellis_classify`, `trellis_mcp_registry` |
| **Save state before `/clear` or `/compact`** | `/pb-handoff` | `trellis_handoff` |
| **Commit & push cleanly (Conventional Commits)** | `/pb-git-convention` | `trellis_scan`, `trellis_review` |
| **Audit or scaffold project documentation (Diátaxis, ADRs, CI)** | `/pb-doc` | `trellis_get_standard`, `trellis_doctor`, `trellis_scan` |
| **Pre-PR & release gate review** | `/pb-review`, `/pb-release-check` | `trellis_review`, `trellis_doctor`, `trellis_scan` |

---

## 3. Practical Workflows & Examples

### Workflow A: Starting a New Feature (`Budget -> Plan -> Spec -> Tests`)
1. **Check task class & safety tier:** Ask your agent or call `trellis_budget` (`file_count`, `task_description`).
   - *Rule:* Even a 1-file change touching `auth`, `sql`, `schema`, `ledger`, or `security` automatically upgrades from `Class S` to `Class M` (requires a Spec/Plan).
2. **Clarify & plan:** Run **`/grill-me`** to resolve open design questions, then **`/pb-plan`** (or `/plan`) to produce an Implementation Plan and pause for human approval.
3. **Write a requirement-linked Spec:** Run **`/pb-spec`** -> calls `trellis_spec(spec_id="SPEC-042", title="...", problem="...", task_class="L", requirements=[...])` so every requirement gets a `[REQ-042-01]` ID.
4. **Write failing tests first:** Run **`/pb-test-writer`** -> calls `trellis_test` (`python`, `typescript`, `java`, or `csharp`) to scaffold Red `[REQ-NNN-XX]` tests before implementing production code.

### Workflow B: Deep Research, Design Analysis & Multi-AI Synthesis
1. **Search internal standards & past RCAs first (`trellis_search_knowledge` / `/pb-knowledge`):**
   ```json
   {
     "query": "session timeout CSRF cookie requirements",
     "caller_clearance": "Internal",
     "top_k": 5,
     "deduplicate": true
   }
   ```
   Returns top chunks ranked with von Mises-Fisher `(cosine, kappa)` confidence and blocks documents above your clearance level.
2. **Pick the right AI model safely (`trellis_route_model` / `/pb-route`):**
   - `data_classification="Public", task_type="research"` -> routes to `perplexity/sonar-pro`, `perplexity/sonar-reasoning-pro`, `gemini/gemini-2.5-pro`, `xai/grok-4`, `anthropic/claude-sonnet-4`.
   - `data_classification="Internal", task_type="research"` -> automatically strips live web-search endpoints (`perplexity/*`).
   - `data_classification="Confidential"` or `"Restricted"` (or `tier=3`) -> blocks all external cloud APIs and routes strictly on-prem (`on_prem/qwen2.5:32b`, `on_prem/qwen2.5-coder:32b`, `on_prem/llama-3.3-70b-instruct`).
   - Pass `"emit_litellm_config": true` to export a ready-to-use LiteLLM proxy config.
3. **Cross-check multiple AI answers (`trellis_synthesize` / `/pb-synthesize`):**
   Pass `prompt` and `responses: [{"model": "...", "answer": "...", "confidence": 0.85, "citations": [...]}]` to get an explicit **Agreements vs. Divergences** table instead of guessing or silent voting.
4. **Complex reasoning in IDE:** Pair these with Antigravity IDE's **`/boost`** for multi-perspective architecture deep dives or **`research` subagent** for wide codebase exploration.

### Workflow C: Debugging & Performance Analysis
- **Bugs, exceptions, or test failures (`/pb-rca` -> `trellis_rca`):**
  Runs the 9-step Fast RCA protocol (blocks unredacted secrets/PANs before analysis, limits suspect scope to 3 hypotheses / 3 call-chain hops, and checks prior RCA matches).
  ```json
  {
    "symptom": "403 Forbidden on POST /admin/keys after session cookie login",
    "evidence": "Missing X-Trellis-CSRF header on cookie-authenticated request",
    "suspect_files": ["trellis_mcp/http_server.py", "trellis_mcp/ui.py"]
  }
  ```
- **Performance & concurrency sizing (`/pb-enhance` -> `trellis_enhance`):**
  Calculates virtual users using Little's Law ($\text{VUs} = \text{TPS} \times (R + Z)$) and audits CPU/memory Big-O and DB/network round-trips.
  ```json
  {
    "target": "GET /admin/keys pagination query",
    "tps": 120,
    "response_time_sec": 0.08,
    "think_time_sec": 2.0,
    "data_size_n": 50000,
    "current_behavior": "Full table scan per request without composite index",
    "mode": "analyze"
  }
  ```

### Workflow D: Security, Privacy & Governance Gates
- **Before sending code/logs to external LLMs (`trellis_classify` & `trellis_scan` / `/pb-data-classification`):**
  - `trellis_classify(content="...", target="prompt")` classifies text into `Public` / `Internal` / `Confidential` / `Restricted` without echoing secrets.
  - `trellis_scan(path=".")` scans repository files for Luhn-valid PANs, JWTs, Myanmar NRCs, regional phones, IBANs, and credentials (and runs `pip-audit` if installed).
- **MCP supply-chain & provenance audit (`/pb-mcp-audit`):**
  - `trellis_mcp_registry` checks `.mcp.json` / `.agents/mcp_config.json` against `docs/standards/approved-mcp-servers.json`.
  - `trellis_verify(name="security-baseline", version="0.1")` verifies SHA-256 and optional HMAC-SHA256 integrity.
  - `trellis_analytics(budget_tokens=2000000)` reports token usage, cost, and `OK`/`WARN`/`EXCEEDED` verdicts from `.trellis_usage.json`.

### Workflow E: Committing, Reviewing & Releasing Safely
1. **Commit (`git`):** Run **`/pb-git-convention`** — creates `<type>/<short-kebab>` branches, checks staged diffs for secrets, runs tests, and formats `<type>(<scope>): <imperative summary>` (`<= 72` chars, lowercase, no trailing `.`).
2. **Code Review (`/pb-review` -> `trellis_review`):** Checks unified git diff + commit message against Story DoD, blocks skipped/weakened tests (`@unittest.skip`, `it.skip`, `@Disabled`), checks `[REQ-NNN-XX]` traceability, and verifies Conventional Commits.
3. **Pipeline State Gate (`trellis_pipeline` / `/pb-pipeline`):** Tracks `research -> plan -> spec -> implement -> review -> deploy`, refuses skipping stages, enforces `human_approved=true` for Tier >= 2 transitions, halts 3-strike loops, and enforces cross-model separation (`writer_model != reviewer_model`).
4. **Release Gate (`/pb-release-check`):** Verifies Story/Release DoD, SLA targets, migration safety, and rollback plan.
5. **Context Handoff (`/pb-handoff` -> `trellis_handoff`):** Compresses current goal, decisions, files touched, and exact next step into `<= 25` lines before starting a fresh session.

---

## 4. Command-Line & Multi-IDE Setup Reference

> **Windows Note:** Always use `python -m trellis_mcp` on Windows PowerShell/CMD (`python3` may hit the Microsoft Store alias).

### Local Workspace & Multi-IDE Setup
```powershell
# 1. Install Trellis plugin & skills globally (~/.gemini/config & ~/.claude/skills)
python -m trellis_mcp --install-global

# 2. Sync .agents/skills/pb-* -> .claude/skills/ & .claude/commands/ and update MCP JSONs
python -m trellis_mcp --sync-workspace

# 3. Validate rules, YAML frontmatter, skill line budgets & relative links
python -m trellis_mcp --check
python -m trellis_mcp --check --fix --dry-run

# 4. Generate MCP config for VS Code, JetBrains, Cursor, Windsurf, or Claude
python -m trellis_mcp --emit-config vscode --config-out .vscode/mcp.json
python -m trellis_mcp --emit-config cursor --config-out .cursor/mcp.json

# 5. Cache standards offline & check usage/cost report
python -m trellis_mcp --sync-cache
python -m trellis_mcp --usage-report --budget-tokens 2000000
```

### Shared HTTP Server, Admin Dashboard & API Keys
```powershell
# Start local HTTP server + auto-generated admin key (printed once to stderr)
python -m trellis_mcp --serve-http --auto-generate-key --port 8080

# Open browser Admin Dashboard (sign in via 15-min HttpOnly cookie + CSRF UI):
# http://127.0.0.1:8080/admin/dashboard

# Issue a least-privilege scoped member key for a teammate
python -m trellis_mcp --generate-key team-alpha --role member --expires-days 90 `
  --scopes trellis_get_standard,trellis_search_knowledge,trellis_classify,trellis_review

# List, rotate, or revoke keys without restarting the server
python -m trellis_mcp --list-keys
python -m trellis_mcp --rotate-key team-alpha --expires-days 90
python -m trellis_mcp --revoke-key team-alpha

# Teammate zero-clone install against a remote HTTPS host (signed bundle)
python -m trellis_mcp --install-remote https://trellis.example.com --api-key "<member-api-key>" --bundle-signing-key "<bundle-signing-key>"
```

### Running Automated Tests & Building Single-File `.pyz`
```powershell
python -m unittest discover -s tests -v
python -m trellis_mcp --build-pyz dist/trellis-mcp.pyz
```
