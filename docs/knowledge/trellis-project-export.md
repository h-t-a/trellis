# AI-Assisted Development Standard - Project Knowledge & Ideation Export

Exported: 2026-10-15
Status: Working draft v0.1 (input for project kickoff)

Legend used in this file:
- **[VERIFIED]** checked against current docs or sources during our discussion
- **[SOURCE: Developers]** came from my own notes, images, or uploaded material
- **[DRAFT]** my proposal, to be decided with developers and the team
- **[TO RESEARCH]** not yet researched in depth, next research topic
- **[VERIFY]** details that differ between sources or versions; confirm in the app/docs before relying on them

---

## 1. Project purpose

Build a shared, version-controlled standard for AI-assisted development so that:

1. **Consistency**: every project and every developer gets the same quality bar when working with AI.
2. **Skill growth**: AI use makes the developer stronger (critical review of plans, rules learned from mistakes), not weaker.
3. **Cross-team collaboration and contribution**: other teams can adopt, reuse, and contribute to the standard.
4. **Planning**: current projects are planned using the same workflow (plan -> implement -> verify -> review).

Tools in daily use: **Antigravity IDE** and **Claude Code**.
Domain context: enterprise banking / government-style systems, so security and testing discipline are first-class concerns.

---

## 2. Tool landscape and how the two tools map

### 2.1 Antigravity IDE features [SOURCE: Developers]
- **Plugins**: package skills, background subagents, linting rules, MCP servers, and lifecycle hooks into one deployable asset.
- **Browser**: browser recordings, allowlist/denylist, separate Chrome profile.
- **Artifacts**: structured deliverables created by the agent so developers can review at milestones instead of watching every step.
  - Implementation Plan (review before code changes)
  - Walkthrough (summary of what changed after implementation)
  - Screenshots, code diffs, diagrams, browser recordings
- **Projects**: prompting/interaction patterns, resuming and forking conversations.
- **Slash commands**: `/agents`, `/boost`, `/btw`, `/changelog`, `/codesearch`, `/context`, `/credits`, `/diff`, `/effort`, `/permissions`, `/plan`, `/resume`, `/statusline`, `/teamwork-preview`, `/title`, `/usage`.
- **Extends**: MCP, Agent Skills (folder with `SKILL.md`), Rules (persistent instructions auto-discovered from the filesystem), IDE Workflows (Markdown files invoked as `/workflow-name`), Custom Subagents, Lifecycle Hooks, Sidecars.
- Some items (e.g. `/teamwork-preview`, Sidecars) look like preview features. [VERIFY] by trying them before they go into the standard.

### 2.2 Claude Code memory and structure [VERIFIED against Claude Code memory docs and summaries]
- Project instructions live in `./CLAUDE.md` or `./.claude/CLAUDE.md`.
- `CLAUDE.local.md` holds personal, machine-local notes, appended after `CLAUDE.md` at the same level. Gitignore it.
- Claude Code walks up the directory tree from the working directory and loads every `CLAUDE.md` / `CLAUDE.local.md` it finds. Nested ones in subdirectories load lazily.
- `.claude/rules/*.md` are modular rule files, discovered automatically; they can be scoped to paths.
- `CLAUDE.md` can import other files with `@path/to/file`, so docs are linked rather than copied.
- **Claude Code reads `CLAUDE.md`, not `AGENTS.md`.**
- Docs recommend keeping each `CLAUDE.md` around **200 lines** for reliability; split into rules, skills, or nested files beyond that.
- `/init` generates a starter `CLAUDE.md`; `/memory` opens the memory editor; `/context` shows what is loaded.
- Subagents are Markdown files in `.claude/agents/`; skills are folders with `SKILL.md`; custom slash commands are Markdown files in `.claude/commands/`.

### 2.3 Concept mapping

