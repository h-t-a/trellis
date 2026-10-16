"""Implementation of the 8 callable Trellis MCP tools ([REQ-MCP-02]).

Each tool returns a standard MCP CallToolResult dictionary:
    {"content": [{"type": "text", "text": "..."}], "isError": False}
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parent.parent

STANDARD_FILE_MAP: dict[str, str] = {
    "testing-standard": "docs/standards/testing-standard.md",
    "performance-sla": "docs/standards/performance-sla.md",
    "definition-of-done": "docs/standards/definition-of-done.md",
    "ai-boundary": "docs/standards/ai-boundary.md",
    "security-baseline": "docs/standards/security-baseline.md",
    "git-convention": "docs/standards/git-convention.md",
    "rca-playbook": "docs/standards/rca-playbook.md",
    "quota-efficiency": "docs/standards/quota-efficiency.md",
    "complexity-and-performance": "docs/standards/complexity-and-performance.md",
    "spec-template": "templates/spec-template.md",
    "implementation-plan": "templates/implementation-plan.md",
    "walkthrough": "templates/walkthrough.md",
}

# F04: Patterns for raw PAN/card numbers (13-19 digits) and common credentials/tokens
_PAN_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
_SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"\bsk-(?:live|test|proj)?-?[A-Za-z0-9]{12,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?:password|passwd|api_key|apikey|client_secret)\s*[:=]\s*['\"][^'\"]{6,}['\"]", re.IGNORECASE),
]

# F03: Keywords indicating Tier 2 (Mandatory Human Review) or Tier 3 (Human-Only) domains
_TIER2_3_KEYWORDS = (
    "auth",
    "jwt",
    "oauth",
    "token",
    "password",
    "credential",
    "secret",
    "session",
    "rbac",
    "permission",
    "acl",
    "validation",
    "sanitize",
    "schema",
    "migration",
    "flyway",
    "liquibase",
    "ddl",
    "sql",
    "ledger",
    "payment",
    "transfer",
    "settlement",
    "balance",
    "security",
    "crypto",
    "encryption",
    "ci/cd",
    "pipeline",
    "dockerfile",
    "terraform",
    "pii",
    "gdpr",
    "pci",
)

_TEST_WEAKENING_PATTERNS = [
    re.compile(r"@Disabled\b"),
    re.compile(r"@Ignore\b"),
    re.compile(r"\b(?:it|describe|test)\.skip\s*\("),
    re.compile(r"\b(?:xit|xdescribe|xtest)\s*\("),
    re.compile(r"@unittest\.skip"),
    re.compile(r"@pytest\.mark\.skip"),
]

_COMMIT_CONVENTION_RE = re.compile(
    r"^(feat|fix|sec|audit|refactor|perf|build|ci|test|docs|style|chore)(\([a-z0-9_/-]+\))?: [a-z][^.]*$"
)


def _ok(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": False}


def _err(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": True}


def _resolve_root(workspace_root: Path | None) -> Path:
    if workspace_root and (workspace_root / "docs" / "standards").exists():
        return workspace_root
    return PACKAGE_ROOT


def tool_trellis_get_standard(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Return the authoritative Trellis standard or template by name."""
    name = str(args.get("name", "all")).strip().lower()
    root = _resolve_root(workspace_root)

    if name in ("all", "list", ""):
        lines = ["# Available Trellis Standards & Templates", ""]
        for key, rel_path in STANDARD_FILE_MAP.items():
            lines.append(f"- `{key}` -> `{rel_path}`")
        return _ok("\n".join(lines))

    rel_path = STANDARD_FILE_MAP.get(name)
    if not rel_path:
        return _err(
            f"Unknown standard '{name}'. Available: {', '.join(sorted(STANDARD_FILE_MAP.keys()))}"
        )

    target = root / rel_path
    if not target.exists():
        target = PACKAGE_ROOT / rel_path
    if not target.exists():
        return _err(f"Standard file not found on disk: {rel_path}")

    return _ok(target.read_text(encoding="utf-8"))


