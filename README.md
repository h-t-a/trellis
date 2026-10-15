# `ai-dev-playbook` (Trellis) - AI-Assisted Development Standard

**Version:** `v0.1` (`[DRAFT]` - Working Kickoff Starter Kit)  
**Primary Tools Supported:** **Claude Code** & **Antigravity IDE**  
**Canonical Source of Truth:** [`docs/standards/`](./docs/standards/)

---

## 1. Purpose

`ai-dev-playbook` (**Trellis**) is a version-controlled starter kit and template repository for AI-assisted software engineering:

1. **Consistency:** Every project and developer follows the same quality bar when working with AI assistants.
2. **Skill Growth:** AI use makes developers stronger (critical review of plans, failing tests first, turning mistakes into explicit rules), not weaker.
3. **Cross-Team Collaboration:** Teams share one canonical set of standards (`docs/standards/`) with thin tool-specific pointers for both Claude Code and Antigravity IDE.
4. **Structured Planning:** Every significant change follows the same lifecycle: **`Plan -> Implement -> Verify -> Review`**.

---

## 2. Who This Is For

- Engineering teams building **enterprise banking, financial, and government-style systems** where security, auditability, and testing discipline are first-class requirements.
- Developers using **Claude Code** (`CLAUDE.md`, `.claude/`) and/or **Antigravity IDE** (`GEMINI.md`, `.agents/`).
- Tech leads, QA engineers, and security reviewers defining repeatable review gates and SLA criteria.

---

## 3. Repository Folder Map

```text
trellis/
├── README.md                        # Project overview, adoption guide, and status
├── CLAUDE.md                        # < 200 lines; imports standards via @docs/standards/...
├── GEMINI.md                        # Short Antigravity context file [VERIFY file name]
├── .mcp.json                        # Shared MCP configuration placeholder (no secrets, no active servers)
├── .gitignore                       # Ignores CLAUDE.local.md, settings.local.json, .env
├── .env.example                     # Safe environment variable placeholders
├── .claude/                         # Claude Code thin configuration
│   ├── settings.json                # Permissions baseline (hooks unwired until approved [VERIFY])
│   ├── rules/                       # Short (< 60 lines) modular rules pointing to docs/standards/
│   ├── commands/                    # /plan-feature, /review, /test-all, /release-checklist
│   ├── skills/                      # test-writer/, security-audit/, code-review/, perf-test/
│   ├── agents/                      # Read-only code-reviewer & security-auditor, plus test-writer
│   └── hooks/                       # validate-bash.sh, secret-scan.sh, run-tests.sh
├── .agents/                         # Antigravity IDE thin configuration [VERIFY .agent vs .agents]
│   ├── rules/                       # Workspace rule pointers (standards.md, git-convention.md)
│   ├── workflows/                   # /plan-feature, /review, /release-checklist
│   └── skills/                      # test-writer/, security-audit/, code-review/, perf-test/
├── docs/
│   ├── standards/                   # SINGLE SOURCE OF TRUTH
│   │   ├── testing-standard.md
│   │   ├── definition-of-done.md
│   │   ├── ai-boundary.md
│   │   ├── security-baseline.md
│   │   ├── performance-sla.md
│   │   └── git-convention.md
│   ├── knowledge/                   # Project knowledge export (trellis-project-export.md)
│   ├── decisions/                   # Architecture Decision Records (0001-single-source-of-truth.md)
│   └── onboarding.md                # Developer onboarding & "review comment -> rule" loop
├── templates/                       # Review gate templates (plan, walkthrough, test-plan, PR)
└── scripts/                         # sync-tool-configs.md (design note for future config sync)
```

---

## 4. How to Adopt in a New Project (3 Steps)

1. **Copy the Starter Kit Structure:**
   Copy `docs/standards/`, `templates/`, `CLAUDE.md`, `GEMINI.md`, `.claude/`, `.agents/`, `.mcp.json`, `.env.example`, and the AI entries in `.gitignore` into your project repository.
2. **Configure Local Permissions & Environment Before First Use:**
   - Copy `.env.example` to `.env` for local placeholders (never commit `.env` or put secrets in rules/skills).
   - Configure tool permissions in `.claude/settings.json` (`[VERIFY]`) and Antigravity `/permissions` (plus browser allowlist/denylist) before running agents on project code.
   - Review `.claude/hooks/*.sh` and explicitly approve hook wiring before enabling automatic hooks.
3. **Run the `Plan -> Implement -> Verify -> Review` Workflow:**
   - Start features with `/plan-feature` (generating an Implementation Plan from `templates/implementation-plan.md` for human approval before code).
   - Verify changes with `/test-all` and `/review`, and complete releases with `/release-checklist`.
   - Follow the [Developer Onboarding Guide](./docs/onboarding.md) for daily usage in both tools.

---

## 5. Contribution Model Summary `[DRAFT]`

- **Single Source of Truth:** Edit canonical policies in `docs/standards/` first (see [ADR 0001](./docs/decisions/0001-single-source-of-truth.md)). Never maintain two divergent copies by hand.
- **Pull Requests & `CODEOWNERS`:** All changes to standards, rules, hooks, or AI-boundary tiers go through a Pull Request reviewed by a named owner (`TODO [TO RESEARCH]`).
- **Record Rationale:** Every change to a rule, hook, or AI-boundary tier records a short reason in `docs/decisions/` (ADR) or the changelog.
- **"Review Comment -> Rule" Loop:** If the same code-review comment appears **more than twice**, propose a rule or skill so the standard evolves from real project feedback.

---

## 6. Status & Roadmap (`v0.1` `[DRAFT]`)

- **Current Version:** `v0.1` (Kickoff scaffold based on [trellis-project-export.md](./docs/knowledge/trellis-project-export.md)).
- **Unfinished / Research Areas:** Marked explicitly with `[DRAFT]`, `TODO [TO RESEARCH]`, and `[VERIFY]` across `docs/standards/` and tool configs so open questions remain visible during Phase 0 / Phase 1 alignment.
