# SPEC-002: Trellis Security Hardening, Supply-Chain Defense & CI Automation

- **Status:** Approved & Implemented (`2026-11-21`)
- **Tier / Class:** Class L · Tier 2/3 Supply Chain, Remote Transport & CI Automation
- **Requirements Covered:** `[REQ-TRL-17]` .. `[REQ-TRL-30]`
- **Threat Model Reference:** [docs/standards/threat-model.md](../standards/threat-model.md)

---

## 1. Remote Write Protection & Path Traversal (`[REQ-TRL-17]` .. `[REQ-TRL-19]`)
- `[REQ-TRL-17]` Remote HTTP calls strictly reject write parameters (`save_to_file`, `auto_fix`); all underscore-prefixed request arguments (e.g. `_remote_mode`, `_auth_label`) are stripped from incoming JSON-RPC calls before server context injection (`F1`).
- `[REQ-TRL-18]` Default member keys receive a strict read-only tool allowlist (`DEFAULT_MEMBER_SCOPES`), preventing execution of administrative or file-writing tools (`F1`).
- `[REQ-TRL-19]` Workspace path containment helper `_is_within_root()` resolves real paths, preventing sibling directory escapes (`../trellis-evil/`) and symlink directory escapes across all tools (`F2`).

## 2. Deploy, TLS & Installer Hardening (`[REQ-TRL-20]` .. `[REQ-TRL-23]`)
- `[REQ-TRL-20]` `/admin/deploy` is disabled by default (`enable_remote_deploy=False`), requires a distinct `deploy_signing_key` separate from bearer tokens, validates version monotonicity, and performs atomic swap with rollback backup (`F3`).
- `[REQ-TRL-21]` Non-loopback binds (`0.0.0.0`) refuse to start without TLS certificates unless `--insecure-http` is passed; Host header allowlist stops DNS rebinding; `--public-url` controls installer endpoints (`F4`, `F7`).
- `[REQ-TRL-22]` Remote installer validates skill names with `^[a-z0-9][a-z0-9-]{0,62}$`, requires signed bundles by default, backs up malformed existing MCP configs, and references `${TRELLIS_API_KEY}` rather than storing plaintext tokens (`F4`, `F6`).
- `[REQ-TRL-23]` `X-Forwarded-For` is only honored from trusted reverse proxies; rate-limiting and lockout state tables evict stale IPs via rolling TTL; legacy plaintext tokens cannot authenticate without migration (`F8`, `F9`).

## 3. OSS Scrubbing, VM Scripts & Hygiene (`[REQ-TRL-24]` .. `[REQ-TRL-25]`)
- `[REQ-TRL-24]` VM setup scripts remove SYSTEM scheduled task execution, WinRM `Any` IP listeners, automatic process killing on port 8080, and hardcoded local directories (`F5`).
- `[REQ-TRL-25]` Scrubbed all tracked files of personal local workstation directories, private VPN IP addresses, and internal project names; added `SECURITY.md` with GitHub Private Vulnerability Reporting (`F13`, `F17`).

## 4. CI Workflow & Claude Hooks (`[REQ-TRL-26]` .. `[REQ-TRL-27]`)
- `[REQ-TRL-26]` Claude Code hooks run real requirement-linked test discovery, catch destructive variations (`rm -rf ~`, `rm -rf .`, `git push -f`), and state defense-in-depth posture (`F12`).
- `[REQ-TRL-27]` GitHub Actions CI pipeline runs across Python 3.9 through 3.13 on `ubuntu-24.04` and `windows-latest`, enforcing doctor checks, test discovery, skill parity, secret scanning, and .pyz build verification (`F11`).

## 5. Data-Driven AI-BOM, Retrieval Benchmark & Threat Model (`[REQ-TRL-28]` .. `[REQ-TRL-30]`)
- `[REQ-TRL-28]` `docs/standards/ai-bom.json` contains verified model catalog with `last_verified`, `deprecation`, and `aliases`; router loads catalog dynamically; `trellis_doctor` audits staleness (>90 days) and deprecation dates (`F10`).
- `[REQ-TRL-29]` Comparative benchmark suite (`tests/test_vmf_bm25_benchmark.py`) evaluates vMF vector retrieval against Okapi BM25 baseline across standards corpus; prompt injection regexes documented as best-effort heuristics (`F14`).
- `[REQ-TRL-30]` Canonical STRIDE threat model established in `docs/standards/threat-model.md` covering all assets, actors, and mitigations (`F17`).