def _scan_redaction_violations(text: str) -> list[str]:
    violations: list[str] = []
    if _PAN_PATTERN.search(text):
        violations.append("Potential unredacted 13-19 digit PAN / card / account number")
    for pat in _SECRET_PATTERNS:
        if pat.search(text):
            violations.append(f"Credential / secret token pattern matched (`{pat.pattern[:32]}...`)")
    return violations


def tool_trellis_rca(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Run the 9-step Fast RCA sequence with F04 Tier 3 redaction gate and F10 banking checks."""
    symptom = str(args.get("symptom", "")).strip()
    evidence = str(args.get("evidence", "")).strip()
    suspect_files = list(args.get("suspect_files") or [])

    if not symptom:
        return _err("`symptom` is required for trellis_rca.")

    combined = f"{symptom}\n{evidence}"
    violations = _scan_redaction_violations(combined)
    if violations:
        bullet_list = "\n".join(f"- {v}" for v in violations)
        return _err(
            "## TIER 3 REDACTION BLOCK (`[REQ-RCA-01]` / `F04`)\n\n"
            "Unredacted sensitive data or credentials were detected in the RCA input:\n"
            f"{bullet_list}\n\n"
            "**Action Required:** Strip raw PANs, account numbers, JWTs, API keys, and PII "
            "using synthetic placeholders (`<PAN_REDACTED>`, `<TOKEN_REDACTED>`, `<USER_1>`) "
            "before invoking `trellis_rca`."
        )

    capped_files = suspect_files[:3]
    file_bullets = (
        "\n".join(f"- `{f}`" for f in capped_files)
        if capped_files
        else "- *(Identify Entry Point -> Domain Service -> Repository/Adapter)*"
    )

    report = f"""# Trellis Fast RCA Report (`[REQ-RCA-01..03]`)

## 1. Symptom & Redacted Evidence
- **Symptom:** {symptom}
- **Evidence (Redaction Verified):** `{evidence or "N/A"}`
- **3-Hop Call-Chain Scope (`[REQ-RCA-02]` — max 3 files):**
{file_bullets}

## 2. Hypotheses (Max 3)
| Rank | Hypothesis | Falsification Probe (1 command or file read) |
| :--- | :--- | :--- |
| **H1** | Primary state, boundary, or concurrency defect at the failing frame | Inspect exact line in `{capped_files[0] if capped_files else "failing module"}` and run targeted unit test |
| **H2** | Upstream contract mismatch (null/empty payload, precision loss, or stale schema) | Check input validation & DTO serialization at entry point |
| **H3** | Downstream timeout, retry storm, or non-idempotent side effect | Check adapter timeout, retry policy, and unique constraint handling |

## 3. Concurrency, Locks & Idempotency (`F10` Banking Checklist)
- [ ] **Race Conditions & Lock Ordering:** Can two concurrent requests read the same balance/state before commit (`SELECT ... FOR UPDATE` / optimistic version check)?
- [ ] **Transaction Isolation:** Does the transaction boundary match required consistency (`READ COMMITTED` vs `REPEATABLE READ` / `SERIALIZABLE`)?
- [ ] **Idempotency & Retries:** Is the operation safe under client/webhook retry or duplicate queue delivery (`X-Idempotency-Key`)?
- [ ] **Decimal & Timezone Safety:** Are monetary values using fixed-point decimal (never IEEE-754 float) and UTC timestamps?

## 4. Regression Test & Fix Verification (`[REQ-RCA-03]`)
1. **Red:** Write a failing unit/integration test reproducing `{symptom}`.
2. **Green:** Apply the minimal root-cause diff (do not bundle unrelated refactors).
3. **Verify:** Run the targeted test suite and confirm zero existing tests were skipped or weakened.
"""
    return _ok(report)


def tool_trellis_budget(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Classify a task into Class S / M / L quota budget with F03 Tier 2/3 safety guard."""
    description = str(args.get("task_description", "")).strip()
    file_count = int(args.get("file_count", 1))
    explicit_tier2_3 = bool(args.get("touches_tier2_or_tier3", False))

    desc_lower = description.lower()
    matched_keywords = [kw for kw in _TIER2_3_KEYWORDS if kw in desc_lower]
    touches_tier2_3 = explicit_tier2_3 or bool(matched_keywords)

    if file_count <= 1 and not touches_tier2_3:
        task_class = "Class S"
        max_reads = 5
        max_tools = 2
        spec_gate = "None (direct execution allowed — Tier 1 only)"
        note = "Eligible for Class S fast-path because scope is 1 file and Tier 1."
    elif file_count <= 5:
        if file_count <= 1 and touches_tier2_3:
            task_class = "Class M (auto-upgraded from Class S: touches Tier 2/3 domain)"
            note = (
                f"F03 Safety Guard triggered: 1-file change touches Tier 2/3 domain "
                f"({', '.join(matched_keywords) or 'explicit flag'}). Class S is restricted to Tier 1."
            )
        else:
            task_class = "Class M"
            note = "Standard 2-5 file or Tier 2 module task."
        max_reads = 12
        max_tools = 6
        spec_gate = "Part A Micro-Spec (4 sections) + human review required before coding"
    else:
        task_class = "Class L"
        max_reads = 25
        max_tools = 12
        spec_gate = "Full Spec (Part A + Part B 10 sections) + Implementation Plan + ADR (if architectural)"
        note = "Multi-module (>5 files) or architectural scope."

    return _ok(
        f"""# Trellis Quota & Task Classification (`[REQ-QUOTA-01]`)

- **Task:** {description or "Unspecified task"}
- **Estimated Files:** {file_count}
- **Touches Tier 2/3 Domain:** `{touches_tier2_3}` ({", ".join(matched_keywords) if matched_keywords else "none detected"})
- **Assigned Class:** **{task_class}**
- **Max File Reads:** ≤ {max_reads}
- **Max Tool / Search Calls:** ≤ {max_tools}
- **Required Spec Gate:** {spec_gate}
- **Rationale:** {note}
"""
    )


def tool_trellis_spec(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Generate a requirement-linked Spec (Part A Micro-Spec for Class M, Part A+B for Class L)."""
    spec_id = str(args.get("spec_id", "SPEC-001")).strip().upper()
    title = str(args.get("title", "Untitled Feature")).strip()
    problem = str(args.get("problem", "Describe the problem and user/business impact.")).strip()
    task_class = str(args.get("task_class", "M")).strip().upper()
    requirements: list[str] = list(args.get("requirements") or ["Define testable requirement"])
    non_goals: list[str] = list(args.get("non_goals") or ["Out-of-scope refactors or schema changes"])
    affected_files: list[str] = list(args.get("affected_files") or ["<path/to/file>"])

    digits_match = re.search(r"(\d+)", spec_id)
    spec_num = digits_match.group(1).zfill(3) if digits_match else "001"

    req_rows = []
    for idx, req_text in enumerate(requirements, start=1):
        req_id = f"REQ-{spec_num}-{idx:02d}"
        req_rows.append(
            f"| `[{req_id}]` | {req_text} | **Given** valid setup, **When** executed, **Then** `{req_id}` is verified by automated test |"
        )
    req_table = "\n".join(req_rows)
    non_goal_bullets = "\n".join(f"- {ng}" for ng in non_goals)
    file_rows = "\n".join(
        f"| `{f}` | Modify | `[REQ-{spec_num}-01]` | Unit / integration test covering `[REQ-{spec_num}-01]` |"
        for f in affected_files
    )

    spec_md = f"""# {spec_id}: {title}

- **Task Class:** `Class {task_class}`
- **Status:** `DRAFT`

---

## Part A: Core Micro-Spec (Mandatory for Class M and Class L)

### 1. Problem & Goal
{problem}

### 2. Non-Goals (Out of Scope)
{non_goal_bullets}

### 3. Requirements & Acceptance Criteria (`[REQ-{spec_num}-XX]`)
| Req ID | Requirement | Acceptance Criteria (`Given / When / Then`) |
| :--- | :--- | :--- |
{req_table}

### 4. File Touch List & Test Plan
| File Path | Action (`Create` / `Modify`) | Linked `[REQ-ID]` | Planned Test Case |
| :--- | :--- | :--- | :--- |
{file_rows}
"""

    if task_class == "L":
        spec_md += """
---

## Part B: Extended Sections (Mandatory for Class L Only)

### 5. Data Model & Schema Impact
- **Migrations:** Document forward-only migration script and index impact.
- **Backward Compatibility:** Confirm zero-downtime dual-read/write compatibility.

### 6. API Contract Changes
- **Endpoints / Schemas:** Document request/response payloads, status codes, and idempotency keys.

### 7. Performance & Complexity Targets
- **Target Throughput & Latency:** p95 < 500ms, p99 < 1500ms, error rate < 0.1%.
- **Algorithmic & I/O Bounds:** Time `O(N)`, Space `O(N)`, DB Queries `O(1)` batched.

### 8. Security & AI Boundary Review (Tier 2 / Tier 3)
- [ ] Input validation & schema enforcement
- [ ] AuthN / AuthZ object-level permission check
- [ ] Audit logging with zero PII/secret leakage

### 9. Rollout, Observability & Rollback Plan
- **Feature Flag / Canary:** Gradual rollout with automated rollback trigger on p99 or 5xx spike.

### 10. Open Questions
- [ ] Confirm cross-service SLA and downstream rate limits before execution.
"""

    return _ok(spec_md)


def tool_trellis_enhance(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Compute Little's Law concurrency sizing and Big-O + I/O complexity analysis ([REQ-PERF-01], F10)."""
    target = str(args.get("target", "TargetComponent")).strip()
    tps = float(args.get("tps", 100.0))
    response_time_sec = float(args.get("response_time_sec", 0.2))
    think_time_sec = float(args.get("think_time_sec", 0.8))
    data_size_n = int(args.get("data_size_n", 1000))
    current_behavior = str(args.get("current_behavior", "Unspecified baseline")).strip()
    mode = str(args.get("mode", "analyze")).strip().lower()

    wait_total = response_time_sec + think_time_sec
    steady_vus = tps * wait_total
    peak_vus = steady_vus * 1.5

    beh_lower = current_behavior.lower()
    has_n_plus_1 = any(tok in beh_lower for tok in ("n+1", "for-loop", "for loop", "per item", "per transaction", "nested loop"))
    current_io = "O(N) queries (N+1 anti-pattern detected)" if has_n_plus_1 else "O(1) or O(log N) indexed lookup"
    target_io = "O(1) batched query (`WHERE id IN (...)` / bulk join) with cursor pagination"

    report = f"""# Trellis Complexity & Performance Analysis (`[REQ-PERF-01]`)

## 1. Target & Mode
- **Target:** `{target}`
- **Mode:** `{mode}`
- **Dataset Scale (`N`):** `{data_size_n:,}` items
- **Current Behavior:** {current_behavior}

## 2. Little's Law Load & VU Sizing (`L = λ × W`)
- **Arrival Rate (`λ`):** `{tps:.1f} TPS`
- **Target Response Time (`R`):** `{response_time_sec:.3f} s`
- **Average Think Time (`Z`):** `{think_time_sec:.3f} s`
- **Total Cycle Time (`W = R + Z`):** `{wait_total:.3f} s`
- **Steady-State Concurrency (`L`):** **{steady_vus:.1f} VUs**
- **Peak Concurrency (1.5x Headroom):** **{peak_vus:.1f} VUs**
- **SLA Gate:** p95 < 500ms, p99 < 1500ms, Error Rate < 0.1%

## 3. CPU, Memory & I/O & Lock Complexity (`F10`)
| Dimension | Current Baseline | Optimal Target | Recommendation |
| :--- | :--- | :--- | :--- |
| **Time Complexity (CPU)** | `{"O(N²)" if "nested" in beh_lower else "O(N)"}` | `O(N)` or `O(log N)` | Pre-index lookups in a `dict`/`Map`/`Set` outside loops |
| **Space Complexity (RAM)** | `O(N)` | `O(page_size)` bounded | Stream or paginate results instead of materializing all `{data_size_n:,}` rows |
| **I/O & Query Complexity (`O(Q)`)** | `{current_io}` | `{target_io}` | Eliminate per-row network/DB round-trips; batch reads/writes |
| **Lock Contention (`O(L_hold)`)** | Held across external call / loop | Minimal row lock at commit | Never hold DB transactions open across HTTP/RPC calls |
"""
    if mode == "implement":
        report += """
## 4. Implementation & Verification Steps (`mode=implement`)
1. Replace loop-bound queries or `O(N²)` scans with pre-indexed batch operations.
2. Add a unit/benchmark test asserting query count `<= 2` regardless of batch size `N`.
3. Verify zero regressions across the existing test suite.
"""
    return _ok(report)


def tool_trellis_handoff(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Generate a compact <=25-line session handoff packet ([REQ-QUOTA-02])."""
    goal = str(args.get("goal", "")).strip()
    current_state = str(args.get("current_state", "")).strip()
    decisions = list(args.get("decisions_made") or [])
    files = list(args.get("files_touched") or [])
    next_step = str(args.get("next_step", "")).strip()
    save_to_file = args.get("save_to_file")

    dec_str = "; ".join(decisions[:4]) if decisions else "None"
    files_str = ", ".join(f"`{f}`" for f in files[:6]) if files else "None"

    packet = f"""# Session Handoff Packet (`[REQ-QUOTA-02]`)
- **Goal:** {goal or "Continue active task"}
- **Current State:** {current_state or "In progress"}
- **Key Decisions:** {dec_str}
- **Files Touched:** {files_str}
- **Immediate Next Step:** {next_step or "Run targeted verification"}
- **Resume Prompt:** Read only the files listed above and execute the Immediate Next Step.
"""
    if save_to_file and workspace_root:
        out_path = (workspace_root / str(save_to_file)).resolve()
        if str(out_path).startswith(str(workspace_root.resolve())):
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(packet, encoding="utf-8")

    return _ok(packet)


def tool_trellis_review(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Audit a diff and commit message against DoD, Testing, Security, and Git standards."""
    diff_text = str(args.get("diff_text", ""))
    commit_message = str(args.get("commit_message", "")).strip()
    spec_req_ids: list[str] = list(args.get("spec_req_ids") or [])

    issues: list[str] = []

    added_lines = "\n".join(
        line[1:]
        for line in diff_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    scan_target = added_lines if added_lines else diff_text

    # 1. Tier 3 Test-Weakening check
    for pat in _TEST_WEAKENING_PATTERNS:
        if pat.search(scan_target):
            issues.append(
                f"**[P0] Tier 3 Test-Weakening:** Detected skipped/disabled test annotation matching `{pat.pattern}`."
            )
            break

    # 2. Secret / Credential / PAN check
    secret_hits = _scan_redaction_violations(scan_target)
    if secret_hits:
        issues.append(
            f"**[P0] Secret / Credential Pattern:** {'; '.join(secret_hits)}."
        )

    # 3. Commit Message Convention check
    if commit_message:
        subject = commit_message.splitlines()[0]
        if len(subject) > 72 or not _COMMIT_CONVENTION_RE.match(subject):
            issues.append(
                f"**[P1] Commit Message Violation:** `{subject}` does not match "
                "`<type>(<scope>): <lowercase imperative summary without period>` (max 72 chars)."
            )

    # 4. Requirement Traceability check
    missing_reqs = [
        req_id
        for req_id in spec_req_ids
        if req_id not in diff_text and req_id not in commit_message
    ]
    if missing_reqs:
        issues.append(
            f"**[P1] Missing Requirement Traceability:** Spec IDs not referenced in diff/tests: `{', '.join(missing_reqs)}`."
        )

    verdict = "FAIL" if issues else "PASS"
    findings_block = (
        "\n".join(f"- {item}" for item in issues)
        if issues
        else "- All automated DoD, Security, Testing, and Commit checks passed."
    )

    return _ok(
        f"""# Trellis Pre-PR Code Review Report

- **Verdict:** **{verdict}**
- **Checked Spec IDs:** `{', '.join(spec_req_ids) if spec_req_ids else 'None specified'}`

## Findings
{findings_block}
"""
    )


def tool_trellis_doctor(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Audit and optionally auto-fix workspace rules, skills, and line budgets (F01, F02, [REQ-MCP-07])."""
    auto_fix = bool(args.get("auto_fix", False))
    inline_files = args.get("files")

    findings: list[str] = []
    fixes_applied: list[str] = []

    # Remote inline files mode ([REQ-MCP-07]: works over HTTP without local disk access)
    if isinstance(inline_files, dict):
        remediated_blobs: list[str] = []
        for rel_path, raw_content in sorted(inline_files.items()):
            content = str(raw_content)
            norm = str(rel_path).replace("\\", "/")
            if ".agents/rules/" in norm and norm.endswith(".md"):
                has_frontmatter = content.startswith("---\n") and "\ntrigger:" in content[:300]
                if not has_frontmatter:
                    findings.append(
                        f"Missing YAML frontmatter in `{norm}` (`F02` requires `trigger:` and `description:`)"
                    )
                    if auto_fix:
                        stem = Path(norm).stem
                        fixed_content = (
                            "---\n"
                            "trigger: always_on\n"
                            f"description: Trellis workspace rule ({stem})\n"
                            "---\n\n"
                            + content
                        )
                        fixes_applied.append(f"Fixed YAML frontmatter for `{norm}`")
                        remediated_blobs.append(f"### `{norm}`\n```markdown\n{fixed_content}```")
            if ".agents/workflows/" in norm and norm.endswith(".md"):
                findings.append(
                    f"Deprecated workflow file `{norm}` — migrate to `.agents/skills/<name>/SKILL.md` (`F01`)"
                )
            if norm.endswith("SKILL.md") and len(content.splitlines()) >= 80:
                findings.append(f"Skill `{norm}` exceeds <80 line budget")
            if norm.endswith("CLAUDE.md") and len(content.splitlines()) >= 200:
                findings.append(f"`{norm}` exceeds <200 line budget")

        status = "HEALTHY" if not findings or (auto_fix and fixes_applied) else "ISSUES_FOUND"
        findings_text = "\n".join(f"- {f}" for f in findings) if findings else "- Zero configuration issues detected."
        fixes_text = "\n".join(f"- {fx}" for fx in fixes_applied) if fixes_applied else "- None"
        extra_section = ("\n## Remediated File Contents\n" + "\n\n".join(remediated_blobs)) if remediated_blobs else ""
        return _ok(
            f"""# Trellis Workspace Doctor Report (`[REQ-MCP-07]` Remote Mode)

- **Mode:** `Inline Payload ({len(inline_files)} file(s))`
- **Status:** **{status}**

## Findings
{findings_text}

## Auto-Fixes Applied
{fixes_text}
{extra_section}"""
        )

    raw_path = args.get("workspace_path")
    root = Path(str(raw_path)).resolve() if raw_path else _resolve_root(workspace_root)

    # 1. Check .agents/rules/*.md for YAML frontmatter (F02)
    rules_dir = root / ".agents" / "rules"
    if rules_dir.exists():
        for rule_file in sorted(rules_dir.glob("*.md")):
            content = rule_file.read_text(encoding="utf-8")
            has_frontmatter = content.startswith("---\n") and "\ntrigger:" in content[:300]
            if not has_frontmatter:
                findings.append(
                    f"Missing YAML frontmatter in `.agents/rules/{rule_file.name}` (`F02` requires `trigger:` and `description:`)"
                )
                if auto_fix:
                    fixed_content = (
                        "---\n"
                        "trigger: always_on\n"
                        f"description: Trellis workspace rule ({rule_file.stem})\n"
                        "---\n\n"
                        + content
                    )
                    rule_file.write_text(fixed_content, encoding="utf-8")
                    fixes_applied.append(f"Fixed YAML frontmatter in `.agents/rules/{rule_file.name}`")

    # 2. Check legacy .agents/workflows/*.md (F01)
    workflows_dir = root / ".agents" / "workflows"
    if workflows_dir.exists():
        legacy_files = list(workflows_dir.glob("*.md"))
        if legacy_files:
            names = ", ".join(f.name for f in legacy_files)
            findings.append(
                f"Deprecated `.agents/workflows/` files present ({names}) — Antigravity IDE uses `.agents/skills/<name>/SKILL.md` (`F01`)"
            )
            if auto_fix:
                for lf in legacy_files:
                    lf.unlink()
                fixes_applied.append(f"Fixed: Removed {len(legacy_files)} deprecated `.agents/workflows/*.md` file(s)")

    # 3. Check .agents/skills/*/SKILL.md line budget (<80 lines) and frontmatter
    skills_dir = root / ".agents" / "skills"
    if skills_dir.exists():
        for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
            lines = skill_md.read_text(encoding="utf-8").splitlines()
            if len(lines) >= 80:
                findings.append(
                    f"Skill `{skill_md.parent.name}/SKILL.md` is {len(lines)} lines (exceeds <80 line budget)"
                )

    # 4. Check CLAUDE.md line budget (<200 lines)
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        c_lines = claude_md.read_text(encoding="utf-8").splitlines()
        if len(c_lines) >= 200:
            findings.append(f"`CLAUDE.md` is {len(c_lines)} lines (exceeds <200 line budget)")

    status = "HEALTHY" if not findings or (auto_fix and fixes_applied) else "ISSUES_FOUND"
    findings_text = "\n".join(f"- {f}" for f in findings) if findings else "- Zero configuration issues detected."
    fixes_text = "\n".join(f"- {fx}" for fx in fixes_applied) if fixes_applied else "- None"

    return _ok(
        f"""# Trellis Workspace Doctor Report (`[REQ-MCP-02]`)

- **Workspace:** `{root}`
- **Status:** **{status}**

## Findings
{findings_text}

## Auto-Fixes Applied
{fixes_text}
"""
    )


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "trellis_get_standard",
        "description": "Retrieve an authoritative Trellis engineering standard or template (e.g., testing-standard, rca-playbook, quota-efficiency, complexity-and-performance, security-baseline, ai-boundary, git-convention, definition-of-done, performance-sla, spec-template).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Standard or template name (or 'all' to list all available standards).",
                }
            },
            "required": ["name"],
        },
    },
    {
        "name": "trellis_rca",
        "description": "Run the Trellis 9-Step Fast Root Cause Analysis sequence (/pb-rca) with Tier 3 PII/PAN/secret redaction gate (F04), 3-hypothesis cap, 3-hop call-chain cap, and banking concurrency/lock checklist (F10).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symptom": {"type": "string", "description": "Observed failure symptom or error behavior."},
                "evidence": {"type": "string", "description": "Redacted stack trace, error code, or log snippet (no raw PANs or tokens)."},
                "suspect_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Up to 3 suspect file paths in the 3-hop call chain.",
                },
            },
            "required": ["symptom"],
        },
    },
    {
        "name": "trellis_spec",
        "description": "Generate a requirement-linked Trellis Specification (/pb-spec): Part A 4-section Micro-Spec for Class M tasks, or Part A + Part B 10-section Full Spec for Class L tasks (F12).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec_id": {"type": "string", "description": "Spec identifier, e.g., SPEC-042."},
                "title": {"type": "string", "description": "Short feature or bugfix title."},
                "problem": {"type": "string", "description": "Problem statement and business/user impact."},
                "task_class": {"type": "string", "enum": ["M", "L"], "description": "Task class ('M' for Micro-Spec, 'L' for Full Spec)."},
                "requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of testable requirements to assign [REQ-NNN-XX] IDs.",
                },
                "non_goals": {"type": "array", "items": {"type": "string"}},
                "affected_files": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["spec_id", "title", "problem", "requirements"],
        },
    },
    {
        "name": "trellis_enhance",
        "description": "Run the Trellis Complexity & Performance Analyzer (/pb-enhance): computes Little's Law concurrency VUs (L = lambda * W) and evaluates CPU, memory, and I/O + DB lock complexity (F10).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Target function, endpoint, or service."},
                "tps": {"type": "number", "description": "Target arrival rate (transactions/requests per second)."},
                "response_time_sec": {"type": "number", "description": "Target response time R in seconds."},
                "think_time_sec": {"type": "number", "description": "Average user think time Z in seconds."},
                "data_size_n": {"type": "integer", "description": "Expected dataset or batch cardinality N."},
                "current_behavior": {"type": "string", "description": "Summary of current algorithm and DB/network I/O pattern."},
                "mode": {"type": "string", "enum": ["analyze", "implement"], "description": "'analyze' (report-only) or 'implement' (with optimization checklist)."},
            },
            "required": ["target", "current_behavior"],
        },
    },
    {
        "name": "trellis_budget",
        "description": "Classify a task into Class S / M / L quota budget and enforce the F03 Tier 2/3 safety guard (1-file changes touching auth, validation, schema, SQL, or security auto-upgrade from Class S to Class M).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {"type": "string", "description": "Description of the planned change."},
                "file_count": {"type": "integer", "description": "Estimated number of files to modify."},
                "touches_tier2_or_tier3": {"type": "boolean", "description": "Explicit flag if touching Tier 2/3 domains."},
            },
            "required": ["task_description", "file_count"],
        },
    },
    {
        "name": "trellis_handoff",
        "description": "Generate a compact <=25-line session handoff packet (/pb-handoff) to preserve context across /clear or /compact boundaries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "current_state": {"type": "string"},
                "decisions_made": {"type": "array", "items": {"type": "string"}},
                "files_touched": {"type": "array", "items": {"type": "string"}},
                "next_step": {"type": "string"},
                "save_to_file": {"type": "string", "description": "Optional workspace-relative path to save the handoff markdown."},
            },
            "required": ["goal", "current_state", "next_step"],
        },
    },
    {
        "name": "trellis_review",
        "description": "Audit a git diff and commit message (/pb-review) against Story DoD, Testing Standard (blocks skipped/disabled tests), Security Baseline (blocks secrets/PANs), and Conventional Commits.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "diff_text": {"type": "string", "description": "Unified git diff text to inspect."},
                "commit_message": {"type": "string", "description": "Proposed git commit message."},
                "spec_req_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of [REQ-NNN-XX] IDs that must be covered in the diff.",
                },
            },
            "required": ["diff_text"],
        },
    },
    {
        "name": "trellis_doctor",
        "description": "Diagnose and auto-fix Antigravity IDE & Claude Code customization issues (missing YAML frontmatter in .agents/rules/*.md, deprecated .agents/workflows/*.md, skill line budgets).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_path": {"type": "string", "description": "Path to workspace root (defaults to current workspace)."},
                "auto_fix": {"type": "boolean", "description": "If true, automatically fixes missing rule YAML frontmatter and removes deprecated workflows."},
            },
        },
    },
]
