# AI Boundary Standard: What AI Should and Should Not Do `[DRAFT]`

**Status:** Working draft v0.1 `[DRAFT, decide with team]`  
**Source:** Canonical Trellis engineering standard (`docs/standards/`)  
**Domain Context:** Enterprise banking and government-style systems.

> [!IMPORTANT]
> **Enforcement Principle:** *A rule is a request; a hook is a guarantee.*  
> Any restriction in Tier 3 that must never happen should be enforced via permissions (`settings.json`, `/permissions`), gitignore rules, and lifecycle hooks-not only stated in prose.

---

## 1. Three-Tier Autonomy Model `[DRAFT]`

### Tier 1: AI May Act Autonomously `[DRAFT]`
Tasks with low blast radius where existing tests or human review at PR time provide sufficient control:
- Boilerplate code generation
- Code explanation and architecture walkthroughs
- Documentation drafts and README/comment updates
- Lint and formatting fixes
- Unit-test drafts (subject to human review of assertions per [testing-standard.md](./testing-standard.md))
- Refactors that are fully covered by existing passing tests

### Tier 2: AI Drafts, Human Must Approve `[DRAFT]`
Tasks that change system behavior, contracts, security posture, or infrastructure. AI may propose an Implementation Plan and draft changes, but **explicit human review and approval are mandatory**:
- Feature code and business logic
- API contract changes
- Database schema definitions and migration scripts
- Dependency upgrades
- CI/CD pipeline configuration changes
- Authentication, authorization, and input-validation code
- Test strategy changes

### Tier 3: Human-Only (AI Excluded or Strictly Read-Only) `[DRAFT]`
High-risk actions where AI agents must **never** execute changes or ingest sensitive data:
- **Production credentials and secrets** (never read, generate, or store real secrets in prompts, rules, or configs)
- **Real customer or production data** in prompts, context files, or MCP connections
- **Production deployments** and direct production data modifications
- **Sign-off on financial or ledger correctness** (e.g., balance updates, settlement logic, fee calculations)
- **Security exceptions and compliance decisions**
- **Removing, skipping, or weakening tests** to make a failing build turn green

---

## 2. Supporting Governance Controls & Evidence (`[REQ-TRL-07]`, `[REQ-TRL-11]`)

1. **Data Classification Levels:** Governed by [data-classification.md](./data-classification.md) (`Public`, `Internal`, `Confidential`, `Restricted / PII / Financial`) and enforced by `trellis_classify` (`[REQ-P2-03]`) and `trellis_route_model` (`[REQ-TRL-11]`, forcing local-only execution on `Restricted` data).
2. **Approved MCP Servers & AI-BOM:** Registry defined in [approved-mcp-servers.json](./approved-mcp-servers.json) and [ai-bom.json](./ai-bom.json); enforced by `trellis_mcp_registry` (`[REQ-P2-04]`) and per-key `scopes` (`[REQ-TRL-03]`).
3. **Approval Authority for Exceptions:** Tier 2 / Tier 3 exceptions require explicit named human approval recorded in the pipeline state (`trellis_pipeline` approval gate, `[REQ-TRL-12]`) and PR walkthrough.
4. **Audit Trail of AI Usage:** All `/mcp` tool calls and HTTP admin events are recorded in `.trellis-audit.jsonl` via `TrellisAuditLogger` (`[REQ-TRL-02]`) with raw tokens/PANs redacted and payload hashes retained for compliance audit.
