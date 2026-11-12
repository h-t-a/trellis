---
name: pb-mcp-audit
description: Audit .mcp.json servers against approved-mcp-servers.json, verify SHA-256/HMAC standard provenance, and inspect Trellis usage/budget telemetry. Invoke as /pb-mcp-audit.
---

# Skill: `/pb-mcp-audit` — MCP Allowlist, Provenance & Quota Audit

**Canonical Standards:**
- [docs/standards/approved-mcp-servers.json](../../docs/standards/approved-mcp-servers.json)
- [docs/standards/ai-bom.json](../../docs/standards/ai-bom.json)
- [docs/standards/security-baseline.md](../../docs/standards/security-baseline.md)
- [docs/standards/quota-efficiency.md](../../docs/standards/quota-efficiency.md)

## Execution Steps

1. **Verify MCP Server Allowlist & Transport (`trellis_mcp_registry`):**
   - Audit `.mcp.json` / `.agents/mcp_config.json` to ensure only approved servers, least-privilege read-only DB settings (`DB_READONLY=true`), and safe transports (no raw shell wrappers or unencrypted HTTP to remote hosts) are configured.
2. **Verify Standard Integrity (`trellis_verify` & `trellis_doctor`):**
   - Run `trellis_verify` to detect any tampering against SHA-256/HMAC provenance hashes and `trellis_doctor` to verify rule/skill sync parity and link integrity.
3. **Check Cost & AI-BOM Governance (`trellis_analytics`):**
   - Review token usage, per-key budgets, and model license alignment in [docs/standards/ai-bom.json](../../docs/standards/ai-bom.json).
