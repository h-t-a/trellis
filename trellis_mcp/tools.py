"""Implementation of the 8 callable Trellis MCP tools ([REQ-MCP-02]).

Each tool returns a standard MCP CallToolResult dictionary:
    {"content": [{"type": "text", "text": "..."}], "isError": False}
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from trellis_mcp.identity import resolve_approver_from_args

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
    "data-classification": "docs/standards/data-classification.md",
    "documentation-standard": "docs/standards/documentation-standard.md",
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

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[ -]?)?(?:\(?\d{3}\)?[ -]?)\d{3}[ -]?\d{4}(?!\d)")
_MM_PHONE_RE = re.compile(r"(?<!\d)(?:\+?959|09)\d{7,9}(?!\d)")
_MM_NRC_RE = re.compile(r"\b(?:1[0-4]|[1-9])/[A-Za-z]{3,16}\([NCEPncep]\)\d{6}\b")
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
_RESTRICTED_KEYWORDS = ("password", "passwd", "client_secret", "private key", "api_key", "apikey", "secret")
_CONFIDENTIAL_KEYWORDS = ("customer", "pii", "salary", "balance", "ledger", "account number", "iban", "ssn", "national id")


def _luhn_valid(digits: str) -> bool:
    """Return True if a 13-19 digit string passes the Luhn check ([REQ-TRL-05])."""
    if not 13 <= len(digits) <= 19 or not digits.isdigit():
        return False
    total = 0
    for idx, ch in enumerate(reversed(digits)):
        val = int(ch)
        if idx % 2 == 1:
            val *= 2
            if val > 9:
                val -= 9
        total += val
    return total % 10 == 0


def wrap_untrusted_context(content: str, source: str = "external") -> str:
    """Wrap external or retrieved text in escaped <untrusted_context> boundaries ([REQ-TRL-05])."""
    safe_source = re.sub(r"[^a-zA-Z0-9._:/-]", "_", source or "external")[:64]
    sanitized = re.sub(r"</?untrusted_context[^>]*>", "[TAG_STRIPPED]", content, flags=re.IGNORECASE)
    return (
        f'<untrusted_context source="{safe_source}" trust="untrusted">\n'
        f"{sanitized}\n"
        "</untrusted_context>"
    )


def _ok(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": False}


def _err(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": True}


def _is_within_root(
    root: Path, candidate: Path, *, allow_target_symlink: bool = False
) -> bool:
    """Return True iff `candidate` resolves strictly inside `root` without sibling or symlink escape ([REQ-TRL-19])."""
    try:
        resolved_root = root.resolve()
        resolved_candidate = candidate.resolve()
        resolved_candidate.relative_to(resolved_root)
    except (OSError, ValueError):
        return False

    if not allow_target_symlink:
        try:
            if candidate.is_symlink():
                return False
        except OSError:
            return False

    try:
        rel_parts = candidate.relative_to(root).parts
    except ValueError:
        try:
            rel_parts = candidate.relative_to(resolved_root).parts
        except ValueError:
            rel_parts = ()

    probe = resolved_root
    for part in rel_parts:
        if part in ("", "."):
            continue
        if part == "..":
            probe = probe.parent
            try:
                probe.resolve().relative_to(resolved_root)
            except (OSError, ValueError):
                return False
            continue
        probe = probe / part
        try:
            if probe.is_symlink():
                probe.resolve().relative_to(resolved_root)
                if not allow_target_symlink:
                    return False
        except (OSError, ValueError):
            return False

    return True


def read_bundled_text(rel_path: str, workspace_root: Path | None = None) -> str | None:
    """Read a bundled markdown/resource file from disk or from a standalone .pyz zip archive ([REQ-MCP-09])."""
    norm_rel = rel_path.replace("\\", "/").lstrip("/")
    for base in (workspace_root, PACKAGE_ROOT):
        if base is not None and base.is_dir():
            candidate = base / norm_rel
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        if base is not None and base.is_file() and zipfile.is_zipfile(base):
            with zipfile.ZipFile(base, "r") as zf:
                if norm_rel in zf.namelist():
                    return zf.read(norm_rel).decode("utf-8")
    return None


def list_bundled_skills(workspace_root: Path | None = None) -> dict[str, str]:
    """Return a map of `{skill_name: skill_markdown}` from disk or from a standalone .pyz zip archive ([REQ-MCP-09])."""
    skills: dict[str, str] = {}
    for base in (workspace_root, PACKAGE_ROOT):
        if base is not None and base.is_dir():
            canonical_dir = base / "skills"
            if canonical_dir.is_dir():
                for skill_md in sorted(canonical_dir.glob("*/*/SKILL.md")):
                    skills[skill_md.parent.name] = skill_md.read_text(encoding="utf-8")
                if skills:
                    return skills
            skills_dir = base / ".agents" / "skills"
            if skills_dir.is_dir():
                for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
                    skills[skill_md.parent.name] = skill_md.read_text(encoding="utf-8")
                if skills:
                    return skills
        if base is not None and base.is_file() and zipfile.is_zipfile(base):
            with zipfile.ZipFile(base, "r") as zf:
                for entry_name in sorted(zf.namelist()):
                    parts = entry_name.split("/")
                    if len(parts) == 4 and parts[0] == "skills" and parts[3] == "SKILL.md":
                        skills[parts[2]] = zf.read(entry_name).decode("utf-8")
                    elif len(parts) == 4 and parts[0] == ".agents" and parts[1] == "skills" and parts[3] == "SKILL.md":
                        skills[parts[2]] = zf.read(entry_name).decode("utf-8")
            if skills:
                return skills
    return skills


def _resolve_root(workspace_root: Path | None) -> Path:
    if workspace_root:
        return workspace_root
    return PACKAGE_ROOT


STANDARDS_MANIFEST = "docs/standards/standards.json"
DEFAULT_STANDARD_VERSION = "0.1"
CACHE_DIRNAME = ".trellis_cache"


def _standard_manifest(root: Path) -> dict[str, dict[str, Any]]:
    """Load `docs/standards/standards.json`, falling back to the built-in map."""
    data: dict[str, Any] = {}
    raw: str | None = None
    if root.is_dir():
        candidate = root / STANDARDS_MANIFEST
        if candidate.is_file():
            try:
                raw = candidate.read_text(encoding="utf-8")
            except OSError:
                raw = None
    else:
        raw = read_bundled_text(STANDARDS_MANIFEST, workspace_root=root)
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                data = parsed
        except (ValueError, TypeError):
            data = {}

    standards = data.get("standards")
    if isinstance(standards, dict) and standards:
        return {str(name): entry for name, entry in standards.items() if isinstance(entry, dict)}

    return {
        name: {
            "version": DEFAULT_STANDARD_VERSION,
            "path": rel_path,
            "versions": {DEFAULT_STANDARD_VERSION: rel_path},
        }
        for name, rel_path in STANDARD_FILE_MAP.items()
    }


def _standard_cache_dir(root: Path) -> Path:
    base = root.parent if root.is_file() else root
    return base / CACHE_DIRNAME / "standards"


def _standard_signing_key(explicit: str | None = None) -> str | None:
    return (
        explicit
        or os.environ.get("TRELLIS_STANDARD_SIGNING_KEY")
        or os.environ.get("TRELLIS_BUNDLE_SIGNING_KEY")
        or None
    )


def _sign_text(text: str, key: str | None) -> str | None:
    if not key:
        return None
    return hmac.new(key.encode("utf-8"), text.encode("utf-8"), hashlib.sha256).hexdigest()


def _write_standard_cache(cache_path: Path, content: str, digest: str) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(content, encoding="utf-8")
        cache_path.with_suffix(".sha256").write_text(digest + "\n", encoding="utf-8")
    except OSError:
        pass


def _load_standard(
    name: str,
    root: Path,
    version: str | None = None,
    offline: bool = False,
    *,
    write_cache: bool = True,
) -> dict[str, Any]:
    """Resolve a standard by name/version, preferring disk/bundle then the offline cache."""
    manifest = _standard_manifest(root)
    entry = manifest.get(name)
    if not entry:
        raise KeyError(
            f"Unknown standard '{name}'. Available: {', '.join(sorted(manifest.keys()))}"
        )

    resolved_version = str(version).strip() if version else str(
        entry.get("version") or DEFAULT_STANDARD_VERSION
    )
    versions = entry.get("versions") if isinstance(entry.get("versions"), dict) else {}
    rel_path = versions.get(resolved_version)
    if rel_path is None and resolved_version == str(entry.get("version")):
        rel_path = entry.get("path")
    if not rel_path:
        available = ", ".join(sorted(versions.keys())) or str(entry.get("version"))
        raise ValueError(
            f"Version '{resolved_version}' not available for '{name}'. Available: {available}"
        )

    cache_dir = _standard_cache_dir(root)
    cache_path = cache_dir / f"{name}@{resolved_version}.md"
    if not _is_within_root(cache_dir, cache_path):
        raise ValueError("Invalid standard name or version path.")
    if root.is_dir() and not _is_within_root(root, root / str(rel_path)):
        raise ValueError(f"Standard path escapes workspace root: {rel_path}")
    content: str | None = None
    source = "bundled"

    if offline:
        if cache_path.is_file():
            content = cache_path.read_text(encoding="utf-8")
            source = "cache"
        else:
            raise FileNotFoundError(
                f"No offline cache for '{name}' version '{resolved_version}'. Run --sync-cache first."
            )
    else:
        content = read_bundled_text(str(rel_path), workspace_root=root)
        if content is None:
            if cache_path.is_file():
                content = cache_path.read_text(encoding="utf-8")
                source = "cache"
            else:
                raise FileNotFoundError(f"Standard file not found: {rel_path}")

    if content is None:
        raise FileNotFoundError(f"Standard file not found: {rel_path}")

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    sidecar = cache_path.with_suffix(".sha256")
    if source == "cache" and sidecar.is_file():
        try:
            expected_digest = sidecar.read_text(encoding="utf-8").strip()
        except OSError:
            expected_digest = ""
        if expected_digest and not hmac.compare_digest(expected_digest, digest):
            raise ValueError(
                f"Offline cache integrity check failed for '{name}' version '{resolved_version}'."
            )
    if write_cache and not offline:
        _write_standard_cache(cache_path, content, digest)

    return {
        "content": content,
        "path": str(rel_path),
        "version": resolved_version,
        "source": source,
        "sha256": digest,
    }


def _standard_metadata(
    name: str, loaded: dict[str, Any], signing_key: str | None = None
) -> dict[str, Any]:
    signature = _sign_text(loaded["content"], _standard_signing_key(signing_key))
    return {
        "name": name,
        "version": loaded["version"],
        "path": loaded["path"],
        "source": loaded["source"],
        "sha256": loaded["sha256"],
        "signed": signature is not None,
        "signature_alg": "HMAC-SHA256" if signature else None,
        "signature": signature,
    }


def tool_trellis_get_standard(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Return the authoritative Trellis standard or template by name and optional version."""
    name = str(args.get("name", "all")).strip().lower()
    version = args.get("version")
    offline = bool(args.get("offline", False))
    root = _resolve_root(workspace_root)
    manifest = _standard_manifest(root)

    if name in ("all", "list", ""):
        lines = ["# Available Trellis Standards & Templates", ""]
        for key in sorted(manifest.keys()):
            entry = manifest[key]
            versions = entry.get("versions") if isinstance(entry.get("versions"), dict) else {}
            available = ", ".join(sorted(versions.keys())) or str(entry.get("version"))
            lines.append(
                f"- `{key}` v{entry.get('version')} (available: {available}) -> `{entry.get('path')}`"
            )
        lines.extend(
            [
                "",
                "Tip: request a historical version with "
                '`{"name": "<standard>", "version": "<x.y>"}`.',
            ]
        )
        return _ok("\n".join(lines))

    if name not in manifest:
        return _err(
            f"Unknown standard '{name}'. Available: {', '.join(sorted(manifest.keys()))}"
        )

    remote_mode = bool(args.get("_remote_mode", False))
    try:
        loaded = _load_standard(
            name,
            root,
            version=str(version) if version else None,
            offline=offline,
            write_cache=not remote_mode,
        )
    except (KeyError, ValueError, FileNotFoundError) as exc:
        return _err(str(exc))

    result = _ok(loaded["content"])
    result["metadata"] = _standard_metadata(name, loaded)
    return result


