---
name: pb-data-classification
description: Use when classifying data into Public/Internal/Restricted tiers and scanning PII. Not for threat modeling or network audits.
metadata: {pack: core, tier: 1, quota_class: S, standards: [data-classification, security-baseline, ai-boundary]}
---

# Skill: `/pb-data-classification` — Data Tier & Secret/PII Guard

**Canonical Standards:**
- [docs/standards/data-classification.md](../../../docs/standards/data-classification.md)
- [docs/standards/security-baseline.md](../../../docs/standards/security-baseline.md)
- [docs/standards/ai-boundary.md](../../../docs/standards/ai-boundary.md)

## Execution Steps

1. **Classify Sensitivity (`trellis_classify`):**
   - Pass the target text/snippet summary to `trellis_classify` to assign `Public`, `Internal`, `Confidential`, or `Restricted`.
2. **Scan Without Echoing Secrets (`trellis_scan`):**
   - Run `trellis_scan` to detect Luhn-valid 13–19 digit PANs, JWTs, API keys/secrets, Myanmar NRC identifiers, regional phone numbers, and IBANs.
   - Never print raw secret values or PANs in chat, diffs, or logs.
3. **Enforce Model Residency Escalation:**
   - If classification is `Confidential` or `Restricted`, block external cloud models and invoke `/pb-route` to restrict execution to on-prem models, or ask the user to redact with synthetic placeholders (`<PAN_REDACTED>`, `<USER_1>`).
