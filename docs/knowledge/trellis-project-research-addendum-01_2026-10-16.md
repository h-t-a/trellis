# AI Dev Playbook — Research Addendum 01
## Fast root-cause debugging, spec-driven work, complexity-aware enhancement, quota efficiency, and custom commands

Date: 2026-10-16
Extends: `ai-dev-standard-project-export.md` (continue numbering from section 15)
Status: Round 1 research. Draft for review.

Legend: **[VERIFIED-OFFICIAL]** from Google's Antigravity IDE codelab (about two weeks old at time of research) · **[COMMUNITY]** from community guides/tools, may be outdated · **[GENERAL]** general engineering practice · **[DRAFT]** my proposal · **[TO RESEARCH]** next round · **[VERIFY]** check in your own IDE

Interpretation note: "quotanization" is read as **AI usage quota / token cost efficiency**. Correct me if you meant something else.

---

## 15. Corrections and confirmations to earlier files

| Earlier assumption | Finding | Action |
|---|---|---|
| Antigravity folder is `.agent` or `.agents` [VERIFY] | Official codelab uses **`.agents/`**: `.agents/rules/`, `.agents/workflows/`, `.agents/skills/` [VERIFIED-OFFICIAL] | Use `.agents/` everywhere |
| Root `GEMINI.md` is the project context file | Official docs name `~/.gemini/GEMINI.md` as the **global** rule file; workspace rules go in `.agents/rules/`. A root `gemini.md` being auto-read comes only from a community guide [COMMUNITY] | Put project rules in `.agents/rules/`. Treat root `GEMINI.md` as optional [VERIFY] |
| Global workflow path | Codelab: `~/.gemini/config/global_workflows/`. An older community guide shows `~/.gemini/antigravity/global_workflows/` | Use the codelab path; confirm on your machine [VERIFY] |
| Skills location | Workspace `.agents/skills/<name>/SKILL.md`; global `~/.gemini/config/skills/` [VERIFIED-OFFICIAL] | Matches the existing plan |
| MCP config | `~/.gemini/config/mcp_config.json` (global) [VERIFIED-OFFICIAL] | Add to docs; keep secrets out of the repo |

Platform note [VERIFIED-OFFICIAL]: Antigravity is now four products: the **Antigravity** app (manage parallel agents), **Antigravity IDE**, **Antigravity CLI** (`agy`), and **Antigravity SDK**. They share the same underlying agents.

---

## 16. Antigravity IDE interaction reference

### 16.1 `@` mentions [VERIFIED-OFFICIAL]
In the agent panel, `@` adds context: **files, directories, the terminal, and MCP servers**. Example from the codelab: `review the @demo_bad_code.py file`.

Other ways to hand context to the agent [VERIFIED-OFFICIAL]:
- Select terminal output containing an error and send it to the conversation with `Cmd + L`.
- In the editor, hover a linter problem → **Explain and fix**.
- In the **Problems** tab → **Send to Agent**.
- `Cmd + L` toggles the agent panel.

**Playbook conventions for `@` [DRAFT]:**
- Prefer `@file` over `@directory`; use a directory only when it is small and relevant.
- For failures, attach terminal output (the failing command and error), not the whole log.
- Name an MCP server explicitly only when the task needs it.
- Never `@` secret files (`.env`, key stores).

### 16.2 Built-in slash commands
Named in the codelab [VERIFIED-OFFICIAL]:
- `/goal`: run a task until completion
- `/schedule`: schedule one-time or recurring tasks
- `/grill-me`: align on a plan with the agent by being questioned first
- `/learn`: extract reusable skills or rules from a conversation

From your own notes [SOURCE: you]: `/agents`, `/boost`, `/btw` (side question), `/changelog`, `/codesearch`, `/context`, `/credits`, `/diff`, `/effort`, `/permissions`, `/plan`, `/resume`, `/statusline`, `/teamwork-preview`, `/title`, `/usage`.

Open items [VERIFY in your IDE, type `/` and read the list]: exact behavior and arguments of `/boost`, `/effort`, `/codesearch`, `/usage`, `/credits`.

