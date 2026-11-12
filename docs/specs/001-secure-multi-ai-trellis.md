# SPEC-001: Secure Enterprise Multi-AI Trellis Control Plane & Orchestration Upgrade

- **Status:** Approved & Implemented (`2026-11-13`)
- **Tier / Class:** Class L · Tier 2/3 Governance, MCP Security & Multi-AI Orchestration
- **Requirements Covered:** `[REQ-TRL-01]` .. `[REQ-TRL-14]`

---

## 1. Security & Transport Hardening (`[REQ-TRL-01]` .. `[REQ-TRL-07]`)
- `[REQ-TRL-01]` Local HTTP server binds `127.0.0.1` by default (`--host 0.0.0.0` explicit for LAN/VM). Requests to `/mcp` or `/admin/*` carrying a disallowed `Origin` header return `403 Forbidden`.
- `[REQ-TRL-02]` Redacted JSONL audit logging (`trellis_mcp/audit.py`, `.trellis-audit.jsonl`) records caller IP, key ID, role, method, path, status, latency, tool name, and SHA-256 request digest while redacting Bearer tokens and Luhn-valid PANs.
- `[REQ-TRL-03]` Repeated `401` authentication failures per client IP trigger temporary `429 Too Many Requests` lockout; API keys support per-key `scopes` restricting permitted MCP tools (`403 Forbidden` when out of scope).
- `[REQ-TRL-04]` JSON-RPC `initialize` negotiates `protocolVersion` against `SUPPORTED_PROTOCOL_VERSIONS` (`2025-06-18`, `2025-03-26`, `2024-11-05`) and `POST /mcp` validates `MCP-Protocol-Version` headers (`400 Bad Request` if unsupported).
- `[REQ-TRL-05]` `trellis_scan` / `trellis_rca` enforce Luhn-validated PAN detection plus JWT, Myanmar NRC, regional phone, and IBAN detectors; `wrap_untrusted_context()` escapes closing delimiter tags.
- `[REQ-TRL-06]` `TrellisKeyStore` caches key records keyed by `(st_mtime_ns, st_size)` and `/readyz` caches `bundle_sha256` with a short TTL invalidated on `/admin/deploy`.
- `[REQ-TRL-07]` `.claude/settings.json` expands deny rules (`.trellis_keys.json`, `~/.ssh/*`, `~/.aws/*`, exfiltration commands) and wires `validate-bash.sh`, `secret-scan.sh` (fixed pipe logic), and `run-tests.sh`. Governance standards include `docs/standards/ai-bom.json`.

## 2. Semantic Knowledge, Routing & Multi-AI Orchestration (`[REQ-TRL-08]` .. `[REQ-TRL-14]`)
- `[REQ-TRL-08]` `trellis_search_knowledge` provides zero-dependency TF-IDF + von Mises-Fisher (`vMF`) hyperspherical search with pluggable `embedder` / Ollama adapter, `(cosine, kappa)` confidence scoring, access-level filtering, and token-budget compression.
- `[REQ-TRL-09]` Hybrid ingestion anomaly gate (`check_ingestion_anomaly`) flags low-similarity / off-cluster documents prior to indexing; `check_agent_drift` detects out-of-scope behavioral drift.
- `[REQ-TRL-10]` `trellis_rca` surfaces `find_similar_rcas()` matches (`## 5. Similar Prior RCAs`) to prevent duplicate root-cause investigations.
- `[REQ-TRL-11]` `trellis_route_model` selects cost/capability-optimal models (`select_route`) while enforcing Restricted/PII local-only execution guarantees (`qwen2.5-coder`), plus LiteLLM configuration generation.
- `[REQ-TRL-12]` `trellis_pipeline` tracks structured `pb-pipeline` stage state, detects fix loops (`fix_loops >= 3`), enforces Tier 2 approval gates and cross-model reviewer separation, and `GET /.well-known/agent.json` serves the A2A agent card.
- `[REQ-TRL-13]` `trellis_synthesize` presents structured agreement/divergence matrices across multiple AI model reviews instead of silent voting.
- `[REQ-TRL-14]` `canary_evaluate()` measures recall/precision retention before promoting new knowledge documents into shared enterprise retrieval.
