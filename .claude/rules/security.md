# Rule: Security Baseline

**Canonical Sources:**
- [Security Baseline](../../docs/standards/security-baseline.md)
- [AI Boundary Standard](../../docs/standards/ai-boundary.md)

## Summary Checklist

1. **Zero Secrets in Context, Code, or Configs:**
   - Never place secrets, tokens, or credentials in `CLAUDE.md`, `GEMINI.md`, rules, skills, `.mcp.json`, or source code.
   - Use `.env.example` with safe placeholders only; keep `.env`, `CLAUDE.local.md`, and `settings.local.json` gitignored.
2. **Respect Tier 3 Human-Only Boundaries (`[DRAFT]`):**
   - Never access or include production credentials, real customer/production data, or production deployment targets in prompts or MCP connections.
   - Financial/ledger correctness sign-off and security exceptions are strictly human-only (see [ai-boundary.md](../../docs/standards/ai-boundary.md)).
3. **Least-Privilege MCP & Permissions:**
   - Use minimum-permission MCP scopes and read-only database connections (`DB_READONLY=true`) where possible.
   - Verify `.claude/settings.json` permissions before running on a real project `[VERIFY]`.
4. **Enforcement via Hooks & Security Review:**
   - *A rule is a request; a hook is a guarantee.* Use `validate-bash.sh` and `secret-scan.sh` (once approved and wired) to enforce command safety and pre-commit secret scanning.
   - Run the read-only `security-auditor` subagent or `/pb-security-audit` skill on changes touching auth, input validation, dependencies, or data access.