### 16.3 Custom slash commands = Workflows [VERIFIED-OFFICIAL]
- A workflow is a saved prompt triggered on demand with `/`. Rules are always-on system-style guidance; workflows are invoked.
- Workspace: `.agents/workflows/<name>.md`. Typing `/gen…` autocompletes a workflow named `generate-unit-tests` in the codelab.
- Create via `...` → **Customizations** → **Workflows** → **+ Workspace**, or by adding the file.

**Naming rule [DRAFT]:** prefix every playbook workflow with `pb-` (e.g. `/pb-rca`). Typing `/pb` lists all playbook commands and avoids collisions with built-ins.

### 16.4 Skills and progressive disclosure [VERIFIED-OFFICIAL]
Only name and description are read up front; the full skill loads when the request matches. The codelab states that loading everything into context causes tool bloat, higher cost, latency, and confusion. This is the main structural lever for cost efficiency: **put long procedures in skills, not in always-on rules.**

### 16.5 Artifacts as review gates [VERIFIED-OFFICIAL]
Implementation plan and task list appear before coding; code diffs during; walkthrough after. You can add document-style comments to a plan and **submit** them to make the agent revise. The agent sometimes proceeds to code without waiting; you can stop it, comment on the plan, and resubmit.
Safety setting: during setup the codelab recommends **Review-driven development**, and Advanced Settings control terminal, file-system, and JavaScript execution freedom. Set these before real work [VERIFIED-OFFICIAL].

---

## 17. Quota and cost model

### 17.1 What the sources agree on
- Quota is **per model family/pool**, and heavy models burn it faster. [COMMUNITY]
- **AI credits** are an overage mechanism after baseline quota runs out; a toggle (Settings → Models) chooses **Never** (wait for refresh) or **Always** (spend credits). [COMMUNITY]
- Credits do not refill or reset the baseline cooldown. [COMMUNITY]
- Quota is shared at the Google-account level across the IDE and CLI. [COMMUNITY]
- Unused quota does not roll over. [COMMUNITY]

### 17.2 What changes often [VERIFY before relying on it]
Refresh windows (5-hour vs weekly), plan prices, and caps differ between sources and have changed during 2026. Do not hard-code any number into the playbook. Read the current numbers from **`/usage`**, **`/credits`**, and the official "Plans" docs in your own account.

### 17.3 Where tokens go [COMMUNITY]
- Every follow-up message re-sends accumulated context, so long conversations cost more per turn.
- Letting the agent explore the whole project is expensive; naming exact files is cheaper.
- Indexing noise (`node_modules`, build output, lock files) wastes context; an ignore file (`.antigravityignore` per a community guide) is claimed to help [VERIFY it exists in your version].
- Large always-on rules cost tokens on every turn.
- Mid-session context compaction exists in the agent harness (documented for the API agent at around 135k tokens) [COMMUNITY-adjacent, VERIFY for IDE].

### 17.4 Quota-efficiency rules for the playbook [DRAFT]
1. **One task, one conversation.** Start fresh after a task closes; carry state in a short handoff file instead of a long thread.
2. **Right-size the model and effort.** Small or single-file changes → fast model, low effort. Cross-cutting design or hard bugs → stronger model, higher `/effort`. Decide before starting, not after burning quota.
3. **Name files with `@`.** Start from the stack trace or the diff, not a repo scan.
4. **Evidence before exploration.** Gather error output, recent diff, and logs first; read code second.
5. **Cap retries.** After 3 failed hypotheses or fix attempts, stop and re-plan (`/grill-me`) rather than looping.
6. **Keep rules short; move procedures to skills.**
7. **Set credit overage to Never** on shared or budget-sensitive accounts unless a deadline justifies Always.
8. **Check `/usage` before large tasks** and log rough cost per task class to learn what is expensive.
9. **Batch checks:** run tests/lint once per change set, not after every edit, unless debugging.

### 17.5 Task cost classes [DRAFT]
| Class | Typical scope | Model/effort | Budget rule |
|---|---|---|---|
| S | one file, clear cause | fast model, low effort | no plan artifact needed |
| M | 2–5 files, one module | default model, medium effort | plan + tasks, tests once |
| L | cross-module, design choice, perf work | strong model, high effort | spec first, plan approval, split into M-sized tasks |

