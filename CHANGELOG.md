# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `trellis_test` MCP tool for REQ-linked failing test skeletons (Python, TypeScript, Java, C#).
- `trellis_scan` MCP tool for secret/PAN scanning with optional `pip-audit` integration.
- `trellis_classify` MCP tool implementing the Public/Internal/Confidential/Restricted AI prompt gate.
- `trellis_mcp_registry` MCP tool enforcing the approved MCP server allowlist.
- `docs/standards/approved-mcp-servers.json` and `docs/standards/data-classification.md` (draft).
- Workspace doctor checks for JSON validity, skill mirror parity, broken relative links, and `--dry-run` previews.
- `/readyz` readiness endpoint and admin-only `/metrics` endpoint with per-key usage counters.
- `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, and an MIT `LICENSE`.

### Fixed

- `.claude/commands/*.md` relative links now resolve after skill mirroring.
- `docs/deployment-guide.md` no longer links to an unbuilt `dist/` artifact.

## [0.1.0] - 2026-11-12

### Added

- Zero-dependency `trellis-mcp` MCP server, HTTP server, installer, and workspace doctor.
- Canonical standards in `docs/standards/` and shared skills in `.agents/skills/`.
- Bearer-token RBAC with hashed-at-rest keys, expiry, rotation, TLS, request limits, and signed deploys.
