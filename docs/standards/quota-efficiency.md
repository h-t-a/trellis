# AI Quota, Token Cost & Prompt-Cache Standard (`quota-efficiency`)

**Status:** Working draft v0.1 `[DRAFT]`  
**Owner:** HTA  
**Sources:** [trellis-project-research-addendum-01_2026-10-16.md](../knowledge/trellis-project-research-addendum-01_2026-10-16.md) (§17), [evaluation-addendum-01.md](../knowledge/evaluation-addendum-01.md) (`F03`, `F06`, `F07`)

---

## 1. Core Principles

1. **Progressive Disclosure First:** Keep always-on rules (`GEMINI.md`, `CLAUDE.md`, `.agents/rules/*.md`, `.claude/rules/*.md`) brief and under budget (< 200 lines; < 24 KB per file). Place multi-step procedures in on-demand **Skills** (`SKILL.md`) or invoke them via **`trellis-mcp`** tools so only metadata loads upfront.
2. **Preserve Prompt Prefix Cache:** Within a single deliverable, keep the model, system prompt, and active MCP server list stable so turns reuse warm prompt caches. Use `/compact` when context grows past ~60% on the same task; start a fresh conversation (using `/pb-handoff` or `trellis_handoff`) when switching to an unrelated task or splitting a Class L epic.
3. **Never Hard-Code Provider Pricing or Caps:** Quota refresh windows (5-hour vs. weekly) and plan limits evolve. Check live numbers via `/usage` (`/cost` in Claude Code) and `/credits` (`agy` CLI), and default credit overage toggles to **Never** (`"useG1Credits": false`) on shared/budget-capped accounts.

---

## 2. Task Cost Classes & Mandatory AI Boundary Guard (`[REQ-QUOTA-01]`)

Classify every task before starting (or call `trellis_budget`):

| Class | Typical Scope | AI Boundary Restriction (`F03`) | Model & Effort | Review & Session Budget Rule |
| :---: | :--- | :--- | :--- | :--- |
| **S** | 1 file, clear cause, < 30 lines | **Tier 1 ONLY.** *Never* auth, input validation, DB schema/migrations, API contracts, CI/CD, security config, or financial/ledger logic. Any Tier 2/3 touch **auto-upgrades to Class M or L**. | Fast model (`Flash` / `Sonnet`), `low` effort | No separate Plan artifact required; write/run failing test once. |
| **M** | 2–5 files, single module, or any 1-file Tier 2 change | **Tier 1 or Tier 2** (human approval required on Implementation Plan before feature/Tier 2 edits). | Default model, `medium` effort | Inline 4-section Micro-Spec in Implementation Plan; keep in 1 warm session (use `/compact` if needed); batch test runs. |
| **L** | Cross-module, architectural choice, schema migration, or SLA perf work | **Tier 2** (human approval on standalone Spec + Plan; **Tier 3** items remain human-only). | Strong reasoning model (`Pro` / `Opus`), `high` effort | Standalone Spec (`docs/specs/NNN-<name>.md`) + approved Plan; split execution into Class M tasks via `/pb-handoff`. |

---

## 3. Nine Operational Quota Rules (`[REQ-QUOTA-02]`)

1. **One deliverable per conversation; warm cache within a deliverable:** Start fresh after a task closes; use `/compact` mid-task rather than cold-restarting when context is still relevant.
2. **Right-size model and effort upfront:** Use `trellis_budget` or the table above before your first prompt; avoid switching models mid-turn (which invalidates prompt cache).
3. **Target exact files with `@file`:** Start from stack traces, `git diff`, or failing test paths—never ask the agent to scan the whole repository.
4. **Evidence before exploration:** Collect terminal failure output, `git diff`, and sanitized logs first; read source files second.
5. **3-Retry Circuit Breaker:** After **3 consecutive failed hypotheses or test runs**, stop coding and re-plan (`/grill-me`) rather than looping.
6. **Keep rules short; put runbooks in Skills and `trellis-mcp`:** Audit instruction token weight periodically with `/context`, `/skill-doctor`, or `trellis_doctor`.
7. **Default credit overage to `Never`:** Enable overage credits only for explicit release deadlines approved by the team lead.
8. **Exclude indexing noise:** Keep `node_modules/`, build outputs, coverage reports, and lockfiles excluded via `.gitignore` and workspace permission deny rules.
9. **Batch verification runs:** Run the test/lint suite once per coherent change set rather than after every single-line edit.
