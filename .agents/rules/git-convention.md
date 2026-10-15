# Antigravity Rule: Git & Commit Conventions `[VERIFY .agent vs .agents]`

**Canonical Source of Truth:**
- [Git Convention & Commit Guidelines](../../docs/standards/git-convention.md)
- [Security Baseline](../../docs/standards/security-baseline.md)

## Summary Checklist (The 5 Golden Rules)

1. **Conventional Commit Format:**
   - Always format commits as: `<type>(<scope>): <summary in present imperative tense>`
   - Wrap optional body lines at **72 characters** and explain the motivation for the change.
2. **Subject Line Rules:**
   - Keep the header line under **72 characters**.
   - Start the subject in **lowercase**, use imperative verbs (`add`, `fix`, `switch`, `adjust` — **not** `added`, `fixes`, `updated`), and **omit any trailing period (`.`)**.
3. **Allowed Banking Commit Types:**
   - `feat`, `fix`, `sec` (security fixes), `audit` (audit/regulatory logging), `refactor`, `perf`, `build`, `ci`, `test`, `docs`, `style`, `chore`.
4. **Semantic Scopes & Branch Naming:**
   - Use an explicit module `<scope>` (see scope tables in [git-convention.md](../../docs/standards/git-convention.md)).
   - Name branches `<type>/<description>` (e.g., `feat/transfer`, `fix/route-mapping`, `sec/session-timeout`, `docs/git-convention`) integrated into `master` via Pull Request.
5. **Pre-Push Verification & Safety:**
   - Verify build, tests, lint, and secret scans pass before pushing.
   - Never commit `.env`, `CLAUDE.local.md`, or `settings.local.json`, and never force-push to `master`.
