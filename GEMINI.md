# GEMINI.md - Antigravity Project Context `[VERIFY file name per Antigravity version]`

> **Verification Note `[VERIFY]`:** Confirm whether your installed Antigravity IDE version loads root `GEMINI.md`, `AGENTS.md`, or `.agents/rules/standards.md` as the primary workspace context file.

## 1. Single Source of Truth

This repository follows the **`ai-dev-playbook` (Trellis) v0.1 + SPEC-001** standard. All authoritative engineering policies live in `docs/standards/` (see [ADR 0001](./docs/decisions/0001-single-source-of-truth.md)):

- [Testing Standard](./docs/standards/testing-standard.md)
- [Performance Testing & SLA Standard](./docs/standards/performance-sla.md)
- [Complexity & Performance Analysis Standard](./docs/standards/complexity-and-performance.md)
- [Root Cause Analysis (RCA) Playbook](./docs/standards/rca-playbook.md)
- [Quota & Token Efficiency Standard](./docs/standards/quota-efficiency.md)
- [Definition of Done](./docs/standards/definition-of-done.md)
- [AI Boundary Standard (Tiers 1–3)](./docs/standards/ai-boundary.md)
- [Security Baseline](./docs/standards/security-baseline.md)
- [Git & Commit Convention](./docs/standards/git-convention.md)
- [Data Classification Standard](./docs/standards/data-classification.md)
- [Approved Multi-AI Catalog (`ai-bom.json`)](./docs/standards/ai-bom.json)
- [SPEC-001: Secure Multi-AI Trellis Upgrade](./docs/specs/001-secure-multi-ai-trellis.md)
- [Developer Onboarding Guide](./docs/onboarding.md)

## 2. Antigravity Workflow, Skills & MCP Tools

1. **Plan & Spec First:** Before writing Class M or Class L / Tier 2 code, create a Spec ([templates/spec-template.md](./templates/spec-template.md)) or **Implementation Plan artifact** ([templates/implementation-plan.md](./templates/implementation-plan.md)) and wait for human approval (`trellis_pipeline` Tier 2 gate).
2. **Test Discipline:** Follow [testing-standard.md](./docs/standards/testing-standard.md). Never delete, skip, or weaken existing tests to make a build pass.
3. **Security, Data Tiers & Model Routing:** Never include secrets, Luhn PANs, JWTs, Myanmar NRCs, or real customer data in prompts or logs. Route `Restricted`/`Confidential` workloads exclusively to on-prem models via `trellis_route_model` ([ai-bom.json](./docs/standards/ai-bom.json), [ai-boundary.md](./docs/standards/ai-boundary.md)).
4. **Git & Commit Discipline:** Follow [git-convention.md](./docs/standards/git-convention.md) and `/git-convention` (`<type>(<scope>): <imperative summary>`, max 72 chars, lowercase subject, no trailing period, semantic branches `<type>/<name>`).
5. **Walkthrough Gate:** After implementation, produce a **Walkthrough artifact** following [templates/walkthrough.md](./templates/walkthrough.md) stating what changed, verification results, and where AI was used.
6. **Customizations & `trellis-mcp` Server:**
   - **Rules (`.agents/rules/*.md`):** `standards.md`, `git-convention.md`, and `quota-efficiency.md` (with `trigger: always_on` YAML frontmatter).
   - **Skills / Slash Commands (`.agents/skills/*/SKILL.md` — 18 skills):** `/pb-plan`, `/pb-spec`, `/pb-pipeline`, `/pb-rca`, `/pb-enhance`, `/pb-handoff`, `/pb-review`, `/pb-release-check`, `/pb-route`, `/pb-synthesize`, `/pb-knowledge`, `/git-convention`, `/data-classification`, `/mcp-registry-audit`, `/test-writer`, `/security-audit`, `/code-review`, and `/perf-test`.
   - **MCP Server (`trellis-mcp` — 18 tools):** `trellis_get_standard`, `trellis_rca`, `trellis_spec`, `trellis_enhance`, `trellis_budget`, `trellis_handoff`, `trellis_review`, `trellis_doctor`, `trellis_test`, `trellis_scan`, `trellis_classify`, `trellis_mcp_registry`, `trellis_verify`, `trellis_analytics`, `trellis_search_knowledge`, `trellis_route_model`, `trellis_pipeline`, and `trellis_synthesize` (`python -m trellis_mcp --install-global`).
