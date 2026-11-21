---
name: pb-git-convention
description: Use when crafting Conventional Commits, branch names, and verifying pre-push gates. Not for resolving code review comments.
metadata: {pack: core, tier: 1, quota_class: S, standards: [git-convention, security-baseline]}
---

# Skill: `/pb-git-convention` — Conventional Commits & Branch Hygiene

**Canonical Standards:**
- [docs/standards/git-convention.md](../../../docs/standards/git-convention.md)
- [docs/standards/security-baseline.md](../../../docs/standards/security-baseline.md)

## Execution Steps

1. **Validate Branch Name:**
   - Use `<type>/<short-kebab-description>` (e.g., `feat/model-router`, `fix/lockout-window`, `sec/origin-allowlist`, `docs/git-skill`).
   - Never commit directly or force-push (`git push --force`) to `master` when a PR workflow is expected.
2. **Format Conventional Commit Header & Body:**
   - Use `<type>(<scope>): <imperative summary>` under **72 characters**.
   - Allowed banking/engineering types: `feat`, `fix`, `sec`, `audit`, `refactor`, `perf`, `build`, `ci`, `test`, `docs`, `style`, `chore`.
   - Start `<summary>` in **lowercase**, use **present imperative tense** (`add`, `fix`, `enforce`, not `added`/`fixes`), and **omit trailing `.`**.
   - Wrap optional body lines at 72 characters explaining **why** the change was made; cite `[REQ-NNN-XX]` IDs and AI co-authorship disclosure when applicable.
3. **Run Pre-Commit / Pre-Push Safety Gates:**
   - Call `trellis_scan` / `trellis_review` (or run `.claude/hooks/secret-scan.sh`) to verify no `.env*`, `.trellis_keys.json`, `settings.local.json`, tokens, or Luhn-valid PANs are staged.
   - Verify the relevant test suite passes without skipped or weakened assertions before pushing.