| Concept | Antigravity | Claude Code | Notes |
|---|---|---|---|
| Persistent standards | Rules | `CLAUDE.md` + `.claude/rules/*.md` | Prompt-level context |
| Project context file | `GEMINI.md` (per community sources) | `CLAUDE.md` | [VERIFY] which file Antigravity reads in our version |
| Task-specific know-how | Skills (`SKILL.md`) | Skills (`SKILL.md`) | Same open-standard idea, reusable across both |
| Repeatable procedures | Workflows (`/name`) | Commands (`.claude/commands/*.md`) | Trajectory-level step sequences |
| Enforcement | Lifecycle hooks | Hooks (`.claude/hooks/`, configured in `settings.json`) | Rules ask; hooks enforce |
| Parallel/specialist work | Custom subagents | `.claude/agents/*.md` | Isolated context, tool limits |
| External tools | MCP | MCP (`.mcp.json`, shared via git) | Least privilege |
| Review gates | Artifacts (plan, walkthrough) | Plan before edits + PR description | Make the same gate in both tools via templates |
| Permissions | `/permissions`, browser allow/deny | `settings.json` permissions | Security baseline |
| Folder for workflows | `.agent/workflows/` or `.agents/workflows/` | `.claude/commands/` | [VERIFY] exact Antigravity folder name by version |

**Design implication:** write the standard once in plain Markdown docs; keep tool-specific files thin and make them point at those docs.

---

## 3. Layered model for the standard [DRAFT]

1. **Rules** (always loaded): coding standards, architecture constraints, naming, security basics. Keep short.
2. **Skills** (loaded on demand): how to do one kind of task well, e.g. write an endpoint, write tests, run a security audit, refactor.
3. **Workflows / Commands** (invoked explicitly): `plan-feature`, `review-pr`, `write-tests`, `release-checklist`, `perf-test`.
4. **Hooks** (automatic enforcement): lint/format after edits, block dangerous commands, secret scan before commit, run tests at completion.
5. **Artifacts / templates** (review gates): implementation plan, walkthrough, test plan, PR template.
6. **MCP and subagents** (reach and parallelism): GitHub, ticketing, DB read-only, browser testing; reviewer and security-auditor subagents.

Key principle: **a rule is a request; a hook is a guarantee.** Anything that must never happen belongs in a hook or permission setting, not only in prose.

---

## 4. Testing standard

### 4.1 Performance testing knowledge [SOURCE: Developers, with corrections]

Context from our meeting notes: Management targets of **10,000** for the Wallet application and **1,000+** for the Web Portal.

Open issue: the term heard in the meeting ("TUS") was assumed to be **TPS** (transactions per second). That is an assumption. **Confirm with the Management** whether 10,000 means TPS, concurrent users, or daily transaction volume. Each changes the architecture and test design completely.

Core terms:
- **TPS**: completed business transactions per second (e.g. full transfer flow).
- **QPS**: queries per second hitting DB/search; one TPS usually causes several QPS.
- **RPS/HPS**: raw HTTP requests or hits per second.
- **VUs**: virtual users simulated by the load tool.
- **Response time**: report as **percentiles (p50/p95/p99)**, not only average; averages hide slow tail requests.
- **Error rate**: part of the SLA, not an afterthought.
- **SLA/SLO**: the pass/fail threshold, e.g. "10,000 TPS sustained 30 min, p95 < 2 s, error rate < 0.1 %". (Numbers are examples, not agreed targets.)

Test types: load, stress, endurance/soak, spike. Also consider volume (large data sets), scalability, and capacity-planning tests. [TO RESEARCH]

