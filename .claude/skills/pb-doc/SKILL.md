---
name: pb-doc
description: Audit, scaffold, and validate project documentation across Diátaxis, ADRs, C4/arc42, API/DB/IaC contracts, SRE runbooks, AGENTS.md, and CI gates. Invoke as /pb-doc.
---

# Skill: `/pb-doc` — Project Documentation Audit & Scaffolding

**Canonical Standards:**
- [docs/standards/documentation-standard.md](../../../docs/standards/documentation-standard.md)
- [docs/standards/definition-of-done.md](../../../docs/standards/definition-of-done.md)
- [docs/standards/security-baseline.md](../../../docs/standards/security-baseline.md)
- [docs/decisions/0001-single-source-of-truth.md](../../../docs/decisions/0001-single-source-of-truth.md)

## Execution Steps

1. **Detect Mode & Scope (`audit` | `scaffold` | `gate`):**
   - Identify stack (Python, TS/Angular, Java, C#, Terraform, DB) and classification tier via `trellis_classify` / `trellis_budget`.
   - For **Class L** or banking compliance scopes, include the ISO/IEC/IEEE 29148:2018 (`9.6.1–9.6.20`) and IEEE 1016-2009 viewpoint mappings.
2. **Audit / Scaffold Layered Artifacts (Diátaxis + SSoT):**
   - Verify root files (`README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `CHANGELOG.md` Keep a Changelog 1.1.0, `SECURITY.md`, `.env.example`).
   - Separate `docs/tutorials/`, `docs/how-to/`, `docs/explanation/` (C4/arc42/Design Docs/CON-OPS), `docs/reference/` (OpenAPI/AsyncAPI/DBML/terraform-docs), `docs/specs/`, `docs/decisions/` (ADRs), and `docs/runbooks/` (Runbooks vs. Playbooks + postmortems).
3. **Enforce Security, Anti-Drift & CI Hygiene:**
   - Run `trellis_scan` and `trellis_doctor` (`python -m trellis_mcp --check`) to catch leaked tokens, PANs, internal hostnames, broken relative links/anchors, and rule/skill budget bloat.
   - Verify or scaffold CI checks (`markdownlint`, `Vale`, `lychee`, contract lint, doctests, secret scan) and PR DoD checkboxes ([templates/pull_request_template.md](../../../templates/pull_request_template.md)).
4. **Tiered Sign-Off:**
   - Present any new Class M/L spec, ADR, API/schema doc, or CI workflow for human approval (resolved via `trellis_pipeline`, `git config user.name`, or named reviewer) before merge; never commit unredacted environment URLs or credentials.
