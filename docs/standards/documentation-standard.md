# Software Engineering Documentation Standard (`[DRAFT]`)

**Status:** Working draft v0.1 `[DRAFT]`  
**Related:** [ADR 0001](../decisions/0001-single-source-of-truth.md), [Definition of Done](./definition-of-done.md), [Security Baseline](./security-baseline.md), [Data Classification](./data-classification.md), [Git Convention](./git-convention.md)

> This standard establishes how engineering projects structured with Trellis document architecture, specifications, contracts, code, operations, and AI-agent context under Git Docs-as-Code.

---

## 1. The 5 Golden Rules (`[REQ-DOC-01]`)

1. **Separate Diátaxis Quadrants & Keep Landing Pages Thin:** Never mix **Tutorials** (learning), **How-to Guides** (tasks), **Reference** (dry specs/APIs), and **Explanation** (architecture/rationale) on the same page. Landing pages (`README.md`, `docs/index.md`) route via links and never duplicate policy prose.
2. **Link, Never Copy (SSoT) & Auto-Generate References:** Maintain one canonical source per policy (`docs/standards/`). Generate API, database, IaC, UI, and code reference docs directly from machine-readable schemas and docstrings.
3. **Capture Rationale at Decision Time:** Record `Non-Goals` and `Alternatives Considered` in Design Docs / Specs and immutable numbered ADRs (`docs/decisions/NNNN-<topic>.md`, MADR or Nygard format) for any architectural or costly-to-reverse choice.
4. **Separate Tactical Runbooks from Strategic Playbooks & Ticket Postmortem Updates:** Keep copy-paste 3:00 AM mitigation **Runbooks** distinct from Incident Commander **Playbooks**, and require blameless postmortems to ticket stale/missing runbook fixes before closure.
5. **Enforce Docs in CI & Tiered PR DoD:** Treat broken syntax, prose ambiguities, broken links/anchors, failing doctests, and leaked secrets/internal hostnames as merge-blocking CI failures; require Tier 1 single-reviewer approval for typo/editorial edits and Tier 2 human approval (resolved via `trellis_pipeline`, `git config user.name`, or named reviewer / maker-checker) for behavior, API, schema, security, or architecture doc changes.

---

## 2. Git Docs-as-Code Policy & Wiki Boundaries (`[REQ-DOC-02]`)

