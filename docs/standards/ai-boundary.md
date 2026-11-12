# AI Boundary Standard: What AI Should and Should Not Do `[DRAFT]`

**Status:** Working draft v0.1 `[DRAFT, decide with team]`  
**Source:** [trellis-project-export.md](../knowledge/trellis-project-export.md) (Section 6)  
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

## 2. Supporting Governance Items to Research `[TO RESEARCH]`

The following supporting policies must be researched and decided with the team before moving this standard from v0.1 `[DRAFT]` to v1.0:

- [ ] **Data Classification Levels (`TODO [TO RESEARCH]`):** Define formal classification tiers (e.g., Public, Internal, Confidential, Restricted/PII/Financial) and map which tiers may be exposed to AI tools. Draft: [data-classification.md](./data-classification.md); enforcement: `trellis_classify` (`[REQ-P2-03]`).
- [ ] **Allowed MCP Servers Per Project (`TODO [TO RESEARCH]`):** Define an approved registry of MCP servers, their required read-only/least-privilege scopes, and the review process before enabling a server in `.mcp.json`. Draft registry: [approved-mcp-servers.json](./approved-mcp-servers.json); enforcement: `trellis_mcp_registry` (`[REQ-P2-04]`).
- [ ] **Approval Authority for Exceptions (`TODO [TO RESEARCH]`):** Define who can grant temporary exceptions to Tier 2 or Tier 3 boundaries and how exceptions expire.
- [ ] **Audit Trail of AI Usage (`TODO [TO RESEARCH]`):** Define how AI-assisted plans, walkthroughs, and PR disclosures are archived for internal or regulatory audit.
