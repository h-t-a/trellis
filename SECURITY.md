# Security Policy

## Reporting a Vulnerability

Do **not** open a public issue for security problems.

Report privately to the repository maintainers with:

- Affected component and version.
- Reproduction steps or proof of concept.
- Impact assessment (data exposure, privilege escalation, denial of service).
- Suggested remediation, if known.

Maintainers will acknowledge the report, investigate, and coordinate a fix and disclosure timeline.

## Supported Versions

| Version | Supported |
| --- | --- |
| `0.1.x` | Yes |

## Security Baseline

All contributors must follow [docs/standards/security-baseline.md](./docs/standards/security-baseline.md) and the [AI Boundary Standard](./docs/standards/ai-boundary.md).

Key expectations:

- Never commit secrets, tokens, production data, or `.trellis_keys.json`.
- Use the lowest-privilege API key role and rotate keys regularly.
- Keep TLS enabled for any non-loopback `trellis-mcp` HTTP deployment.
- Run `trellis_scan` and `trellis_review` before release.
- Treat production deployments, ledger/financial sign-off, and real customer data as human-only (Tier 3).
