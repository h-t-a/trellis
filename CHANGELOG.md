# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Documentation Standard, Thin Rules & `/pb-doc` Skill (`[REQ-DOC-01..06]`):**
  - Added canonical `docs/standards/documentation-standard.md` covering Diátaxis separation, Git Docs-as-Code & wiki boundaries, C4/arc42/ADRs, API/DB/IaC/UI/code/ML contracts, SRE runbooks vs. playbooks, CI quality gates, `AGENTS.md` / `/llms.txt` v2, and an ISO/IEC/IEEE 29148:2018 & IEEE 1016-2009 compliance appendix.
  - Added always-on workspace rule `.agents/rules/documentation.md`, modular rule `.claude/rules/documentation.md`, and the 18th unified skill `/pb-doc` (`.agents/skills/pb-doc/SKILL.md`, synced via `--sync-workspace` and exposed via MCP `prompts/*`).
  - Registered `documentation-standard` and `data-classification` in `docs/standards/standards.json` and `STANDARD_FILE_MAP`.
- **SPEC-001 Security, Audit & Protocol Hardening (`[REQ-TRL-01..07]`):**
  - Loopback bind default (`127.0.0.1`), `Origin` allowlist checks (`403`) on `/mcp` and `/admin/*`, and `--allowed-origin` CLI flag.
  - Redacted JSONL audit logging (`trellis_mcp/audit.py`, `--audit-log`) stripping Bearer tokens and Luhn PANs.
  - Repeated `401` per-IP lockout (`429`) and per-key tool `scopes` enforcement (`--scopes`, `POST /admin/keys`).
  - MCP `protocolVersion` negotiation (`2025-06-18`, `2025-03-26`, `2024-11-05`) and `MCP-Protocol-Version` header validation (`400`).
  - Luhn-validated PAN checks, JWT, Myanmar NRC, phone, and IBAN redaction detectors plus `wrap_untrusted_context` delimiter escaping.
  - `TrellisKeyStore` `(st_mtime_ns, st_size)` cache and `/readyz` bundle digest TTL cache.
  - Hardened `.claude/settings.json` deny list & wired `PreToolUse` / `Stop` hooks.
- **Multi-AI Orchestration, vMF Knowledge & Expanded Skills (`[REQ-TRL-08..15]`):**
  - `trellis_search_knowledge` (zero-dep TF-IDF + von Mises-Fisher clustering, `(cosine, kappa)` confidence, access filter, anomaly gate, behavioral drift, Canary sandbox, and RCA deduplication).
  - `trellis_route_model` + LiteLLM config generator + `docs/standards/ai-bom.json` covering legally licensed commercial APIs (`perplexity/sonar*`, `xai/grok-*`, `gemini/*`, `anthropic/claude-*`, `openai/gpt-5*`, `mistral/*`) and commercial open-weight on-prem models (`Apache-2.0`, `Llama 3.3 Community License`).
  - `trellis_pipeline`, `trellis_synthesize`, and unauthenticated A2A agent card (`GET /.well-known/agent.json`).
  - Unified all workflow skills cleanly under `/pb-*` (17 non-overlapping skills: `/pb-plan`, `/pb-spec`, `/pb-pipeline`, `/pb-rca`, `/pb-enhance`, `/pb-handoff`, `/pb-review` merging `code-review`, `/pb-release-check`, `/pb-route`, `/pb-synthesize`, `/pb-knowledge`, `/pb-git-convention`, `/pb-data-classification`, `/pb-mcp-audit`, `/pb-security-audit`, `/pb-test-writer`, `/pb-perf-test`), dynamically exposed via MCP `prompts/list` + `prompts/get`, with stale mirror pruning in `sync_workspace` and tests in `tests/test_spec_001_upgrades.py`.
- **Documentation Sync:** Updated `README.md`, `CONTRIBUTING.md`, `docs/how-to-use.md`, `docs/deployment-guide.md`, `docs/onboarding.md`, `scripts/sync-tool-configs.md`, and `.env.example` to match `ui.py`/`branding.py` Admin Dashboard UI, practical tool usage workflows, HTTP endpoints, env vars, `--rotate-key`/`--emit-config` CLI flags, and the full 42-test suite (`unittest discover -s tests`).
- `trellis_test` MCP tool for REQ-linked failing test skeletons (Python, TypeScript, Java, C#).
- `trellis_scan` MCP tool for secret/PAN scanning with optional `pip-audit` integration.
- `trellis_classify` MCP tool implementing the Public/Internal/Confidential/Restricted AI prompt gate.
- `trellis_mcp_registry` MCP tool enforcing the approved MCP server allowlist.
- `trellis_verify` MCP tool for SHA-256/HMAC provenance verification of retrieved standards.
- `trellis_analytics` MCP tool for token/cost/quota reporting from a local usage ledger.
- `--emit-config` bridge generating MCP config for VS Code, JetBrains, Cursor, Windsurf, and Claude.
- Versioned standards manifest (`docs/standards/standards.json`) with offline cache (`--sync-cache`).
- Admin key-management dashboard at `GET /admin/dashboard`.
- HttpOnly admin dashboard sessions: key exchange via `POST /admin/session`, 15-minute signed cookie, `SameSite=Strict`, CSRF header enforcement, server-side sign-out, and nonce-based CSP. The raw admin key is no longer stored in browser storage.
- `docs/standards/approved-mcp-servers.json` and `docs/standards/data-classification.md` (draft).
- Workspace doctor checks for JSON validity, skill mirror parity, broken relative links, and `--dry-run` previews.
- `/readyz` readiness endpoint and admin-only `/metrics` endpoint with per-key usage counters.
- `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, and an MIT `LICENSE`.

### Fixed

- Fixed silent `KeyError` in `tool_trellis_rca` (`similarity`/`summary` -> `cosine`/`excerpt`) so `## 5. Similar Prior RCAs` renders cleanly (`[REQ-TRL-10]`).
- Expanded `trellis_mcp/knowledge.py` corpus indexing to cover root docs (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`), `templates/*.md`, `docs/integrations/*.md`, and `docs/how-to-use.md` with `**Classification:**` metadata parsing.
- Aligned `tool_trellis_spec` Part A and Part B headings with `templates/spec-template.md`, extended `tool_trellis_doctor` to check `GEMINI.md` line budgets, root docs, and local `#heading` anchors, and fixed `README.md` section ordering (`3.2 -> 3.3 -> 3.4`).
- `.claude/commands/*.md` relative links now resolve after skill mirroring.
- `docs/deployment-guide.md` no longer links to an unbuilt `dist/` artifact.

## [0.1.0] - 2026-11-12

### Added

- Zero-dependency `trellis-mcp` MCP server, HTTP server, installer, and workspace doctor.
- Canonical standards in `docs/standards/` and shared skills in `.agents/skills/`.
- Bearer-token RBAC with hashed-at-rest keys, expiry, rotation, TLS, request limits, and signed deploys.
