---
trigger: always_on
description: Documentation SSoT, Diátaxis separation, security hygiene, and CI/DoD doc gates
---

# Antigravity Rule: Documentation Standards

**Canonical Source of Truth:**
- [Documentation Standard](../../docs/standards/documentation-standard.md)
- [ADR 0001: Single Source of Truth](../../docs/decisions/0001-single-source-of-truth.md)
- [Definition of Done](../../docs/standards/definition-of-done.md)

## Summary Checklist (The 5 Golden Rules)

1. **Diátaxis & Thin Landing Pages:** Never mix Tutorials, How-Tos, Reference, and Explanation on one page; keep `README.md` and `docs/index.md` concise and link-driven.
2. **Link, Never Copy (SSoT):** Author policies once in `docs/standards/` and generate API/DB/IaC/code references from contracts (`OpenAPI`, `AsyncAPI`, `DBML`, `terraform-docs`, docstrings).
3. **Record Rationale:** Capture `Non-Goals`, `Alternatives Considered`, and numbered ADRs (`docs/decisions/`) when behavior, architecture, or schemas change.
4. **Ops & Security Safety:** Keep tactical 3:00 AM **Runbooks** separate from **Playbooks**; never commit credentials, PANs, PII, internal hostnames, or staging/prod login URLs in docs.
5. **CI & Story DoD Gates:** Validate Markdown, prose (`Vale`), links/anchors (`lychee`), contracts, doctests, and secrets on every PR; update docs/ADRs before merge.
