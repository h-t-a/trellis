# Rule: Documentation Standards

**Canonical Sources:**
- [Documentation Standard](../../docs/standards/documentation-standard.md)
- [ADR 0001: Single Source of Truth](../../docs/decisions/0001-single-source-of-truth.md)
- [Definition of Done](../../docs/standards/definition-of-done.md)

## Summary Checklist

1. **Diátaxis & SSoT:** Keep Tutorials, How-Tos, Reference, and Explanation separate. Link to `docs/standards/` rather than duplicating prose across rules, READMEs, or comments.
2. **Contract-Driven Reference:** Generate API (`OpenAPI 3.1/3.2`, `AsyncAPI 3.0`), DB (`DBML`/`SchemaSpy`), IaC (`terraform-docs`), and code docs from source schemas/docstrings; capture *why* in ADRs (`docs/decisions/`).
3. **Operational Readiness:** Keep tactical Runbooks distinct from Incident Commander Playbooks, and require blameless postmortems to update stale/missing runbooks.
4. **Security & Privacy:** Never write tokens, Luhn PANs, PII, internal hostnames, or live/staging login links into repository docs or examples.
5. **PR & CI Gate:** Update docs/ADRs whenever behavior, APIs, or schemas change, and verify lint, link/anchor, doctest, and secret checks pass before merge.