Sizing relationship (Little's Law): **concurrent VUs ≈ TPS × (response time + think time)**.

Correction to the earlier note: "ramp VUs up until the target is reached" describes only the ramp-up phase. Acceptance means **holding the target load for a defined duration and checking the SLA pass/fail**, then going beyond it (stress) to find the breaking point.

Tools to compare: Apache JMeter, Grafana k6 (and others). [TO RESEARCH]

Items missing from the original notes (to add to the standard):
- baseline measurement before changes
- production-like test environment and data volume
- realistic test data and transaction scripts (e.g. Login -> Balance -> Transfer -> Confirm)
- monitoring during tests (CPU, memory, DB IOPS, connection pools, GC)
- bottleneck analysis and re-test loop
- explicit pass/fail criteria and sign-off owner
- when performance tests run (per release, nightly, on major change)

### 4.2 Test levels and policy [TO RESEARCH]
For each level, define: what it verifies, who writes it, where it runs, and what blocks a merge.
- Unit
- Integration
- Contract (API)
- End-to-end
- Performance
- Security (SAST, dependency scan, DAST)
- Regression / smoke

Also decide: test data management, environment strategy, coverage policy (risk-based rather than a single percentage), flaky-test policy, CI gates.

### 4.3 Rules for AI-written tests [DRAFT seeds, to research]
- A human reviews every AI-written test for meaningful assertions (not tests that pass without checking anything).
- AI must not delete, skip, or weaken an existing test to make a build pass.
- New behavior and bug fixes come with a test that fails before the change and passes after.
- Tests state the requirement they verify.
- Consider mutation testing to check test quality.

---

## 5. Definition of Done [DRAFT, to research and finalize]

**Story / change level**
- Implementation plan reviewed by a human before significant AI-generated code (plan artifact or equivalent)
- Code reviewed by a human
- Tests at the right levels written and passing in CI
- Lint/format/static analysis clean
- Secret scan and dependency scan clean
- Docs or ADR updated when behavior or architecture changed
- Walkthrough or PR description states what changed and where AI was used

**Release level**
- Regression suite green
- Performance test run against the agreed SLA, with report attached
- Migrations and schema changes reviewed by a human
- Rollback plan documented
- Monitoring and alerts in place
- Sign-off by named owner

---

## 6. AI boundary: what AI should and should not do [DRAFT, decide with team]

**Tier 1: AI may act autonomously**
Boilerplate, code explanation, documentation drafts, lint/format fixes, unit-test drafts, refactors that existing tests cover.

**Tier 2: AI drafts, human must approve**
Feature code, API changes, DB schema and migration scripts, dependency upgrades, CI/CD config, authentication/authorization and input-validation code, test strategy changes.

**Tier 3: human-only (AI excluded or read-only)**
- production credentials and secrets
- real customer or production data in prompts or MCP connections
- production deployments and production data changes
- sign-off on financial/ledger correctness
- security exceptions and compliance decisions
- removing or weakening tests to get a green build

Supporting items to research: data classification levels, which MCP servers are allowed per project, approval authority for exceptions, audit trail of AI usage. [TO RESEARCH]

---

## 7. Security baseline [SOURCE: Developers + images + docs]

- Never put secrets in `CLAUDE.md`, rules, or skills. Use `.env.example` as the template; real `.env` is gitignored.
- Gitignore `CLAUDE.local.md` and `settings.local.json`.
- Pre-commit secret detection hook.
- Minimum-permission MCP scope; read-only DB access where possible.
- Configure permissions (`/permissions`, `settings.json`) and browser allowlist/denylist before first use on a real project.
- Hooks that block unsafe shell operations (the `validate-bash` idea from our second image).
- Audit subagent for security review (`security-auditor`).

---

## 8. Project folder structure (draft)

The project is a **starter kit / template repo** that teams can copy or reference.

```
trellis/
├── README.md
├── CLAUDE.md                  # short; imports standards with @docs/standards/...
├── GEMINI.md                  # short; points to same docs  [VERIFY file name per Antigravity version]
├── .mcp.json                  # MCP server config shared via git (no secrets)
├── .gitignore                 # CLAUDE.local.md, settings.local.json, .env
├── .env.example
├── .claude/
│   ├── settings.json          # permissions, hooks wiring
│   ├── rules/                 # code-style.md, testing.md, api-conventions.md, security.md
│   ├── commands/              # plan-feature.md, review.md, test-all.md, release-checklist.md
│   ├── skills/                # test-writer/, security-audit/, code-review/, perf-test/
│   ├── agents/                # code-reviewer.md, security-auditor.md, test-writer.md
│   └── hooks/                 # validate-bash.sh, secret-scan.sh, run-tests.sh
├── .agents/                   # Antigravity: workflows/, rules/, skills/  [VERIFY folder names]
├── docs/
│   ├── standards/             # source of truth
│   │   ├── testing-standard.md
│   │   ├── definition-of-done.md
│   │   ├── ai-boundary.md
│   │   ├── security-baseline.md
│   │   └── performance-sla.md
│   ├── knowledge/             # research exports (e.g. performance testing notes)
│   ├── decisions/             # ADRs
│   └── onboarding.md
├── templates/                 # implementation-plan.md, walkthrough.md, test-plan.md, PR template
└── scripts/                   # sync script: generate tool-specific files from docs/standards
```

Notes on our two folder-structure images:
- **Image with pink background**: matches the documented layout (CLAUDE.md, CLAUDE.local.md, `.mcp.json`, `.claude/` with settings, rules, commands, skills, agents, hooks). Use it as the reference.
- **Blue "Project Structure" cheat sheet**: useful ideas, but it contains typos (`Hoobs`, `PoetToolUse`, `code-revloser.yml`, `/oost`) and some points that conflict with the docs:
  - lists agents as `.yml`; Claude Code subagents are Markdown files
  - says keep `CLAUDE.md` under 500 lines; docs recommend about 200
  - presents `/deploy`, `/test-all`, `/bootstrap` as "common" commands; these are custom commands developers define, not built-ins
  - context-percentage thresholds (`/compact` at 70–90 %, `/clear` at 90 %+) are rules of thumb, not official limits
- Anti-patterns worth keeping from the sheet: bloated `CLAUDE.md`, vague instructions ("write good code"), copying docs instead of linking, no testing guidance, no error-handling patterns.

You mentioned more findings about project folders are coming; this section should be revised after those.

---

## 9. Ideation plan / roadmap [DRAFT]

**Phase 0: Confirm**
- Which project is the pilot (Wallet? Web Portal? other)
- What the Management targets actually mean (TPS vs users vs volume)
- Who owns the standard and who approves changes

**Phase 1: Research (granular)**
1. Testing standard (levels, data, environments, CI gates, performance SLA)
2. Definition of Done (story and release)
3. AI boundary (tiers, data classification, approvals)
4. Security baseline details

**Phase 2: Write the source-of-truth docs** in `docs/standards/`.

**Phase 3: Encode into tools**
Rules -> skills -> workflows/commands -> hooks -> subagents -> MCP, for both Claude Code and Antigravity.

**Phase 4: Pilot** on one project for a fixed period. Collect what AI got wrong, turn repeated review comments into rules, tighten or relax tiers.

**Phase 5: Cross-team rollout**
Contribution model, onboarding doc, versioned releases of the standard.

Suggested success measures: fewer repeated review comments, test pass rate on first CI run, time from plan to merged PR, number of rule/skill contributions from other teams, zero secret leaks.

---

## 10. Collaboration and contribution model [DRAFT]

- Standards live in a repo; changes go through pull requests with a named reviewer (CODEOWNERS).
- Every change to a rule, hook, or AI-boundary tier records a short reason (ADR or changelog).
- "Review comment -> rule" loop: if the same review comment appears more than twice, propose a rule or skill.
- Version the standard (e.g. v0.1, v0.2) so teams know which one they follow.
- Keep one source of truth; generate or link tool-specific files rather than maintaining two copies by hand.

## 11. Personal skill-growth practices [DRAFT]

- Read the AI's implementation plan critically before approving; write down what I would have changed.
- Write the failing test or acceptance criteria myself before asking AI to implement.
- Turn mistakes into rules or skills, which forces me to state the standard explicitly.
- Periodically do a task without AI to keep fundamentals sharp.

---

## 13. Verification checklist before finalizing

- [ ] Antigravity: workflows/rules/skills folder names and context file (`GEMINI.md` vs other)
- [ ] Antigravity: which preview features are stable enough to depend on
- [ ] Claude Code: hook configuration format in our installed version
- [ ] Claude Code: current `CLAUDE.md` length guidance
- [ ] Performance tooling choice (JMeter vs k6) and target environment

## 14. Reference pointers

- Claude Code memory docs: https://code.claude.com/docs/en/memory
- Our uploaded material: performance testing knowledge export; Antigravity features list; two Claude Code project-structure images; Claude command cheat sheet (note: most "commands" in that image are prompt phrases, not real commands).
