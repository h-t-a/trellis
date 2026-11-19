---
trigger: always_on
description: Core Trellis engineering standards, single source of truth, and review gates
---

# Antigravity Workspace Rules - `ai-dev-playbook` (Trellis)

## 1. Canonical Source of Truth (`docs/standards/`)

Do not duplicate engineering policies into tool-specific files (see [ADR 0001](../../docs/decisions/0001-single-source-of-truth.md)). Always follow the canonical standards in `docs/standards/` (also accessible via `@trellis-mcp` / `trellis_get_standard`):

- **Testing Standard:** [docs/standards/testing-standard.md](../../docs/standards/testing-standard.md)
- **Performance Testing & SLA Standard:** [docs/standards/performance-sla.md](../../docs/standards/performance-sla.md)
- **Definition of Done:** [docs/standards/definition-of-done.md](../../docs/standards/definition-of-done.md)
- **AI Boundary Standard (Tiers 1–3):** [docs/standards/ai-boundary.md](../../docs/standards/ai-boundary.md)
- **Security Baseline:** [docs/standards/security-baseline.md](../../docs/standards/security-baseline.md)
- **Git & Commit Convention:** [docs/standards/git-convention.md](../../docs/standards/git-convention.md)
- **Fast Root-Cause Analysis (RCA):** [docs/standards/rca-playbook.md](../../docs/standards/rca-playbook.md)
- **Quota & Token Cost Efficiency:** [docs/standards/quota-efficiency.md](../../docs/standards/quota-efficiency.md)
- **Complexity & Performance:** [docs/standards/complexity-and-performance.md](../../docs/standards/complexity-and-performance.md)
- **Data Classification:** [docs/standards/data-classification.md](../../docs/standards/data-classification.md)
- **Documentation Standard:** [docs/standards/documentation-standard.md](../../docs/standards/documentation-standard.md)

## 2. Core Operating Rules

1. **Plan Before Significant Code:** Produce an Implementation Plan artifact ([templates/implementation-plan.md](../../templates/implementation-plan.md)) and obtain human approval (resolved via `trellis_pipeline`, `git config user.name`, or named reviewer) before writing Tier 2 or feature code.
2. **Test Integrity:** Follow [testing-standard.md](../../docs/standards/testing-standard.md). Write failing tests first, state the `[REQ-NNN-XX]` verified, and **never** delete, skip, or weaken existing tests to make a build pass (Tier 3 prohibition).
3. **Zero Secrets & Tier 3 Exclusion:** Never place secrets, tokens, or real customer/production PII/PAN data in prompts, rules, skills, or MCP configurations ([security-baseline.md](../../docs/standards/security-baseline.md)).
4. **Git & Commit Discipline:** Follow [git-convention.md](../../docs/standards/git-convention.md) and [.agents/rules/git-convention.md](./git-convention.md).
5. **Walkthrough & AI Disclosure:** After implementation, produce a Walkthrough artifact ([templates/walkthrough.md](../../templates/walkthrough.md)) stating what changed and where AI was used.
