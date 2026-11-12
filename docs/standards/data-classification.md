# Data Classification Standard `[DRAFT]`

**Status:** Working draft v0.1 `[DRAFT, decide with team]`  
**Related:** [AI Boundary](./ai-boundary.md), [Security Baseline](./security-baseline.md), [Approved MCP Servers](./approved-mcp-servers.json)

> This draft defines classification levels and AI exposure rules. A human owner must approve it before it becomes v1.0. The `trellis_classify` tool implements this gate; it does not replace legal/compliance sign-off.

## 1. Classification Levels

| Level | Description | Examples | AI Prompt | Logs / Commits |
| --- | --- | --- | --- | --- |
| **Public** | Safe for public disclosure. | Marketing copy, open-source docs | Allowed | Allowed |
| **Internal** | Non-public but low sensitivity. | Architecture notes, internal standards | Allowed | Allowed |
| **Confidential** | Business-sensitive or personal data. | Customer names, emails, balances, IBANs | Redact first | Redact first |
| **Restricted** | Regulated secrets or high-blast-radius data. | Passwords, API keys, PANs, private keys, JWT tokens | **Blocked** | **Blocked** |

## 2. Rules

1. **Default deny:** If content cannot be confidently classified, treat it as **Confidential**.
2. **Restricted is Tier 3:** Never send Restricted data to an AI prompt, external tool, log sink, or commit.
3. **Redaction before prompting:** Replace Confidential identifiers with stable placeholders (for example `<USER_1>`, `<EMAIL_REDACTED>`) and keep the mapping outside the AI context.
4. **Synthetic data for tests:** Use generated or anonymized fixtures, never production customer data.
5. **Deterministic gate:** Run `trellis_classify` before pasting logs or records into a prompt when the classification is uncertain.

## 3. Automated Checks

- `trellis_classify` — classifies content and blocks Restricted → prompt; flags Confidential.
- `trellis_scan` — detects secret/PAN patterns in the workspace.
- `trellis_review` — blocks secrets/PANs in diffs and commit messages.

## 4. Approval Checklist

- [ ] Data owners confirm the level definitions and examples.
- [ ] Legal/compliance confirms retention, residency, and regulatory mapping.
- [ ] Security confirms redaction and telemetry controls.
- [ ] Remove the `[DRAFT]` marker only after all boxes are checked.
