# Rule: Git & Commit Conventions

**Canonical Source of Truth:**
- [Git Convention & Commit Guidelines](../../docs/standards/git-convention.md)
- [Security Baseline](../../docs/standards/security-baseline.md)

## Summary Checklist (The 5 Golden Rules)

1. **Conventional Commit Format:**
   - Every commit message must follow: `<type>(<scope>): <summary in present imperative tense>`
   - Optional body lines must explain *why* (motivation/context) and wrap at **72 characters**.
2. **Subject Line Rules:**
   - Maximum **72 characters** total for the header line.
   - Start subject with **lowercase**; use imperative verbs (`add`, `fix`, `switch`, `adjust` — **never** `added`, `fixes`, `updated`).
   - **No trailing period (`.`)** at the end of the header.
3. **Allowed Banking Commit Types:**
   - `feat` (new capability), `fix` (bug fix), `sec` (security fix/headers/session), `audit` (audit logging/KYC/compliance), `refactor` (no behavior change), `perf` (performance), `build` (deps/build config), `ci` (pipelines), `test` (tests), `docs` (documentation), `style` (formatting only), `chore` (maintenance).
4. **Domain Scope & Semantic Branch Naming:**
   - Always include a specific `<scope>` matching the module changed (e.g., `standards`, `claude`, `agents`, `templates` in `trellis`; or `router`, `auth`, `session`, `transfers`, `accounts`, `security` in banking apps).
   - Name branches `<type>/<description>` (e.g., `feat/transfer`, `fix/login-redirect`, `sec/session-timeout`, `docs/git-convention`) branched from `master`.
5. **Pre-Commit & Pre-Push Integrity:**
   - Stage explicit files rather than blind `git add .` when untracked local files exist; never stage `.env`, `CLAUDE.local.md`, or `settings.local.json`.
   - Run build, lint, secret scan, and tests before pushing. Never run `git push --force` to `master`.