---

## 18. Fast root-cause analysis (RCA) method [GENERAL, DRAFT for the playbook]

Goal: shortest path from symptom to proven cause, with the fewest tokens and minutes.

1. **Restate the symptom** in one line: expected vs actual, where, since when, how often.
2. **Reproduce.** If it cannot be reproduced, say so and collect more evidence; do not guess a fix.
3. **Collect cheap evidence first:** stack trace, failing test, logs around the failure, last known good version, recent commits touching the area (`/diff`, git log/blame).
4. **Narrow the search space** by bisecting: git bisect on commits, input minimization, disabling components, or comparing a working and a failing environment.
5. **Form at most 3 ranked hypotheses.** For each, name the single cheapest check that would disprove it.
6. **Run the cheapest discriminating check first** (a log line, a unit test, a query plan, a single breakpoint).
7. **Prove the cause** with a test that fails because of it.
8. **Ask "why did this reach us?"** (missing test, weak validation, unclear spec) and record a rule or test to prevent recurrence (`/learn` can help extract it).
9. **Report:** cause, evidence, minimal fix options, risk, test added.

Typical performance-flavored causes to check early in enterprise Java/web back ends [GENERAL]: N+1 queries, missing database indexes, unbounded result sets without pagination, work repeated inside loops, chatty remote calls, lock contention or connection-pool exhaustion, synchronous calls that should be batched.

Anti-patterns: fixing before reproducing, reading the whole codebase first, changing several things at once, "fixing" by weakening a test, retrying the same failed idea.

[TO RESEARCH]: structured RCA formats (5 Whys, fault tree, timeline), observability inputs to attach to the agent (traces, metrics), flaky-test triage, production incident variant with human-only steps per the AI boundary.

---

## 19. Spec-driven development flow [DRAFT, with research needed]

Why it matters here: a written spec gives the agent a precise target, reduces rework tokens, and gives reviewers something to check the result against.

Proposed lifecycle:
1. **Spec** (`docs/specs/NNN-<name>.md`): problem, goals, non-goals, constraints, acceptance criteria, edge cases, test cases, security/AI-boundary notes, open questions.
2. **Approval** of the spec by a human (Tier 2 decision).
3. **Plan:** agent's implementation plan must trace to spec items; task list derived from the spec.
4. **Implement + test:** each acceptance criterion maps to at least one test.
5. **Verify:** walkthrough checks every criterion; deviations are listed.
6. **Close:** update spec status, ADR if architecture changed, extract new rules with `/learn`.

Spec template sections [DRAFT]: Context · Problem · Goals / Non-goals · Requirements (numbered, testable) · Acceptance criteria (Given/When/Then) · Constraints (performance SLA, security, compatibility) · Design notes · Test plan · Rollout/rollback · Open questions.

[TO RESEARCH]: how other spec-driven toolkits structure specs → plan → tasks, and which parts are worth adopting; how to keep specs small enough to be cheap but precise enough to be testable; spec ↔ test traceability.

---

## 20. Enhancement with time-complexity awareness [GENERAL, DRAFT]

1. **State the workload:** data size (n), growth, frequency, latency budget, memory limits. Complexity claims are meaningless without these.
2. **Measure before optimizing:** profile or time the current path; optimize only hot spots (the performance SLA from the testing standard supplies the target).
3. **Analyze current Big-O** (time and space) and identify the dominant term.
4. **List 2–3 options with tradeoffs:** complexity, memory, code complexity, risk, migration cost. Prefer the **direct approach** (simplest solution that meets the target) over clever ones.
5. **Pick one** with a stated reason and the condition under which you would revisit it.
6. **Implement behind tests;** add a benchmark or performance test for the hot path.
7. **Re-measure** and record before/after numbers in the walkthrough.

Output format for the agent: current complexity · target · options table · recommendation · benchmark plan.

[TO RESEARCH]: data-structure and indexing cheat sheet by common enterprise scenarios (lookups, joins, batch jobs, pagination, caching and invalidation), microbenchmark pitfalls, database query plan reading.