- **Authoritative Substrate:** Store all engineering specs, ADRs, architecture views, contracts, runbooks, and standards as plain text (Markdown, reST, OpenAPI/AsyncAPI YAML, DBML, Mermaid/D2) in Git alongside source code.
- **Stack Documentation Generators:**
  - **Unified API Portals:** **Redoc CE 3.0** or **Scalar** (OpenAPI 3.1/3.2, AsyncAPI 3.0, GraphQL SDL, MCP `x-mcp`).
  - **SSGs & Code References:** **Zensical** (or Material for MkDocs during its maintenance window through May 2027), **Docusaurus**, **VitePress**, or **Astro Starlight** for portals; **Sphinx** (Python/C++ via Breathe), **TypeDoc / Compodoc** (TS/Angular), **Javadoc** (Java, honoring the first-sentence `.` summary rule), **DocFX / XML docs** (C#), **Go doc comments**, **rustdoc**, and **Storybook** for UI catalogs.
  - **Diagrams-as-Code:** Prefer **Mermaid**, **D2**, or **Structurizr DSL** over unversioned binary images.
- **Non-Git Wiki Boundaries:** Tools like **Confluence**, **Notion**, or self-hosted **Wiki.js** (`v3.4.0` standalone only due to `AGPL-3.0`) may be used for early PM discovery, meeting notes, or read-only executive pointers—**never** as the source of truth for technical specs, API contracts, runbooks, or `Restricted` data. Never rely on GitHub Free private-repo Wikis/Pages (unavailable on Free private repos).

---

## 3. Canonical Repository Layout & Required Artifacts (`[REQ-DOC-03]`)

```text
project-root/
├── README.md                    # Human entry: purpose, setup, minimal runnable example, license
├── AGENTS.md                    # Coding-agent entry (or CLAUDE.md / GEMINI.md pointers)
├── CONTRIBUTING.md              # Local dev/test setup, branch/commit conventions, PR checklist
├── CHANGELOG.md                 # Keep a Changelog 1.1.0 ([Unreleased], SemVer, YYYY-MM-DD)
├── SECURITY.md                  # Vulnerability reporting & disclosure SLA
├── .env.example                 # Safe configuration placeholders only (zero real secrets/hosts)
├── docs/
│   ├── index.md                 # Thin Diátaxis navigation hub
│   ├── tutorials/               # Guided beginner labs
│   ├── how-to/                  # Goal-oriented recipes (deploy, rotate keys, migrate)
│   ├── explanation/             # C4 (Context/Container/Component) + arc42 + Design Docs + CON-OPS
│   ├── reference/               # OpenAPI 3.1/3.2 (RFC 9457 errors), AsyncAPI 3.0, DBML/SchemaSpy, terraform-docs, Model Cards
│   ├── specs/                   # Traceable [REQ-NNN-XX] specs (Class M / Class L)
│   ├── decisions/               # Immutable numbered ADRs (MADR / Nygard)
│   └── runbooks/                # Tactical alert runbooks + Incident Commander playbooks + blameless postmortems
```

---

## 4. Security, Privacy & Freshness Controls (`[REQ-DOC-04]`)

- **Zero Secrets & Internal Hostname Ban:** Never commit production credentials, tokens, Luhn PANs, customer PII, staging/production login URLs, or internal DB server hostnames in docs, templates, or examples ([security-baseline.md](./security-baseline.md), [git-convention.md](./git-convention.md), [data-classification.md](./data-classification.md)). Link out to access-controlled secret/CMDB portals instead.
- **Ownership & Freshness:** Map `docs/` paths in `CODEOWNERS` and embed review dates (e.g., `<!--* freshness: { owner: 'team-handle', reviewed: 'YYYY-MM-DD' } *-->` or `Last Reviewed:` metadata) for runbooks and standards (review SLA: 90–180 days).
- **Agentic Discovery:** Keep root context files concise (`CLAUDE.md < 200` lines, `GEMINI.md < 200` lines, modular rules `< 60` lines, skills `< 80` lines). Public doc portals should publish `/llms.txt` (v2 link relations: `rel="alternate" type="text/markdown"`, `rel="describedby"`).

---

## 5. CI Quality Gates & Tiered Review (`[REQ-DOC-05]`)

Every PR touching documentation or public interfaces must pass automated CI checks:
1. **Format & Prose:** `markdownlint` (structure) + `Vale` (active voice, terminology, sentence case, banned ambiguities).
2. **Links & Anchors:** `lychee` or `markdown-link-check` (relative files, local `#heading` anchors, external URLs).
3. **Contracts & Runnable Examples:** OpenAPI/AsyncAPI linting (`redocly lint` / Spectral), `terraform-docs` freshness, and runnable doctests (`pytest --doctest-modules`, `cargo test --doc`, etc.).
4. **Secret & DoD Checks:** `trellis_scan` / `gitleaks` + Story DoD confirmation that behavior/API/schema changes include updated docs or ADRs.
5. **Approval Tiering:** Tier 1 typo/clarification PRs require 1 reviewer; Tier 2/banking PRs (API, schema, auth, security, SLA, compliance docs) require explicit human (resolved reviewer / maker-checker) sign-off.

---

## 6. Enterprise Banking & Compliance Mapping Appendix (`[REQ-DOC-06]`)

For **Class L** systems, core banking/payment platforms, or formal regulatory audits:
- **Requirements (ISO/IEC/IEEE 29148:2018 Clause 9.6):** Map Class L SRS sections across `9.6.1`–`9.6.20` (overview, scope, product perspective `.1`–`.8`, functions, user characteristics, limitations, assumptions, apportioning, external interfaces, functional/usability/performance/DB/design/compliance/quality attributes, `9.6.19` Verification methods, `9.6.20` Supporting info). Every requirement must be singular, measurable, and linked to `[REQ-NNN-XX]` tests.
- **Architecture & SDD (ISO/IEC/IEEE 42010:2022 & IEEE Std 1016-2009):** Express architectures via Stakeholders → Concerns → Viewpoints → Views (EoI, ADF, Aspects). Map SDD artifacts to applicable **IEEE 1016-2009 viewpoints** (*Context, Composition, Logical, Dependency, Information, Patterns Use, Interface, Structure, Interaction, State Dynamics, Algorithm, Resource*), alongside **arc42** (12 sections) and **C4** (Context, Container, Component, Code).
- **Change & Audit Control:** Record release changes in **Keep a Changelog 1.1.0** format (`Added / Changed / Deprecated / Removed / Fixed / Security`) and include **CON-OPS / Theory of Operation** ahead of generated API reference dumps.
