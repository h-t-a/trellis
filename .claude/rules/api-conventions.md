# Rule: API & Schema Conventions

**Canonical Sources:**
- [AI Boundary Standard](../../docs/standards/ai-boundary.md)
- [Definition of Done](../../docs/standards/definition-of-done.md)
- [Testing Standard](../../docs/standards/testing-standard.md)

## Summary Checklist (`[DRAFT]`)

1. **Tier 2 Human Approval Required:**
   - All API contract changes, database schema changes, migration scripts, and input-validation/authentication/authorization logic are **Tier 2** items in [ai-boundary.md](../../docs/standards/ai-boundary.md).
   - AI may draft them inside an Implementation Plan, but **explicit human approval is mandatory** before implementation and before release.
2. **Contract & Integration Testing (`TODO [TO RESEARCH]`):**
   - API changes must be accompanied by contract/integration tests as defined in [testing-standard.md](../../docs/standards/testing-standard.md) (`TODO [TO RESEARCH]: finalize API contract testing framework and merge-blocking gates`).
3. **Migration Safety & Rollback (`[DRAFT]`):**
   - Every database schema or migration change requires human review and a documented rollback plan before release (see Release-level checklist in [definition-of-done.md](../../docs/standards/definition-of-done.md)).
4. **Documentation Update (`[DRAFT]`):**
   - Any change to an API contract or data model must update the corresponding API documentation or ADR in `docs/decisions/`.
5. **Open Conventions (`TODO [TO RESEARCH]`):**
   - `TODO [TO RESEARCH]`: Define team-wide REST/gRPC versioning, error-payload schema, idempotency key rules for financial transfers, and pagination standards.