---

## 21. Custom command catalog (workflows) [DRAFT, names and steps to approve]

All files go in `.agents/workflows/` (Antigravity) and mirror in `.claude/commands/` (Claude Code). Each stays short and links to the docs in `docs/standards/`; long procedures live in skills.

| Command | Purpose | Inputs | Key steps | Quota guard |
|---|---|---|---|---|
| `/pb-rca` | Find root cause fast | symptom, `@terminal` or `@logfile`, suspect `@file` | sections 18 steps 1–9 | start from the stack trace; max 3 hypotheses; no repo-wide scan |
| `/pb-fix` | Fix a diagnosed bug | RCA report or failing test | failing test → minimal diff → run tests once → walkthrough | stop after 3 failed attempts and re-plan |
| `/pb-spec` | Write or update a spec | problem statement | draft spec from template → ask only blocking questions → wait for approval | one conversation for the spec only |
| `/pb-enhance` | Plan and implement an improvement | approved spec or request | workload → measure → options → recommend → implement → re-measure | require class (S/M/L) before starting |
| `/pb-complexity` | Analyze performance of code | `@file` and optional target | Big-O, hotspots, options, recommendation | analyze named functions only |
| `/pb-budget` | Estimate cost before starting | task description | classify S/M/L, suggest model and effort, suggest splits, remind to check `/usage` | output under 15 lines |
| `/pb-handoff` | Save state before a new conversation | current conversation | write short status file: goal, done, decisions, next steps, files to `@` | keep file under about 40 lines |
| `/pb-review` | Pre-PR check | current diff | check DoD, AI boundary, tests, security baseline, spec traceability | read the diff, not the repo |

Built-ins to combine with these (verify behavior first): `/plan`, `/grill-me` for alignment, `/diff` for changes, `/goal` for run-to-completion on well-specified tasks, `/learn` to turn lessons into rules or skills, `/usage` and `/credits` for cost.

Workflow file template [DRAFT]:
```
---
description: <one line: when to use this command>
---
# /pb-<name>
Inputs expected: ...
Follow docs/standards/<relevant>.md.
Steps:
1. ...
Stop conditions: ...
Output format: ...
Quota guard: ...
```
(Verify whether workflow files accept frontmatter in your version; if not, put the description in the first line.) [VERIFY]

Matching skills to add [DRAFT]: `rca-playbook`, `spec-writer`, `complexity-analysis`, `quota-budgeting`. Matching hook idea for Claude Code: warn when a task exceeds 3 consecutive failed test runs.

---

## 22. Changes to apply to project files

1. Replace `.agent` / `.agents` uncertainty with `.agents/` throughout the export and kickoff prompt.
2. Move Antigravity project rules to `.agents/rules/`; make root `GEMINI.md` optional [VERIFY].
3. Add `docs/specs/` and `templates/spec-template.md`.
4. Add `docs/standards/rca-playbook.md`, `docs/standards/quota-efficiency.md`, `docs/standards/complexity-and-performance.md`.
5. Add the `pb-*` workflows in section 21 (after you approve names and steps).
6. Add a section on `@` conventions and a slash-command reference to `docs/onboarding.md`.

## 23. Next research round (proposed order)

1. Confirm in your IDE: `/` command list and arguments, workflow frontmatter, `.antigravityignore`, credit settings.
2. RCA playbook granularity: evidence checklist per symptom type (exception, slow, wrong data, intermittent, deployment-only).
3. Spec-driven toolkits comparison and a minimal spec template that is cheap to use.
4. Complexity and performance cheat sheet for your typical systems.
5. Quota experiments: run the same small task at two effort levels and compare `/usage` before/after to build your own cost table.
6. Then return to testing standard, Definition of Done, and AI boundary details.

## 24. Sources used in this round
- Google Codelabs: Getting Started with Antigravity IDE (official)
- Community guides and monitoring extensions for Antigravity quota (setup guide, token-optimization guide, quota explainers, pricing summaries) [COMMUNITY]; numbers vary and change, so verify in-product.
