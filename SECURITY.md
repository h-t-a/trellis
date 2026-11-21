# Security Policy

## Reporting a Vulnerability

Do **not** open a public issue or pull request for security vulnerabilities.

Report privately via **GitHub Private Vulnerability Reporting**:

- https://github.com/h-t-a/trellis/security/advisories/new

Include in your report:

- Affected component and version (`python -m trellis_mcp --version`).
- Reproduction steps or minimal proof of concept.
- Impact assessment (data exposure, privilege escalation, supply-chain tampering, denial of service).
- Suggested remediation, if known.

Maintainers will acknowledge the report within 3 business days, investigate, and coordinate a fix and disclosure timeline.

## Supported Versions

| Version | Supported |
| --- | --- |
| `0.1.x` | Yes |

## Security Baseline

All contributors must follow [docs/standards/security-baseline.md](./docs/standards/security-baseline.md) and the [AI Boundary Standard](./docs/standards/ai-boundary.md).

Key expectations:

- Never commit secrets, tokens, production data, or `.trellis_keys.json`.
- Use the lowest-privilege API key role (`member` defaults to a read-only allowlist) and rotate keys regularly.
- Keep TLS enabled for any non-loopback `trellis-mcp` HTTP deployment (`--tls-cert` / `--tls-key` or TLS-terminating reverse proxy with `--public-url` and `--trust-proxy`).
- Keep `POST /admin/deploy` disabled unless explicitly needed with a separate `--deploy-signing-key`.
- Run `trellis_scan` and `trellis_review` before release.
- Treat production deployments, ledger/financial sign-off, and real customer data as human-only (Tier 3).