def tool_trellis_verify(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Verify the SHA-256 hash and optional HMAC signature of a retrieved standard ([REQ-P3-05])."""
    name = str(args.get("name", "")).strip().lower()
    if not name:
        return _err("Provide the standard 'name' to verify.")
    root = _resolve_root(workspace_root)
    version = args.get("version")
    signing_key = args.get("signing_key")

    remote_mode = bool(args.get("_remote_mode", False))
    try:
        loaded = _load_standard(
            name,
            root,
            version=str(version) if version else None,
            write_cache=not remote_mode,
        )
    except (KeyError, ValueError, FileNotFoundError) as exc:
        return _err(str(exc))

    expected_sha = str(args.get("expected_sha256", "")).strip().lower() or None
    expected_sig = str(args.get("expected_signature", "")).strip().lower() or None
    actual_sig = _sign_text(loaded["content"], _standard_signing_key(signing_key))
    checks: list[str] = []
    ok = True

    if expected_sha:
        match = hmac.compare_digest(expected_sha, loaded["sha256"])
        ok = ok and match
        checks.append(f"sha256: {'MATCH' if match else 'MISMATCH'}")
    if expected_sig:
        if actual_sig is None:
            ok = False
            checks.append("signature: NO SIGNING KEY CONFIGURED")
        else:
            match = hmac.compare_digest(expected_sig, actual_sig)
            ok = ok and match
            checks.append(f"signature: {'MATCH' if match else 'MISMATCH'}")
    if not expected_sha and not expected_sig:
        checks.append("No expected hash/signature supplied; reporting computed provenance only.")

    status = "VALID" if ok else "INVALID"
    if not expected_sha and not expected_sig:
        status = "HASHED"

    lines = [
        f"# Trellis Provenance Verification: {name}",
        "",
        f"- Status: **{status}**",
        f"- Version: `{loaded['version']}`",
        f"- Source: `{loaded['source']}`",
        f"- SHA-256: `{loaded['sha256']}`",
        f"- Signed: `{bool(actual_sig)}`"
        + (f" (`HMAC-SHA256: {actual_sig}`)" if actual_sig else ""),
        "",
        "## Checks",
        *[f"- {item}" for item in checks],
    ]
    result = _ok("\n".join(lines))
    result["metadata"] = {
        "name": name,
        "version": loaded["version"],
        "sha256": loaded["sha256"],
        "signature": actual_sig,
        "valid": ok,
        "status": status,
    }
    if status == "INVALID":
        result["isError"] = True
    return result


def tool_trellis_analytics(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Report token usage, cost, and quota utilization from a local usage ledger ([REQ-P3-04])."""
    root = _resolve_root(workspace_root)
    base = root.parent if root.is_file() else root
    usage_arg = args.get("usage_file")
    if usage_arg:
        usage_candidate = base / str(usage_arg)
        if not _is_within_root(base, usage_candidate):
            return _err("`usage_file` must stay within the workspace root ([REQ-TRL-19]).")
        usage_path = usage_candidate.resolve()
    else:
        usage_path = base / ".trellis_usage.json"
    budget = int(args.get("budget_tokens") or 0)
    rate = float(args.get("cost_per_1k_tokens") or 0.0)
    period_days = args.get("period_days")

    entries: list[dict[str, Any]] = []
    if usage_path.is_file():
        try:
            raw = json.loads(usage_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                raw = raw.get("entries", [])
            if isinstance(raw, list):
                entries = [e for e in raw if isinstance(e, dict)]
        except (OSError, ValueError):
            return _err(f"Could not parse usage ledger: {usage_path.name}")

    cutoff: datetime | None = None
    if period_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=float(period_days))

    per_key: dict[str, dict[str, Any]] = {}
    per_tool: dict[str, int] = {}
    total_in = total_out = 0
    total_cost = 0.0

    for entry in entries:
        if cutoff is not None:
            stamp = entry.get("timestamp")
            try:
                parsed = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                if parsed < cutoff:
                    continue
            except (ValueError, TypeError):
                pass
        tokens_in = int(entry.get("input_tokens") or 0)
        tokens_out = int(entry.get("output_tokens") or 0)
        tool = str(entry.get("tool") or "unknown")
        label = str(entry.get("label") or entry.get("key_id") or "unattributed")
        cost = entry.get("cost_usd")
        if cost is None:
            cost = ((tokens_in + tokens_out) / 1000.0) * rate
        cost = float(cost)

        total_in += tokens_in
        total_out += tokens_out
        total_cost += cost
        bucket = per_key.setdefault(
            label, {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
        )
        bucket["requests"] += 1
        bucket["input_tokens"] += tokens_in
        bucket["output_tokens"] += tokens_out
        bucket["cost_usd"] += cost
        per_tool[tool] = per_tool.get(tool, 0) + 1

    used = total_in + total_out
    utilization = (used / budget * 100.0) if budget > 0 else None
    if budget and used >= budget:
        verdict = "EXCEEDED"
    elif utilization is not None and utilization >= 80.0:
        verdict = "WARN"
    else:
        verdict = "OK"
    if not usage_path.is_file():
        verdict = "NO_DATA"

    lines = [
        "# Trellis Cost & Quota Analytics",
        "",
        f"- Ledger: `{usage_path}` ({'found' if usage_path.is_file() else 'missing'})",
        f"- Entries: {len(entries)}",
        f"- Total tokens: {used} (input {total_in} / output {total_out})",
        f"- Estimated cost: ${total_cost:.4f}"
        + (f" (@ ${rate:.4f}/1K tokens)" if rate else ""),
        f"- Budget utilization: {f'{utilization:.1f}%' if utilization is not None else 'not configured'}",
        f"- Verdict: **{verdict}**",
    ]
    if per_key:
        lines.extend(["", "## Per Key / Team"])
        for label, bucket in sorted(per_key.items()):
            lines.append(
                f"- `{label}`: {bucket['requests']} requests, "
                f"{bucket['input_tokens'] + bucket['output_tokens']} tokens, "
                f"${bucket['cost_usd']:.4f}"
            )
    if per_tool:
        lines.extend(["", "## Per Tool"])
        for tool, count in sorted(per_tool.items()):
            lines.append(f"- `{tool}`: {count}")

    result = _ok("\n".join(lines))
    result["metadata"] = {
        "entries": len(entries),
        "total_tokens": used,
        "cost_usd": round(total_cost, 6),
        "budget_tokens": budget,
        "utilization_pct": round(utilization, 2) if utilization is not None else None,
        "verdict": verdict,
    }
    return result


def _is_placeholder_value(value: str) -> bool:
    lowered = value.lower()
    if lowered.startswith("bearer "):
        token = lowered[len("bearer ") :]
        if token in ("auth", "token", "header", "key", "scheme", "bearer"):
            return True
        if len(token) < 16 and not any(ch.isdigit() for ch in token):
            return True
    return any(marker in value for marker in ("<", ">", "$", "{", "}", "...", "xxxx")) or any(
        word in lowered for word in ("redacted", "example", "placeholder", "dummy", "your_", "api_key", "token")
    )


def _scan_redaction_violations(text: str, ignore_placeholders: bool = False) -> list[str]:
    violations: list[str] = []
    for pan_match in _PAN_PATTERN.finditer(text):
        raw_pan = pan_match.group(0)
        if ignore_placeholders and _is_placeholder_value(raw_pan):
            continue
        digits = re.sub(r"[^0-9]", "", raw_pan)
        if _luhn_valid(digits):
            violations.append("Potential unredacted Luhn-valid 13-19 digit PAN / card number")
            break
    for pat in _SECRET_PATTERNS:
        match = pat.search(text)
        if match and not (ignore_placeholders and _is_placeholder_value(match.group(0))):
            violations.append(f"Credential / secret token pattern matched (`{pat.pattern[:32]}...`)")
    jwt_match = _JWT_RE.search(text)
    if jwt_match and not (ignore_placeholders and _is_placeholder_value(jwt_match.group(0))):
        violations.append("JWT bearer token pattern detected")
    nrc_match = _MM_NRC_RE.search(text)
    if nrc_match and not (ignore_placeholders and _is_placeholder_value(nrc_match.group(0))):
        violations.append("Regional national ID (Myanmar NRC) pattern detected")
    if not ignore_placeholders:
        if _MM_PHONE_RE.search(text):
            violations.append("Regional phone number pattern detected")
        if _IBAN_RE.search(text):
            violations.append("IBAN / bank account pattern detected")
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

    similar_section = ""
    try:
        from .knowledge import find_similar_rcas

        prior = find_similar_rcas(symptom, workspace_root=workspace_root, top_k=3)
        if prior:
            bullets = "\n".join(
                f"- `{item['id']}` (cosine={item['cosine']}): {item['excerpt']}"
                for item in prior
            )
            similar_section = f"\n## 5. Similar Prior RCAs (`[REQ-TRL-10]`)\n{bullets}\n"
    except Exception:
        similar_section = ""

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
{similar_section}"""
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
    author = resolve_approver_from_args(args, workspace_root, keys=("author", "approver", "reviewer"))
    approver = resolve_approver_from_args(args, workspace_root, keys=("approver", "reviewer", "author"))

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

- **Author:** `{author.name}` (`{author.source}`)
- **Task Class:** `Class {task_class}`
- **Status:** `DRAFT`
- **Human Approval:** [ ] Approved by `{approver.name}` (`{approver.source}`) on `[YYYY-MM-DD]`

---

## Part A: Core Micro-Spec (Mandatory for Class M and Class L)

### 1. Problem, Goal & Non-Goals
- **Problem Statement:** {problem}
- **Non-Goals (Out of Scope):**
{non_goal_bullets}

### 2. Numbered Requirements & Testable Acceptance Criteria (`[REQ-{spec_num}-XX]`)
| Req ID | Requirement | Acceptance Criteria (`Given / When / Then`) |
| :--- | :--- | :--- |
{req_table}

### 3. Security, Privacy & AI-Boundary Check
- [ ] **No Tier 3 Violations:** No production secrets, unredacted customer PII/PAN data, production DB mutations, or financial/ledger sign-off delegated to AI.
- **Tier 2 Human Review Areas Touched:** `[Auth / Input Validation / DB Schema / API Contract / CI-CD / None]`

### 4. Traceability & Test Plan
| File Path | Action (`Create` / `Modify`) | Linked `[REQ-ID]` | Planned Test Case |
| :--- | :--- | :--- | :--- |
{file_rows}
"""

    if task_class == "L":
        spec_md += f"""
---

## Part B: Extended Sections (Mandatory for Class L Only)

### 5. Context & Architecture Background
- **System Dependencies & ADRs:** Document upstream/downstream boundaries, data model/schema impact, and linked ADRs.

### 6. Edge Cases, Concurrency & Failure Modes
- **Idempotency & Retries:** Document duplicate request handling (`X-Idempotency-Key`), API contract errors, and timeout behavior.
- **Concurrency & Locking:** Specify transaction isolation level, lock ordering, and boundary inputs.

### 7. Performance SLA & Complexity Constraints
- **Target Throughput & Latency:** p95 < 500ms, p99 < 1500ms, error rate < 0.1%.
- **Algorithmic & I/O Bounds:** Time `O(N)`, Space `O(N)`, DB Queries `O(1)` batched.

### 8. Design Notes & Alternatives Considered
- **Chosen Approach & Security Review:** Document input validation, AuthN/AuthZ object-level checks, audit logging with zero PII/secret leakage, and rejected alternatives.

### 9. Rollout, Migration & Rollback Plan
- **Database / Config Migrations:** Document backward-compatible forward migrations and dual-read/write safety.
- **Feature Flag / Canary & Rollback:** Gradual rollout with automated rollback trigger on p99 or 5xx spike.

### 10. Open Questions & Human Sign-Off
- [ ] Confirm cross-service SLA and downstream rate limits before execution.
- [ ] Approved by `{approver.name}` (`{approver.source}`) on `[YYYY-MM-DD]`
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
    if save_to_file:
        if bool(args.get("_remote_mode", False)):
            return _err("`save_to_file` is disabled in remote HTTP mode ([REQ-TRL-17]).")
        if workspace_root:
            candidate = workspace_root / str(save_to_file)
            if not _is_within_root(workspace_root, candidate, allow_target_symlink=False):
                return _err("`save_to_file` must stay within the workspace root ([REQ-TRL-19]).")
            out_path = candidate.resolve()
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
    reviewer = resolve_approver_from_args(args, workspace_root, keys=("reviewer", "approver", "author"))
    findings_block = (
        "\n".join(f"- {item}" for item in issues)
        if issues
        else "- All automated DoD, Security, Testing, and Commit checks passed."
    )

    return _ok(
        f"""# Trellis Pre-PR Code Review Report

- **Verdict:** **{verdict}**
- **Reviewer / Approver:** `{reviewer.name}` (`{reviewer.source}`)
- **Checked Spec IDs:** `{', '.join(spec_req_ids) if spec_req_ids else 'None specified'}`

## Findings
{findings_block}
"""
    )


def _strip_fenced_code_blocks(md_text: str) -> str:
    """Remove fenced code blocks (``` or ~~~) while preserving line structure for link/heading checks."""
    kept: list[str] = []
    in_fence = False
    fence_char = ""
    for line in md_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
            elif marker[0] == fence_char:
                in_fence = False
                fence_char = ""
            continue
        if not in_fence:
            kept.append(line)
    return "\n".join(kept)


def _slugify_heading(heading_text: str) -> str:
    """Generate a GitHub Flavored Markdown heading anchor slug."""
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading_text)
    cleaned = re.sub(r"[`*_~]", "", cleaned).strip().lower()
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)
    return cleaned.replace(" ", "-")


def _extract_markdown_anchors(md_text: str) -> set[str]:
    """Collect GFM heading slugs outside fenced code blocks."""
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for line in _strip_fenced_code_blocks(md_text).splitlines():
        match = re.match(r"^\s*#{1,6}\s+(.+?)(?:\s+#+\s*)?$", line)
        if not match:
            continue
        base = _slugify_heading(match.group(1))
        if not base:
            continue
        seen = counts.get(base, 0)
        slug = base if seen == 0 else f"{base}-{seen}"
        counts[base] = seen + 1
        anchors.add(slug)
    return anchors


def tool_trellis_doctor(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Audit and optionally auto-fix workspace rules, skills, and line budgets (F01, F02, [REQ-MCP-07])."""
    auto_fix = bool(args.get("auto_fix", False))
    dry_run = bool(args.get("dry_run", False))
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
            if norm.endswith("SKILL.md") and len(content.splitlines()) > 40:
                findings.append(f"Skill `{norm}` exceeds <=40 line budget")
            if norm.endswith(("CLAUDE.md", "GEMINI.md")) and len(content.splitlines()) >= 200:
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

    remote_mode = bool(args.get("_remote_mode", False))
    raw_path = args.get("workspace_path")
    if remote_mode:
        if auto_fix:
            return _err("`auto_fix` is disabled in remote HTTP mode ([REQ-TRL-17]).")
        base_root = _resolve_root(workspace_root)
        if raw_path:
            candidate = base_root / str(raw_path)
            if not _is_within_root(base_root, candidate):
                return _err(
                    "`workspace_path` must stay within the server workspace root in remote mode ([REQ-TRL-17, REQ-TRL-19])."
                )
            root = candidate.resolve()
        else:
            root = base_root
    else:
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
                if auto_fix and dry_run:
                    fixes_applied.append(
                        f"Would fix YAML frontmatter in `.agents/rules/{rule_file.name}` (dry run, no write)"
                    )
                elif auto_fix:
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
            if auto_fix and dry_run:
                fixes_applied.append(
                    f"Would remove {len(legacy_files)} deprecated `.agents/workflows/*.md` file(s) (dry run, no write)"
                )
            elif auto_fix:
                for lf in legacy_files:
                    lf.unlink()
                fixes_applied.append(f"Fixed: Removed {len(legacy_files)} deprecated `.agents/workflows/*.md` file(s)")

    # 3. Check SKILL.md line budget (<=40 lines), frontmatter metadata, and standards links ([REQ-TRL-32])
    skill_candidates: list[Path] = []
    canonical_skills = root / "skills"
    if canonical_skills.is_dir():
        skill_candidates.extend(canonical_skills.glob("*/*/SKILL.md"))
    agents_skills = root / ".agents" / "skills"
    if agents_skills.is_dir():
        for sk_file in agents_skills.glob("*/SKILL.md"):
            if sk_file not in skill_candidates:
                skill_candidates.append(sk_file)

    for skill_md in sorted(set(skill_candidates)):
        rel = skill_md.relative_to(root).as_posix()
        try:
            content = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = content.splitlines()
        if len(lines) > 40:
            findings.append(
                f"Skill `{rel}` is {len(lines)} lines (exceeds <=40 line budget)"
            )
        # Check frontmatter
        if not (content.startswith("---\n") and "\n---\n" in content[4:]):
            findings.append(f"Skill `{rel}` missing YAML frontmatter (`---`)")
            continue
        fm_part = content[4:content.find("\n---\n", 4)]
        if "\nname:" not in ("\n" + fm_part):
            findings.append(f"Skill `{rel}` missing `name` in frontmatter")
        if "\ndescription:" not in ("\n" + fm_part):
            findings.append(f"Skill `{rel}` missing `description` in frontmatter")
        else:
            desc_match = re.search(r"^description:\s*(.*?)$", fm_part, re.MULTILINE)
            if desc_match:
                desc = desc_match.group(1).strip()
                if len(desc) > 180:
                    findings.append(f"Skill `{rel}` description exceeds 180 chars ({len(desc)} chars)")
                if "Use when" not in desc or "Not for" not in desc:
                    findings.append(f"Skill `{rel}` description must include both 'Use when' and 'Not for' phrases")
        if "\nmetadata:" not in ("\n" + fm_part):
            findings.append(f"Skill `{rel}` missing `metadata` block in frontmatter")
        else:
            meta_match = re.search(r"^metadata:\s*\{([^}]+)\}", fm_part, re.MULTILINE)
            if meta_match:
                m_body = meta_match.group(1)
                stds_match = re.search(r"standards:\s*\[([^\]]*)\]", m_body)
                if stds_match:
                    raw_stds = [s.strip().strip("'\"") for s in stds_match.group(1).split(",") if s.strip()]
                    for std in raw_stds:
                        std_path = root / "docs" / "standards" / f"{std}.md"
                        if not std_path.is_file():
                            findings.append(f"Skill `{rel}` references non-existent standard `{std}` (missing docs/standards/{std}.md)")

    # 3b. Validate skills/skills.index.json manifest ([REQ-TRL-31, REQ-TRL-32])
    index_path = root / "skills" / "skills.index.json"
    if index_path.is_file():
        try:
            idx_data = json.loads(index_path.read_text(encoding="utf-8"))
            all_skills = idx_data.get("skills", [])
            seen_triggers: dict[str, str] = {}
            for sk in all_skills:
                sk_id = sk.get("id", "unknown")
                for tr in sk.get("triggers", []):
                    clean_tr = tr.strip().lower()
                    if clean_tr in seen_triggers:
                        findings.append(f"Duplicate trigger `{clean_tr}` between `{seen_triggers[clean_tr]}` and `{sk_id}`")
                    else:
                        seen_triggers[clean_tr] = sk_id
        except Exception as exc:
            findings.append(f"Invalid skills index manifest `skills/skills.index.json`: {exc}")

    # 4. Check CLAUDE.md and GEMINI.md line budgets (<200 lines)
    for ctx_name in ("CLAUDE.md", "GEMINI.md"):
        ctx_md = root / ctx_name
        if ctx_md.exists():
            c_lines = ctx_md.read_text(encoding="utf-8").splitlines()
            if len(c_lines) >= 200:
                findings.append(f"`{ctx_name}` is {len(c_lines)} lines (exceeds <200 line budget)")

    # 5. Validate JSON configuration files
    for rel in (".mcp.json", ".agents/mcp_config.json", ".agents/skills.json", ".claude/settings.json", "docs/standards/ai-bom.json"):
        cfg_path = root / rel
        if cfg_path.is_file():
            try:
                json.loads(cfg_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                findings.append(f"Invalid JSON in `{rel}`: {exc}")

    # 5b. Audit ai-bom.json catalog freshness & deprecations ([REQ-TRL-28])
    aibom_path = root / "docs" / "standards" / "ai-bom.json"
    if aibom_path.is_file():
        try:
            import datetime
            aibom_data = json.loads(aibom_path.read_text(encoding="utf-8"))
            today = datetime.date.today()
            for m in aibom_data.get("models", []):
                mid = m.get("id", "unknown")
                dep = m.get("deprecation")
                if dep:
                    try:
                        dep_d = datetime.date.fromisoformat(str(dep))
                        if dep_d <= today:
                            findings.append(f"Model `{mid}` in `ai-bom.json` is deprecated as of {dep_d}")
                    except ValueError:
                        pass
                last_v = m.get("last_verified")
                if not last_v:
                    findings.append(f"Model `{mid}` in `ai-bom.json` is missing `last_verified` date")
                else:
                    try:
                        v_d = datetime.date.fromisoformat(str(last_v))
                        if (today - v_d).days > 90:
                            findings.append(f"Model `{mid}` in `ai-bom.json` has not been verified in >90 days (last verified {v_d})")
                    except ValueError:
                        pass
        except Exception as exc:
            findings.append(f"Could not audit `docs/standards/ai-bom.json`: {exc}")

    # 6. Check skill mirror parity (.agents/skills and .claude/skills)
    if canonical_skills.is_dir():
        for pack_dir in sorted(canonical_skills.iterdir()):
            if not pack_dir.is_dir() or pack_dir.name.startswith("."):
                continue
            for skill_md in sorted(pack_dir.glob("*/SKILL.md")):
                name = skill_md.parent.name
                ag_mirror = root / ".agents" / "skills" / name / "SKILL.md"
                cl_mirror = root / ".claude" / "skills" / name / "SKILL.md"
                if not ag_mirror.is_file():
                    findings.append(f"Skill `{name}` is not mirrored to `.agents/skills/{name}/SKILL.md`")
                if not cl_mirror.is_file():
                    findings.append(f"Skill `{name}` is not mirrored to `.claude/skills/{name}/SKILL.md`")
    elif agents_skills.exists():
        for skill_md in sorted(agents_skills.glob("*/SKILL.md")):
            name = skill_md.parent.name
            mirror = root / ".claude" / "skills" / name / "SKILL.md"
            if not mirror.is_file():
                findings.append(
                    f"Skill `{name}` is not mirrored to `.claude/skills/{name}/SKILL.md`"
                )

    # 7. Detect broken relative Markdown links and local #heading anchors
    link_re = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
    md_files: list[Path] = []
    for pattern in (
        "README.md",
        "CLAUDE.md",
        "GEMINI.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "SECURITY.md",
        "docs/**/*.md",
        "templates/*.md",
        ".agents/**/*.md",
        ".claude/**/*.md",
    ):
        md_files.extend(root.glob(pattern))
    checked_links: set[str] = set()
    anchor_cache: dict[Path, set[str]] = {}
    for md_path in sorted(set(md_files)):
        if not md_path.is_file():
            continue
        try:
            md_text = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        scan_text = _strip_fenced_code_blocks(md_text)
        rel_src = md_path.relative_to(root).as_posix()
        for raw_target in link_re.findall(scan_text):
            raw_clean = raw_target.strip()
            if not raw_clean or raw_clean.startswith(("http://", "https://", "mailto:", "@", "<")):
                continue
            if "{" in raw_clean or "}" in raw_clean:
                continue
            if "#" in raw_clean:
                target, anchor = raw_clean.split("#", 1)
                target = target.strip()
                anchor = anchor.strip()
            else:
                target, anchor = raw_clean, ""
            key = f"{md_path.as_posix()}::{raw_clean}"
            if key in checked_links:
                continue
            checked_links.add(key)
            if not target:
                resolved = md_path.resolve()
            else:
                resolved = (md_path.parent / target).resolve()
                if not resolved.exists():
                    findings.append(f"Broken relative link in `{rel_src}` -> `{target}`")
                    continue
            if anchor and resolved.is_file() and resolved.suffix.lower() == ".md":
                if resolved not in anchor_cache:
                    try:
                        anchor_cache[resolved] = _extract_markdown_anchors(
                            resolved.read_text(encoding="utf-8")
                        )
                    except (OSError, UnicodeDecodeError):
                        anchor_cache[resolved] = set()
                if anchor.lower() not in anchor_cache[resolved]:
                    findings.append(f"Broken anchor link in `{rel_src}` -> `{raw_clean}`")

    # 8. Informational DRAFT/TODO markers (never affects status)
    marker_lines: list[str] = []
    marker_files = [root / "CLAUDE.md", *sorted((root / "docs" / "standards").glob("*.md"))]
    for md_path in marker_files:
        if not md_path.is_file():
            continue
        try:
            md_text = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        drafts = len(re.findall(r"\[DRAFT\]", md_text))
        todos = len(re.findall(r"\bTODO\b", md_text))
        if drafts or todos:
            marker_lines.append(
                f"- `{md_path.relative_to(root).as_posix()}`: {drafts} `[DRAFT]`, {todos} `TODO`"
            )
    markers_text = "\n".join(marker_lines) if marker_lines else "- None"
    markers_hint = (
        "- Human sign-off is required before finalizing `[DRAFT]` standards (`Tier 3`)."
        if marker_lines
        else "- No draft markers detected."
    )

    if dry_run and fixes_applied:
        status = "DRY_RUN"
    elif not findings or (auto_fix and not dry_run and fixes_applied):
        status = "HEALTHY"
    else:
        status = "ISSUES_FOUND"
    findings_text = "\n".join(f"- {f}" for f in findings) if findings else "- Zero configuration issues detected."
    fixes_text = "\n".join(f"- {fx}" for fx in fixes_applied) if fixes_applied else "- None"

    return _ok(
        f"""# Trellis Workspace Doctor Report (`[REQ-MCP-02]`)

- **Workspace:** `{root}`
- **Status:** **{status}**
- **Dry Run:** `{dry_run and auto_fix}`

## Findings
{findings_text}

## Auto-Fixes Applied
{fixes_text}

## Draft & TODO Markers (informational)
{markers_text}
{markers_hint}
"""
    )


def _slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return (slug or "case")[:limit]


def _workspace_root(workspace_root: Path | None) -> Path:
    return (workspace_root or PACKAGE_ROOT).resolve()


def tool_trellis_test(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Generate failing REQ-linked test skeletons for Python/TS/Java/C# ([REQ-P2-01])."""
    spec_id = str(args.get("spec_id", "SPEC-001")).strip().upper()
    title = str(args.get("title", "Untitled requirement")).strip()
    requirements: list[str] = list(args.get("requirements") or ["Define testable requirement"])
    language = str(args.get("language", "python")).strip().lower()
    test_file = str(args.get("test_file", "") or "").strip()

    digits = re.search(r"(\d+)", spec_id)
    spec_num = digits.group(1).zfill(3) if digits else "001"
    safe_title = title.replace('"""', "'''")

    req_ids: list[str] = []
    if language in ("python", "py", "unittest"):
        lines = [
            f'"""Red-phase tests for {spec_id}: {safe_title}',
            "",
            "Generated by trellis_test. Every test below MUST fail until the",
            "requirement is implemented (Red -> Green discipline).",
            '"""',
            "from __future__ import annotations",
            "",
            "import unittest",
            "",
            "",
            f"class TestSpec{spec_num}(unittest.TestCase):",
        ]
        for idx, req in enumerate(requirements, start=1):
            req_id = f"REQ-{spec_num}-{idx:02d}"
            req_ids.append(req_id)
            method = f"test_{req_id.lower().replace('-', '_')}_{_slugify(str(req))}"
            lines += [
                f"    def {method}(self) -> None:",
                f'        """[{req_id}] {str(req).replace(chr(34) * 3, chr(39) * 3)}"""',
                "        # Given:",
                "        ...",
                "        # When:",
                "        ...",
                "        # Then:",
                f'        self.fail("[{req_id}] not implemented yet (expected RED phase)")',
                "",
            ]
        code = "\n".join(lines)
    elif language in ("typescript", "ts", "javascript", "js", "jest"):
        lines = [
            f"// Red-phase tests for {spec_id}: {title}",
            f'describe("{spec_id}: {title}", () => {{',
        ]
        for idx, req in enumerate(requirements, start=1):
            req_id = f"REQ-{spec_num}-{idx:02d}"
            req_ids.append(req_id)
            lines += [
                f'  test("[{req_id}] {req}", () => {{',
                "    // Given / When / Then",
                "    // RED: replace with a real assertion once implemented.",
                "    expect(true).toBe(false);",
                "  });",
                "",
            ]
        lines.append("});")
        code = "\n".join(lines)
    elif language in ("java", "junit", "junit5"):
        lines = [
            "import static org.junit.jupiter.api.Assertions.fail;",
            "",
            "import org.junit.jupiter.api.Test;",
            "",
            f"class Spec{spec_num}Test {{",
        ]
        for idx, req in enumerate(requirements, start=1):
            req_id = f"REQ-{spec_num}-{idx:02d}"
            req_ids.append(req_id)
            method = f"req{spec_num}_{idx:02d}_{_slugify(str(req), 28)}"
            lines += [
                "    @Test",
                f"    void {method}() {{",
                f'        fail("[{req_id}] not implemented yet (expected RED phase)");',
                "    }",
                "",
            ]
        lines.append("}")
        code = "\n".join(lines)
    elif language in ("csharp", "cs", "c#", "xunit"):
        lines = [
            "using Xunit;",
            "",
            f"public class Spec{spec_num}Tests",
            "{",
        ]
        for idx, req in enumerate(requirements, start=1):
            req_id = f"REQ-{spec_num}-{idx:02d}"
            req_ids.append(req_id)
            method = f"Req{spec_num}_{idx:02d}_{_slugify(str(req), 28)}"
            lines += [
                "    [Fact]",
                f"    public void {method}()",
                "    {",
                f'        Assert.Fail("[{req_id}] not implemented yet (expected RED phase)");',
                "    }",
                "",
            ]
        lines.append("}")
        code = "\n".join(lines)
    else:
        return _err(
            f"Unsupported language '{language}'. Supported: python, typescript, java, csharp."
        )

    file_hint = f"\n- **Suggested Test File:** `{test_file}`" if test_file else ""
    return _ok(
        f"""# Trellis Failing Test Skeleton (`[REQ-P2-01]`)

- **Spec:** `{spec_id}` — {title}
- **Language:** `{language}`
- **Requirements:** {", ".join(f"`[{r}]`" for r in req_ids)}
- **Red-Phase Guarantee:** Every generated test deliberately fails until implemented.{file_hint}

## Generated Skeleton

```{language}
{code}
```

## Next Steps
1. Save the skeleton to the suggested test file.
2. Run it and confirm it **fails** for the right reason (Red).
3. Implement the minimal change, then make the test pass (Green).
4. Do not delete or skip the test to force a green build (`Tier 3` prohibition).
"""
    )


def _iter_workspace_text_files(
    root: Path,
    max_files: int = 500,
    max_bytes: int = 500_000,
    exclude: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Collect readable UTF-8 text files under `root`, skipping binary/build directories."""
    skip_dirs = {".git", "node_modules", "dist", "build", "__pycache__", ".venv", "venv", ".idea", ".vscode"}
    excludes = [e.strip().strip("/") for e in (exclude or []) if e.strip()]
    files: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink() or not _is_within_root(root, path):
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel == ex or rel.startswith(ex + "/") for ex in excludes):
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        try:
            if path.stat().st_size > max_bytes:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "\x00" in text:
            continue
        files.append((rel, text))
        if len(files) >= max_files:
            break
    return files


def tool_trellis_scan(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Run secret scanning and optional dependency vulnerability scanning ([REQ-P2-02])."""
    root = _workspace_root(workspace_root)
    rel_path = str(args.get("path", ".") or ".").strip()
    candidate = root / rel_path
    if not _is_within_root(root, candidate):
        return _err("`path` must stay within the workspace root ([REQ-TRL-19]).")
    target = candidate.resolve()
    if not target.exists():
        return _err(f"Scan path does not exist: {rel_path}")

    exclude = list(
        args.get("exclude")
        or ["tests/", "test/", "dist/", "node_modules/", "__pycache__/", ".git/"]
    )
    max_files = int(args.get("max_files", 500))
    scan_secrets = bool(args.get("scan_secrets", True))
    scan_deps = bool(args.get("scan_deps", True))
    timeout_sec = float(args.get("timeout_sec", 120))

    findings: list[str] = []
    scanned = 0
    prefix = "" if target == root else target.relative_to(root).as_posix()
    if scan_secrets:
        if target.is_file():
            candidates = [(prefix, target.read_text(encoding="utf-8", errors="ignore"))]
        elif target.is_dir():
            candidates = [
                (rel, text)
                for rel, text in _iter_workspace_text_files(root, max_files=max_files, exclude=exclude)
                if not prefix or rel == prefix or rel.startswith(prefix + "/")
            ]
        else:
            candidates = []
        for rel, text in candidates:
            scanned += 1
            hits = _scan_redaction_violations(text, ignore_placeholders=True)
            if hits:
                findings.append(f"`{rel}` -> {hits[0]}")

    dep_lines: list[str] = []
    dep_fail = False
    if scan_deps:
        pip_audit_available = importlib.util.find_spec("pip_audit") is not None
        if pip_audit_available:
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "pip_audit", "-f", "json"],
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                )
                vulns = 0
                try:
                    data = json.loads(proc.stdout or "[]")
                    for dep in data if isinstance(data, list) else []:
                        vulns += len(dep.get("vulns") or [])
                except json.JSONDecodeError:
                    dep_lines.append("- `pip-audit` produced non-JSON output; rerun manually.")
                if vulns:
                    dep_fail = True
                    dep_lines.append(f"- **pip-audit found `{vulns}` known vulnerabilities.**")
                else:
                    dep_lines.append("- `pip-audit`: no known vulnerabilities in installed packages.")
            except subprocess.TimeoutExpired:
                dep_lines.append(f"- `pip-audit` timed out after {timeout_sec:.0f}s.")
            except OSError as exc:
                dep_lines.append(f"- `pip-audit` failed to run: {exc}")
        else:
            dep_lines.append(
                "- `pip-audit` not installed. Install with `python -m pip install pip-audit` "
                "or add it to your CI dependencies."
            )
        gitleaks = shutil.which("gitleaks")
        dep_lines.append(
            f"- `gitleaks`: {'available at ' + gitleaks if gitleaks else 'not installed (built-in regex scanner used)'}"
        )

    verdict = "FAIL" if findings or dep_fail else "PASS"
    findings_block = "\n".join(f"- {f}" for f in findings) if findings else "- No secret/PAN patterns detected."
    dep_block = "\n".join(dep_lines) if dep_lines else "- Dependency scan disabled."
    excludes_text = ", ".join(str(e).strip() for e in exclude) or "none"

    return _ok(
        f"""# Trellis Security & Dependency Scan (`[REQ-P2-02]`)

- **Workspace:** `{root}`
- **Scan Target:** `{rel_path}`
- **Text Files Scanned:** `{scanned}` (excludes: {excludes_text})
- **Verdict:** **{verdict}**

## Secret / PAN Findings
{findings_block}

## Dependency & Tooling
{dep_block}

## Notes
- Findings report only pattern categories/paths, never raw secret values.
- Run `trellis_scan` in CI as a non-bypassable gate before release.
"""
    )


def tool_trellis_classify(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Classify content (Public/Internal/Confidential/Restricted) and gate AI prompts ([REQ-P2-03])."""
    content = str(args.get("content", ""))
    target = str(args.get("target", "prompt")).strip().lower()
    if not content.strip():
        return _err("`content` is required for trellis_classify.")

    restricted: list[str] = list(_scan_redaction_violations(content))
    if _JWT_RE.search(content):
        restricted.append("JWT bearer token pattern detected")
    lower = content.lower()
    restricted += [f"Restricted keyword: `{kw}`" for kw in _RESTRICTED_KEYWORDS if kw in lower]

    confidential: list[str] = []
    if _EMAIL_RE.search(content):
        confidential.append("Email address pattern detected")
    if _PHONE_RE.search(content):
        confidential.append("Phone number pattern detected")
    if _IBAN_RE.search(content):
        confidential.append("IBAN / bank account pattern detected")
    confidential += [f"Confidential keyword: `{kw}`" for kw in _CONFIDENTIAL_KEYWORDS if kw in lower]

    if restricted:
        classification = "Restricted"
    elif confidential:
        classification = "Confidential"
    elif "internal" in lower or "proprietary" in lower:
        classification = "Internal"
    else:
        classification = "Public"

    if target == "prompt":
        allowed = classification in ("Public", "Internal")
        reason = (
            "Allowed: content is not Confidential/Restricted."
            if allowed
            else "Blocked: redact or de-identify before sending to an AI prompt (Tier 3)."
        )
    else:
        allowed = classification != "Restricted"
        reason = (
            "Allowed for non-prompt target; avoid committing Confidential/Restricted data."
            if allowed
            else "Blocked: Restricted data must never enter logs, commits, or prompts (Tier 3)."
        )

    findings = restricted or confidential
    findings_block = "\n".join(f"- {f}" for f in findings) if findings else "- No sensitive patterns detected."
    return _ok(
        f"""# Trellis Data Classification & AI Prompt Gate (`[REQ-P2-03]`)

- **Classification:** **{classification}**
- **Target:** `{target}`
- **AI Prompt Allowed:** `{allowed}`
- **Verdict:** {reason}

## Signals (values never echoed)
{findings_block}

## Recommended Handling
- **Public/Internal:** Safe for AI prompts under normal review.
- **Confidential:** Redact or tokenize identifiers (`<USER_1>`, `<EMAIL_REDACTED>`) before prompting; restrict logs.
- **Restricted:** Do not send to AI or external tools. Use synthetic data only (Tier 3 in `docs/standards/ai-boundary.md`).
"""
    )


def tool_trellis_mcp_registry(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Enforce an approved MCP server allowlist and transport/scoping rules ([REQ-P2-04])."""
    root = _workspace_root(workspace_root)
    config_paths = list(args.get("config_paths") or [".mcp.json", ".agents/mcp_config.json"])
    strict = bool(args.get("strict", True))

    approved = args.get("approved_servers")
    if not approved:
        registry_path = root / "docs" / "standards" / "approved-mcp-servers.json"
        if registry_path.is_file():
            try:
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
                entry = registry.get("approved", registry)
                if isinstance(entry, dict):
                    approved = list(entry.keys())
                elif isinstance(entry, list):
                    approved = [str(v) for v in entry]
            except (OSError, json.JSONDecodeError):
                approved = None
        if not approved:
            approved = ["trellis-mcp"]
    approved_set = {str(a) for a in approved}

    findings: list[str] = []
    checked: list[str] = []
    for rel in config_paths:
        candidate = root / str(rel)
        if not _is_within_root(root, candidate):
            return _err("`config_paths` entries must stay within the workspace root ([REQ-TRL-19]).")
        cfg_path = candidate.resolve()
        if not cfg_path.is_file():
            continue
        checked.append(str(rel))
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(f"`{rel}` is not valid JSON: {exc}")
            continue
        servers = data.get("mcpServers") if isinstance(data, dict) else None
        if not isinstance(servers, dict):
            findings.append(f"`{rel}` has no `mcpServers` object.")
            continue
        for name, cfg in servers.items():
            if name not in approved_set:
                findings.append(
                    f"`{rel}`: unapproved MCP server `{name}` (allowlist: {', '.join(sorted(approved_set))})"
                )
            if not isinstance(cfg, dict):
                continue
            command = str(cfg.get("command", "")).lower()
            if re.search(r"\b(sh|bash|cmd|powershell|pwsh)\b", command) and re.search(
                r"(-c\b|/c\b|-command\b)", command
            ):
                findings.append(f"`{rel}`: `{name}` launches an inline shell command (risky).")
            url = str(cfg.get("serverUrl") or cfg.get("url") or "")
            if url.startswith("http://") and not re.match(
                r"http://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?", url
            ):
                findings.append(f"`{rel}`: `{name}` uses plaintext HTTP remote URL `{url}`.")
            env = cfg.get("env")
            if isinstance(env, dict):
                blob = "\n".join(f"{k}={v}" for k, v in env.items())
                if _scan_redaction_violations(blob, ignore_placeholders=True):
                    findings.append(f"`{rel}`: `{name}` embeds a secret-like value in `env`.")

    if not checked:
        return _ok(
            "# Trellis Approved MCP Registry (`[REQ-P2-04]`)\n\n"
            f"No MCP config files found. Allowlist: `{', '.join(sorted(approved_set))}`.\n"
        )

    verdict = "FAIL" if findings else "PASS"
    findings_block = "\n".join(f"- {f}" for f in findings) if findings else "- All configured MCP servers are approved and transport-safe."
    return _ok(
        f"""# Trellis Approved MCP Registry (`[REQ-P2-04]`)

- **Config Files Checked:** {", ".join(f"`{c}`" for c in checked)}
- **Allowlist:** {", ".join(f"`{a}`" for a in sorted(approved_set))}
- **Mode:** `{"strict" if strict else "advisory"}`
- **Verdict:** **{verdict}**

## Findings
{findings_block}

## Policy
- Only servers in `docs/standards/approved-mcp-servers.json` may be enabled.
- Remote MCP servers must use HTTPS (loopback HTTP is allowed for local development).
- Never inline shell wrappers or embed credentials in `.mcp.json`.
"""
    )


def tool_trellis_skill_route(
    args: dict[str, Any], workspace_root: Path | None = None
) -> dict[str, Any]:
    """Deterministically route a task description to the optimal Trellis skill, pack, and gate ([REQ-TRL-33])."""
    task = str(args.get("task", "")).strip().lower()
    if not task:
        return _err("`task` argument is required for trellis_skill_route")

    root = _resolve_root(workspace_root)
    index_path = root / "skills" / "skills.index.json"
    skills_catalog: list[dict[str, Any]] = []

    if index_path.is_file():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            skills_catalog = data.get("skills", [])
        except (OSError, json.JSONDecodeError):
            skills_catalog = []

    if not skills_catalog:
        return _err("Skills index not found or empty")

    task_words = set(re.findall(r"\w+", task))
    scored: list[tuple[float, dict[str, Any]]] = []

    for item in skills_catalog:
        score = 0.0
        # Positive trigger matches
        for trigger in item.get("triggers", []):
            tr_lower = trigger.lower()
            if tr_lower in task:
                score += 5.0
            else:
                tr_words = set(re.findall(r"\w+", tr_lower))
                overlap = len(tr_words & task_words)
                if overlap > 0:
                    score += overlap * 1.5

        # Negative not_for discounts
        for nf in item.get("not_for", []):
            nf_lower = nf.lower()
            if nf_lower in task:
                score -= 6.0
            else:
                nf_words = set(re.findall(r"\w+", nf_lower))
                overlap = len(nf_words & task_words)
                if overlap > 0:
                    score -= overlap * 2.0

        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_matches = scored[:2]

    if not top_matches:
        for item in skills_catalog:
            if item.get("id") == "pb-plan":
                top_matches = [(1.0, item)]
                break

    matched_skills: list[dict[str, Any]] = []
    top_tier = 1
    collected_standards: list[str] = []

    for score, item in top_matches:
        matched_skills.append({
            "id": item["id"],
            "pack": item.get("pack", "core"),
            "tier": item.get("tier", 1),
            "quota_class": item.get("quota_class", "M"),
            "why": f"Matched triggers: {', '.join(item.get('triggers', [])[:3])}",
        })
        top_tier = max(top_tier, item.get("tier", 1))
        for std in item.get("standards", []):
            if std not in collected_standards:
                collected_standards.append(std)

    if top_tier == 3:
        gate_note = "Tier 3: Strictly human-authorized only. Zero autonomous action."
    elif top_tier == 2:
        gate_note = "Tier 2: AI drafts, human approves. Pause for review."
    else:
        gate_note = "Tier 1: Autonomous execution within budget."

    rendered_text = (
        f"# Trellis Skill Router (`[REQ-TRL-33]`)\n\n"
        f"- **Task:** `{task}`\n"
        f"- **Gate:** **{gate_note}**\n\n"
        f"## Recommended Skills\n"
        + "\n".join(
            f"- `{s['id']}` (Pack: `{s['pack']}`, Tier: `{s['tier']}`, Quota: `{s['quota_class']}`): {s['why']}"
            for s in matched_skills
        )
        + f"\n\n## Canonical Standards to Consult\n"
        + "\n".join(f"- `docs/standards/{std}.md`" for std in collected_standards)
    )

    res = {
        "skills": matched_skills,
        "gate": gate_note,
        "standards": collected_standards,
        "content": [{"type": "text", "text": rendered_text}],
    }
    return res


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "trellis_get_standard",
        "description": "Retrieve an authoritative Trellis engineering standard or template (e.g., testing-standard, rca-playbook, quota-efficiency, complexity-and-performance, security-baseline, ai-boundary, git-convention, definition-of-done, performance-sla, spec-template) with SHA-256/HMAC provenance metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Standard or template name (or 'all' to list all available standards and versions).",
                },
                "version": {
                    "type": "string",
                    "description": "Optional historical version, e.g., '0.1'. Defaults to the current version.",
                },
                "offline": {
                    "type": "boolean",
                    "description": "If true, resolve from the local .trellis_cache/standards offline cache only.",
                },
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
                "author": {"type": "string", "description": "Optional spec author name (auto-resolved from git config user.name if omitted)."},
                "approver": {"type": "string", "description": "Optional human approver name (auto-resolved from git config user.name if omitted)."},
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
                "reviewer": {"type": "string", "description": "Optional human reviewer/approver name (auto-resolved from git config user.name if omitted)."},
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
                "dry_run": {"type": "boolean", "description": "If true (default when auto_fix is set), preview fixes without writing to disk."},
            },
        },
    },
    {
        "name": "trellis_test",
        "description": "Generate REQ-linked failing test skeletons ([REQ-NNN-XX]) for Python unittest, TypeScript/Jest, Java/JUnit5, or C#/xUnit to enforce the Red -> Green testing discipline.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec_id": {"type": "string", "description": "Spec identifier, e.g., SPEC-042."},
                "title": {"type": "string", "description": "Short feature or bugfix title."},
                "requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Testable requirements; each becomes a [REQ-NNN-XX] failing test.",
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "typescript", "java", "csharp"],
                    "description": "Target test language/framework.",
                },
                "test_file": {"type": "string", "description": "Optional suggested test file path."},
            },
            "required": ["spec_id", "title", "requirements"],
        },
    },
    {
        "name": "trellis_scan",
        "description": "Scan the workspace for secrets/PANs using built-in patterns and optionally run pip-audit for dependency vulnerabilities. Reports categories and paths only, never raw secret values.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Workspace-relative path to scan (default '.')."},
                "exclude": {"type": "array", "items": {"type": "string"}, "description": "Workspace-relative prefixes to skip."},
                "max_files": {"type": "integer", "description": "Maximum number of text files to scan (default 500)."},
                "scan_secrets": {"type": "boolean", "description": "Enable built-in secret/PAN scanning (default true)."},
                "scan_deps": {"type": "boolean", "description": "Enable pip-audit dependency scanning when available (default true)."},
                "timeout_sec": {"type": "number", "description": "Subprocess timeout for pip-audit in seconds."},
            },
        },
    },
    {
        "name": "trellis_classify",
        "description": "Classify content as Public/Internal/Confidential/Restricted and gate AI prompts or logs/commits (Tier 3). Sensitive values are never echoed back.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Content to classify (prompt, log line, or commit text)."},
                "target": {"type": "string", "enum": ["prompt", "log", "commit"], "description": "Intended destination for the content."},
            },
            "required": ["content"],
        },
    },
    {
        "name": "trellis_mcp_registry",
        "description": "Enforce the approved MCP server allowlist and transport/scoping rules for .mcp.json and .agents/mcp_config.json.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "config_paths": {"type": "array", "items": {"type": "string"}, "description": "Workspace-relative MCP config files to check."},
                "approved_servers": {"type": "array", "items": {"type": "string"}, "description": "Override allowlist (defaults to docs/standards/approved-mcp-servers.json or trellis-mcp)."},
                "strict": {"type": "boolean", "description": "If true (default), unapproved servers fail the audit."},
            },
        },
    },
    {
        "name": "trellis_verify",
        "description": "Verify a standard's SHA-256 hash and optional HMAC-SHA256 provenance signature to defend against tampered or injected standards.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Standard or template name to verify."},
                "version": {"type": "string", "description": "Optional version to verify (defaults to current)."},
                "expected_sha256": {"type": "string", "description": "Expected SHA-256 hex digest."},
                "expected_signature": {"type": "string", "description": "Expected HMAC-SHA256 hex signature."},
                "signing_key": {"type": "string", "description": "Optional HMAC key; defaults to TRELLIS_STANDARD_SIGNING_KEY or TRELLIS_BUNDLE_SIGNING_KEY."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "trellis_analytics",
        "description": "Report token usage, estimated cost, and quota utilization from a local usage ledger (.trellis_usage.json) instead of advisory-only quota rules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "usage_file": {"type": "string", "description": "Workspace-relative usage ledger path (default .trellis_usage.json)."},
                "budget_tokens": {"type": "integer", "description": "Token budget for quota utilization (optional)."},
                "cost_per_1k_tokens": {"type": "number", "description": "Cost per 1,000 tokens when entries omit cost_usd."},
                "period_days": {"type": "number", "description": "Only include entries from the last N days."},
            },
        },
    },
    {
        "name": "trellis_search_knowledge",
        "description": "Search Trellis standards, ADRs, specs, and RCAs using L2-normalized vectors + von Mises-Fisher (vMF) confidence (cosine + kappa), access-aware provenance filtering, compression, and anomaly detection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query or symptom description."},
                "caller_clearance": {"type": "string", "enum": ["Public", "Internal", "Confidential", "Restricted"], "description": "Caller data-classification clearance for access-aware retrieval."},
                "tenant": {"type": "string", "description": "Optional tenant scope filter."},
                "top_k": {"type": "integer", "description": "Maximum number of chunks to return (default 5)."},
                "deduplicate": {"type": "boolean", "description": "Compress near-duplicate chunks via cluster representatives."},
                "rca_only": {"type": "boolean", "description": "Restrict search to historical RCA/debugging artifacts."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "trellis_route_model",
        "description": "Select a compliant AI model and fallback chain based on Data Classification (Public..Restricted), AI Boundary Tier (1..3), and task type, with optional LiteLLM config export.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_type": {"type": "string", "enum": ["research", "coding", "review", "classify", "general"]},
                "data_classification": {"type": "string", "enum": ["Public", "Internal", "Confidential", "Restricted"]},
                "tier": {"type": "integer", "enum": [1, 2, 3]},
                "emit_litellm_config": {"type": "boolean"},
            },
            "required": ["data_classification"],
        },
    },
    {
        "name": "trellis_pipeline",
        "description": "Validate and advance the stateful pb-pipeline workflow (research -> plan -> spec -> implement -> review -> deploy) with Tier 2 human approval gates, recursive loop detection, and cross-model reviewer enforcement.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "current_stage": {"type": "string"},
                "target_stage": {"type": "string"},
                "tier": {"type": "integer", "enum": [1, 2, 3]},
                "human_approved": {"type": "boolean"},
                "history": {"type": "array", "items": {"type": "string"}},
                "max_steps": {"type": "integer"},
                "writer_model": {"type": "string"},
                "reviewer_model": {"type": "string"},
                "cross_model_review": {"type": "boolean"},
                "approver": {"type": "string", "description": "Optional human approver name (auto-resolved from git config user.name or API key label if omitted)."},
            },
            "required": ["current_stage", "target_stage"],
        },
    },
    {
        "name": "trellis_synthesize",
        "description": "Synthesize multi-model outputs into consensus points, explicit divergences/disagreements, weighted confidence, and evidence citations for collaborative problem solving.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Problem statement or question posed to the AI models."},
                "responses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string"},
                            "answer": {"type": "string"},
                            "confidence": {"type": "number"},
                            "citations": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["model", "answer"],
                    },
                },
            },
            "required": ["prompt", "responses"],
        },
    },
    {
        "name": "trellis_skill_route",
        "description": "Deterministically route a software engineering task or symptom to the optimal Trellis skill card, pack, tier, and execution gate based on skills.index.json.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Description of the development task, bug symptom, or engineering request."},
            },
            "required": ["task"],
        },
    },
]
