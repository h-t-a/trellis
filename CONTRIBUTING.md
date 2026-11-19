# Contributing to Trellis

## Workflow

1. **Plan** — For Class M/L or any Tier 2/3 change, produce an Implementation Plan and get human approval before writing feature code.
2. **Implement** — Keep changes small and requirement-linked (`[REQ-NNN-XX]`). Never weaken, skip, or delete tests to make a build pass.
3. **Verify** — Run the test suite, the workspace doctor, and any relevant performance checks.
4. **Review** — Open a PR using `templates/pull_request_template.md` and pass the review gate.

## Requirements

- Python 3.9+ (standard library only; no runtime dependencies).
- PowerShell 5.1+ on Windows or a POSIX shell on macOS/Linux.

## Setup

```powershell
python -m trellis_mcp --sync-workspace
python -m trellis_mcp --check
python -m unittest discover -s tests -v
```

## Tests

- Add a failing test first (`trellis_test` can generate a skeleton), then implement.
- Use requirement IDs in test names and docstrings (`[REQ-NNN-XX]`).
- Run the full suite (`47` tests across `test_trellis_mcp.py` and `test_spec_001_upgrades.py`) before pushing: `python -m unittest discover -s tests -v`.

## Commit Convention

- Follow Conventional Commits: `feat(scope): summary`, `fix(scope): summary`, `docs(scope): summary`.
- Keep the subject imperative, lowercase, ≤ 72 characters, and without a trailing period.
- Reference the affected requirement IDs in the commit body when relevant.

## Security

- Never commit secrets, tokens, `.env` files, or `.trellis_keys.json`.
- Report vulnerabilities according to [SECURITY.md](./SECURITY.md).
- Follow [docs/standards/ai-boundary.md](./docs/standards/ai-boundary.md) for AI-assisted changes.

## Documentation

- Update [CHANGELOG.md](./CHANGELOG.md) for user-visible changes.
- Keep standards in `docs/standards/` and unified `/pb-*` skills in `.agents/skills/` as the single source of truth; run `python -m trellis_mcp --sync-workspace` after skill edits and link rather than duplicate.
