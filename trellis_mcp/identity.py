"""Ethical, zero-dependency human approver identity resolution ([REQ-TRL-16])."""

from __future__ import annotations

import getpass
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    import pwd
except ImportError:  # pragma: no cover - non-POSIX platforms (Windows)
    pwd = None  # type: ignore[assignment]

_GENERIC_AUTH_LABELS = frozenset({"", "admin", "default", "member", "env:trellis_api_key", "anonymous"})
_GENERIC_OS_USERS = frozenset({"", "root", "nobody", "daemon", "www-data", "system", "unknown"})
_GENERIC_GECOS = frozenset({"", "system administrator", "administrator", "unprivileged user"})
_PLACEHOLDER_RE = re.compile(r"^(?:\[.*\]|<.*>|tbd|todo|none|null|n/a|unspecified)$", re.IGNORECASE)


@dataclass(frozen=True)
class ApproverIdentity:
    """Resolved human approver/reviewer name and the ethical source used to obtain it."""

    name: str
    source: str


def _clean_name(raw: object) -> str | None:
    if raw is None:
        return None
    text = re.sub(r"[\r\n\t`]+", " ", str(raw)).strip()
    if not text or _PLACEHOLDER_RE.match(text):
        return None
    return text[:120]


def _read_git_user_name(workspace_root: Path | None) -> str | None:
    """Read local/global `git config user.name` (never `user.email`) with a short timeout."""
    cwd = str(workspace_root) if workspace_root and workspace_root.exists() else None
    commands = [
        (["git", "config", "user.name"], cwd),
        (["git", "config", "--global", "user.name"], None),
    ]
    for cmd, cmd_cwd in commands:
        if cmd_cwd is None and cmd[2] != "--global":
            continue
        try:
            proc = subprocess.run(
                cmd,
                cwd=cmd_cwd,
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0:
            cleaned = _clean_name(proc.stdout)
            if cleaned:
                return cleaned
    return None


def _read_os_user_name() -> tuple[str | None, str]:
    """Read non-sensitive local OS display name (POSIX GECOS) or username fallback."""
    if pwd is not None and hasattr(os, "getuid"):
        try:
            entry = pwd.getpwuid(os.getuid())
            gecos_name = _clean_name(str(entry.pw_gecos).split(",", 1)[0])
            if gecos_name and gecos_name.lower() not in _GENERIC_GECOS:
                return gecos_name, "os:display_name"
        except (KeyError, OSError):
            pass

    for candidate in (
        lambda: getpass.getuser(),
        lambda: os.environ.get("USER"),
        lambda: os.environ.get("USERNAME"),
    ):
        try:
            name = _clean_name(candidate())
        except (OSError, KeyError, ImportError):
            name = None
        if name and name.lower() not in _GENERIC_OS_USERS:
            return name, "os:username"
    return None, ""


def resolve_human_approver(
    workspace_root: Path | None = None,
    *,
    explicit: str | None = None,
    authenticated_label: str | None = None,
    remote_mode: bool = False,
) -> ApproverIdentity:
    """Ethically resolve the active human approver/reviewer name.

    Resolution priority (no network calls, no emails, no credential/secret access):
    1. Explicit tool argument (`approver`, `reviewer`, `author`)
    2. Explicit environment override (`TRELLIS_APPROVER`, `TRELLIS_USER_NAME`)
    3. Authenticated HTTP key label (ignoring generic labels like `env:TRELLIS_API_KEY` or `admin`)
    4. Local `git config user.name` (disabled in `remote_mode` to avoid attributing the VM host)
    5. Local OS display name / username (disabled in `remote_mode`)
    6. Safe generic fallback (`Human Reviewer`)
    """
    explicit_name = _clean_name(explicit)
    if explicit_name:
        return ApproverIdentity(name=explicit_name, source="explicit")

    for env_var in ("TRELLIS_APPROVER", "TRELLIS_USER_NAME"):
        env_name = _clean_name(os.environ.get(env_var))
        if env_name:
            return ApproverIdentity(name=env_name, source=f"env:{env_var}")

    auth_name = _clean_name(authenticated_label)
    if auth_name and auth_name.lower() not in _GENERIC_AUTH_LABELS:
        return ApproverIdentity(name=auth_name, source="auth:key_label")

    if not remote_mode:
        git_name = _read_git_user_name(workspace_root)
        if git_name:
            return ApproverIdentity(name=git_name, source="git:user.name")

        os_name, os_source = _read_os_user_name()
        if os_name:
            return ApproverIdentity(name=os_name, source=os_source)

    return ApproverIdentity(name="Human Reviewer", source="fallback")


def resolve_approver_from_args(
    args: dict[str, object],
    workspace_root: Path | None = None,
    *,
    keys: tuple[str, ...] = ("approver", "reviewer", "author"),
) -> ApproverIdentity:
    """Resolve human approver from tool `args` (and optional server-injected HTTP caller context)."""
    explicit: str | None = None
    for key in keys:
        val = args.get(key)
        if isinstance(val, str) and val.strip():
            explicit = val
            break
    raw_label = args.get("_auth_label")
    auth_label = str(raw_label) if isinstance(raw_label, str) else None
    remote_mode = bool(args.get("_remote_mode", False))
    return resolve_human_approver(
        workspace_root=workspace_root,
        explicit=explicit,
        authenticated_label=auth_label,
        remote_mode=remote_mode,
    )
