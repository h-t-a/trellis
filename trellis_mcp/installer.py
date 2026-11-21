"""Cross-device workspace synchronization, global user-level installer, and single-file .pyz bundler ([REQ-MCP-03, REQ-MCP-07, REQ-MCP-09]).

Supports:
- `sync_workspace(repo_root)`: Syncs `.agents/skills/` -> `.claude/skills/`, updates `.mcp.json`
  and `.agents/mcp_config.json`, and removes deprecated `.agents/workflows/*.md`.
- `install_global(repo_root, home_dir)`: Installs the `trellis` Antigravity plugin into
  `~/.gemini/config/plugins/trellis/`, registers `trellis-mcp` in `~/.gemini/config/mcp_config.json`,
  and installs `/pb-*` skills into `~/.claude/skills/`.
- `build_pyz_bundle(repo_root, output_path)`: Packs `trellis_mcp`, `docs/standards/`, `templates/`,
  and `.agents/` into a single standalone `trellis-mcp.pyz` executable archive (`[REQ-MCP-09]`).
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib.request import Request

from trellis_mcp import __version__
from trellis_mcp.tools import STANDARD_FILE_MAP, list_bundled_skills, read_bundled_text

SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_SAFE_BASE_URL_RE = re.compile(r"^https?://[A-Za-z0-9._:\-\[\]]+(?:/[A-Za-z0-9._/\-]*)?$")


def validate_skill_name(name: str) -> bool:
    """Return True iff `name` is a safe single-segment lowercase skill identifier ([REQ-TRL-22])."""
    return bool(isinstance(name, str) and SKILL_NAME_RE.match(name))


def _chmod_owner_only(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _merge_mcp_config(
    config_path: Path,
    server_entry: dict[str, Any],
    *,
    restrict_permissions: bool = False,
) -> None:
    """Safely merge `trellis-mcp` into an existing or new MCP JSON config file ([REQ-TRL-22]).

    If an existing config file cannot be parsed as valid JSON, backs it up to
    `<name>.bak.<timestamp>` and aborts with ValueError instead of silently wiping other servers.
    """
    data: dict[str, Any] = {"mcpServers": {}}
    if config_path.exists():
        raw_existing = config_path.read_text(encoding="utf-8")
        try:
            loaded = json.loads(raw_existing)
        except json.JSONDecodeError as exc:
            backup = config_path.with_name(f"{config_path.name}.bak.{int(time.time())}")
            shutil.copy2(config_path, backup)
            raise ValueError(
                f"Refusing to overwrite malformed MCP config `{config_path}` (backup saved to `{backup.name}`): {exc}"
            ) from exc
        if not isinstance(loaded, dict):
            backup = config_path.with_name(f"{config_path.name}.bak.{int(time.time())}")
            shutil.copy2(config_path, backup)
            raise ValueError(
                f"Refusing to overwrite non-object MCP config `{config_path}` (backup saved to `{backup.name}`)."
            )
        data = loaded

    if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
        data["mcpServers"] = {}

    data["mcpServers"]["trellis-mcp"] = server_entry
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if restrict_permissions:
        _chmod_owner_only(config_path)


def sync_workspace(repo_root: Path) -> str:
    """Synchronize `.agents/skills/` to `.claude/skills/` and configure workspace MCP files."""
    root = repo_root.resolve()
    agents_skills_dir = root / ".agents" / "skills"
    claude_skills_dir = root / ".claude" / "skills"
    claude_commands_dir = root / ".claude" / "commands"

    synced_skills: list[str] = []
    if agents_skills_dir.exists():
        claude_skills_dir.mkdir(parents=True, exist_ok=True)
        claude_commands_dir.mkdir(parents=True, exist_ok=True)
        for skill_md in sorted(agents_skills_dir.glob("*/SKILL.md")):
            skill_name = skill_md.parent.name
            dest_skill_dir = claude_skills_dir / skill_name
            dest_skill_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(skill_md, dest_skill_dir / "SKILL.md")
            synced_skills.append(skill_name)

            # For /pb-* skills, also mirror to .claude/commands/<name>.md for Claude Code slash command compatibility.
            # Command files live one directory shallower than skills, so rebase `../../../` links to `../../`.
            if skill_name.startswith("pb-"):
                command_text = skill_md.read_text(encoding="utf-8").replace("(../../../", "(../../")
                (claude_commands_dir / f"{skill_name}.md").write_text(command_text, encoding="utf-8")

        synced_set = set(synced_skills)
        for existing_dir in sorted(claude_skills_dir.iterdir()):
            if existing_dir.is_dir() and existing_dir.name not in synced_set:
                shutil.rmtree(existing_dir, ignore_errors=True)
        for existing_cmd in sorted(claude_commands_dir.glob("*.md")):
            if existing_cmd.stem not in synced_set:
                existing_cmd.unlink(missing_ok=True)

    # Remove deprecated .agents/workflows/*.md files (F01)
    workflows_dir = root / ".agents" / "workflows"
    removed_workflows: list[str] = []
    if workflows_dir.exists():
        for wf in sorted(workflows_dir.glob("*.md")):
            removed_workflows.append(wf.name)
            wf.unlink()
        if not any(workflows_dir.iterdir()):
            workflows_dir.rmdir()

    # Ensure .agents/skills.json exists
    skills_manifest = root / ".agents" / "skills.json"
    skills_manifest.parent.mkdir(parents=True, exist_ok=True)
    skills_manifest.write_text(
        json.dumps({"skills": [{"path": ".agents/skills"}]}, indent=2) + "\n",
        encoding="utf-8",
    )

    # Configure workspace .mcp.json and .agents/mcp_config.json
    py_cmd = "python" if sys.platform == "win32" else "python3"
    workspace_mcp_entry = {
        "command": py_cmd,
        "args": ["-m", "trellis_mcp"],
        "env": {"PYTHONPATH": "."},
    }
    _merge_mcp_config(root / ".mcp.json", workspace_mcp_entry)
    _merge_mcp_config(root / ".agents" / "mcp_config.json", workspace_mcp_entry)

    return (
        f"Synced {len(synced_skills)} skills ({', '.join(synced_skills)}) to `.claude/skills/`, "
        f"updated `.mcp.json` and `.agents/mcp_config.json` with `trellis-mcp`, "
        f"and removed {len(removed_workflows)} deprecated `.agents/workflows/*.md` file(s)."
    )


def install_global(repo_root: Path, home_dir: Path | None = None) -> str:
    """Install Trellis plugin, rules, skills, and `trellis-mcp` globally into the user's home directory."""
    root = repo_root.resolve()
    home = (home_dir or Path.home()).resolve()

    plugin_dir = home / ".gemini" / "config" / "plugins" / "trellis"
    plugin_rules_dir = plugin_dir / "rules"
    plugin_skills_dir = plugin_dir / "skills"
    plugin_rules_dir.mkdir(parents=True, exist_ok=True)
    plugin_skills_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write plugin.json
    plugin_manifest = {
        "name": "trellis",
        "version": __version__,
        "description": "Trellis AI Engineering Playbook: Fast RCA, Spec-Driven Dev, Complexity/Little's Law, Quota Guards, and DoD Review.",
        "author": {"name": "HTA"},
        "rules": "rules/AGENTS.md",
        "skills": "skills",
        "mcpServers": ".mcp.json",
    }
    (plugin_dir / "plugin.json").write_text(
        json.dumps(plugin_manifest, indent=2) + "\n", encoding="utf-8"
    )

    # 2. Write global plugin rules/AGENTS.md combining workspace rules with YAML frontmatter
    standards_rule_text = read_bundled_text(".agents/rules/standards.md", workspace_root=root)
    if standards_rule_text:
        (plugin_rules_dir / "AGENTS.md").write_text(standards_rule_text, encoding="utf-8")
    else:
        (plugin_rules_dir / "AGENTS.md").write_text(
            "---\ntrigger: always_on\ndescription: Trellis AI Engineering Playbook global rules\n---\n\n"
            "# Trellis Global Rules\nUse `trellis-mcp` tools (`trellis_rca`, `trellis_spec`, `trellis_enhance`, `trellis_budget`, `trellis_review`, `trellis_test`, `trellis_scan`, `trellis_classify`, `trellis_mcp_registry`, `trellis_verify`, `trellis_analytics`).\n",
            encoding="utf-8",
        )

    # 3. Copy all workspace skills into ~/.gemini/config/plugins/trellis/skills/ and ~/.claude/skills/
    claude_global_skills = home / ".claude" / "skills"
    claude_global_skills.mkdir(parents=True, exist_ok=True)

    bundled_skills = list_bundled_skills(workspace_root=root)
    installed_skills: list[str] = []
    for skill_name, skill_text in sorted(bundled_skills.items()):
        for target_base in (plugin_skills_dir, claude_global_skills):
            dest = target_base / skill_name
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "SKILL.md").write_text(skill_text, encoding="utf-8")
        installed_skills.append(skill_name)

    # 4. Write global MCP server entry with portable PYTHONPATH pointing to repo_root
    py_cmd = "python" if sys.platform == "win32" else "python3"
    global_mcp_entry = {
        "command": py_cmd,
        "args": ["-m", "trellis_mcp"],
        "env": {"PYTHONPATH": str(root)},
    }
    _merge_mcp_config(plugin_dir / ".mcp.json", global_mcp_entry)
    _merge_mcp_config(home / ".gemini" / "config" / "mcp_config.json", global_mcp_entry)

    return (
        f"Installed `trellis-mcp` globally:\n"
        f"- Antigravity plugin: `{plugin_dir}`\n"
        f"- Global MCP config: `{home / '.gemini/config/mcp_config.json'}`\n"
        f"- Claude Code global skills: `{claude_global_skills}` ({len(installed_skills)} skills)"
    )


def _standard_provenance(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Return per-standard version, SHA-256, and optional HMAC signature for bundles ([REQ-P3-05])."""
    root = repo_root.resolve()
    entries: dict[str, dict[str, Any]] = {}
    versions: dict[str, str] = {}
    manifest_path = root / "docs" / "standards" / "standards.json"
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for name, entry in (data.get("standards") or {}).items():
                if isinstance(entry, dict) and entry.get("version"):
                    versions[str(name)] = str(entry["version"])
        except (OSError, ValueError, TypeError):
            versions = {}

    signing_key = os.environ.get("TRELLIS_STANDARD_SIGNING_KEY") or os.environ.get(
        "TRELLIS_BUNDLE_SIGNING_KEY"
    )
    for name, rel_path in STANDARD_FILE_MAP.items():
        content = read_bundled_text(rel_path, workspace_root=root)
        if content is None:
            continue
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        record: dict[str, Any] = {
            "version": versions.get(name, "0.1"),
            "path": rel_path,
            "sha256": digest,
        }
        if signing_key:
            record["signature"] = hmac.new(
                signing_key.encode("utf-8"), content.encode("utf-8"), hashlib.sha256
            ).hexdigest()
        entries[name] = record
    return entries


def build_remote_bundle(repo_root: Path) -> dict[str, Any]:
    """Build a JSON-serializable bundle of rules and skills for zero-clone remote clients ([REQ-MCP-07, REQ-MCP-09])."""
    root = repo_root.resolve()
    skills = list_bundled_skills(workspace_root=root)

    rules_md = read_bundled_text(".agents/rules/standards.md", workspace_root=root) or (
        "---\ntrigger: always_on\ndescription: Trellis AI Engineering Playbook global rules\n---\n\n"
        "# Trellis Global Rules\nUse `trellis-mcp` tools (`trellis_rca`, `trellis_spec`, `trellis_enhance`, `trellis_budget`, `trellis_review`, `trellis_test`, `trellis_scan`, `trellis_classify`, `trellis_mcp_registry`, `trellis_verify`, `trellis_analytics`).\n"
    )

    return {
        "version": __version__,
        "rules_md": rules_md,
        "skills": skills,
        "standards": _standard_provenance(root),
    }


def build_pyz_bundle(repo_root: Path, output_path: Path) -> str:
    """Pack `trellis_mcp`, `docs/standards/`, `templates/`, and `.agents/` into a single standalone `.pyz` file ([REQ-MCP-09])."""
    root = repo_root.resolve()
    out = output_path.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    buf = io.BytesIO()
    included_count = 0
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Entrypoint for `python trellis-mcp.pyz`
        zf.writestr(
            "__main__.py",
            "import sys\nfrom trellis_mcp.__main__ import main\nraise SystemExit(main())\n",
        )
        include_patterns = [
            "trellis_mcp/*.py",
            "docs/standards/*.md",
            "docs/standards/*.json",
            "docs/standards/versions/*.md",
            "docs/integrations/*.md",
            "templates/*.md",
            ".agents/rules/*.md",
            ".agents/skills/*/SKILL.md",
        ]
        for pattern in include_patterns:
            for file_path in sorted(root.glob(pattern)):
                if file_path.is_file():
                    arcname = file_path.relative_to(root).as_posix()
                    zf.write(file_path, arcname=arcname)
                    included_count += 1

    with out.open("wb") as f:
        f.write(b"#!/usr/bin/env python3\n")
        f.write(buf.getvalue())

    try:
        os.chmod(out, 0o755)
    except OSError:
        pass

    size_kb = out.stat().st_size / 1024.0
    return f"Built standalone single-file bundle: {out} ({included_count} files, {size_kb:.1f} KB)"


def install_remote(
    server_url: str,
    api_key: str | None = None,
    home_dir: Path | None = None,
    signing_key: str | None = None,
    *,
    allow_unsigned: bool = False,
    write_literal_key: bool = False,
) -> str:
    """Zero-clone client installer: fetches `/bundle.json`, verifies signature & skill names, and configures MCP + skills ([REQ-MCP-07, REQ-TRL-22])."""
    base = server_url.rstrip("/")
    if base.endswith("/mcp"):
        base = base[:-4]
    if not _SAFE_BASE_URL_RE.match(base):
        raise ValueError(f"Invalid server_url: {server_url!r}")
    mcp_endpoint = f"{base}/mcp"
    bundle_endpoint = f"{base}/bundle.json"

    resolved_key = (api_key or os.environ.get("TRELLIS_API_KEY", "")).strip()
    resolved_signing_key = (
        signing_key if signing_key is not None else os.environ.get("TRELLIS_BUNDLE_SIGNING_KEY", "")
    ).strip() or None
    if not resolved_signing_key and not allow_unsigned:
        raise ValueError(
            "Bundle signature verification is mandatory ([REQ-TRL-22]). "
            "Pass --bundle-signing-key / TRELLIS_BUNDLE_SIGNING_KEY, or opt in explicitly with --allow-unsigned."
        )

    headers: dict[str, str] = {"Accept": "application/json"}
    if resolved_key:
        headers["Authorization"] = f"Bearer {resolved_key}"

    req = Request(bundle_endpoint, headers=headers, method="GET")
    from trellis_mcp.http_server import open_url_resilient

    with open_url_resilient(req, timeout=15) as resp:
        raw = resp.read()
        provided_sig = resp.headers.get("X-Trellis-Bundle-Signature")
        if provided_sig is None and isinstance(resp.headers, dict):
            provided_sig = resp.headers.get("x-trellis-bundle-signature")
        if resolved_signing_key:
            if not provided_sig:
                raise ValueError(
                    "Bundle signature missing but TRELLIS_BUNDLE_SIGNING_KEY is configured; refusing install."
                )
            expected_sig = hmac.new(
                resolved_signing_key.encode("utf-8"), raw, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected_sig, str(provided_sig).strip().lower()):
                raise ValueError(
                    "Bundle signature verification failed (possible MITM or tampered server); refusing install."
                )
        bundle = json.loads(raw.decode("utf-8"))

    skills_map: dict[str, str] = dict(bundle.get("skills") or {})
    for skill_name in skills_map:
        if not validate_skill_name(skill_name):
            raise ValueError(
                f"Invalid skill name in remote bundle: {skill_name!r} "
                "(must match ^[a-z0-9][a-z0-9-]{{0,62}}$) ([REQ-TRL-22])."
            )

    home = (home_dir or Path.home()).resolve()
    plugin_dir = home / ".gemini" / "config" / "plugins" / "trellis"
    plugin_rules_dir = plugin_dir / "rules"
    plugin_skills_dir = plugin_dir / "skills"
    claude_global_skills = home / ".claude" / "skills"

    # Compute diff summary against existing installed files before writing ([REQ-TRL-22 / F6])
    added_skills: list[str] = []
    updated_skills: list[str] = []
    unchanged_skills: list[str] = []
    for skill_name, skill_content in sorted(skills_map.items()):
        existing_path = plugin_skills_dir / skill_name / "SKILL.md"
        new_text = str(skill_content)
        if not existing_path.exists():
            added_skills.append(skill_name)
        elif existing_path.read_text(encoding="utf-8", errors="ignore") != new_text:
            updated_skills.append(skill_name)
        else:
            unchanged_skills.append(skill_name)

    # Validate & merge MCP configs FIRST so malformed existing configs abort cleanly before partial writes
    auth_header_val = (
        f"Bearer {resolved_key}"
        if (write_literal_key and resolved_key)
        else "Bearer ${TRELLIS_API_KEY}"
    )
    remote_mcp_entry: dict[str, Any] = {
        "serverUrl": mcp_endpoint,
        "headers": {
            "Authorization": auth_header_val
        },
    }
    _merge_mcp_config(
        home / ".gemini" / "config" / "mcp_config.json",
        remote_mcp_entry,
        restrict_permissions=True,
    )
    _merge_mcp_config(
        plugin_dir / ".mcp.json",
        remote_mcp_entry,
        restrict_permissions=True,
    )

    plugin_rules_dir.mkdir(parents=True, exist_ok=True)
    plugin_skills_dir.mkdir(parents=True, exist_ok=True)
    claude_global_skills.mkdir(parents=True, exist_ok=True)

    plugin_manifest = {
        "name": "trellis",
        "version": bundle.get("version", __version__),
        "description": "Trellis AI Engineering Playbook (Remote MCP + Global Skills)",
        "author": {"name": "HTA"},
        "rules": "rules/AGENTS.md",
        "skills": "skills",
        "mcpServers": ".mcp.json",
    }
    (plugin_dir / "plugin.json").write_text(
        json.dumps(plugin_manifest, indent=2) + "\n", encoding="utf-8"
    )
    (plugin_rules_dir / "AGENTS.md").write_text(
        str(bundle.get("rules_md", "")), encoding="utf-8"
    )

    for skill_name, skill_content in sorted(skills_map.items()):
        for target_base in (plugin_skills_dir, claude_global_skills):
            dest = target_base / skill_name
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "SKILL.md").write_text(str(skill_content), encoding="utf-8")

    return (
        f"Installed remote `trellis-mcp` client (zero git clone):\n"
        f"- Remote MCP endpoint: `{mcp_endpoint}`\n"
        f"- Antigravity plugin: `{plugin_dir}`\n"
        f"- Global MCP config: `{home / '.gemini/config/mcp_config.json'}` (mode 0600, env-var token ref)\n"
        f"- Bundle diff: +{len(added_skills)} added, ~{len(updated_skills)} updated, ={len(unchanged_skills)} unchanged\n"
        f"- Installed {len(skills_map)} `/pb-*` & engineering skills into `{claude_global_skills}`"
    )


def render_remote_install_script(base_url: str) -> str:
    """Render a hardened zero-clone POSIX shell script (`GET /install.sh`) ([REQ-TRL-22])."""
    clean_base = base_url.rstrip("/")
    if not _SAFE_BASE_URL_RE.match(clean_base):
        raise ValueError(f"Refusing to render installer for unsafe base_url: {base_url!r}")
    return f"""#!/bin/sh
# Zero-Clone Remote Installer for Trellis MCP ({clean_base})
# Usage:
#   export TRELLIS_API_KEY="<your-team-api-key>"
#   export TRELLIS_BUNDLE_SIGNING_KEY="<bundle-signing-key>"
#   curl -fsSL -H "Authorization: Bearer $TRELLIS_API_KEY" {clean_base}/install.sh | sh
set -eu

if [ -z "${{TRELLIS_API_KEY:-}}" ]; then
  echo "Error: TRELLIS_API_KEY environment variable is not set." >&2
  echo "Run: export TRELLIS_API_KEY='<team-key>' before running this installer." >&2
  exit 1
fi

python3 - "{clean_base}" <<'PYEOF'
import hashlib, hmac, json, os, re, shutil, sys, time
from pathlib import Path
from urllib.request import Request, urlopen

SKILL_RE = re.compile(r"^[a-z0-9][a-z0-9-]{{0,62}}$")
base = sys.argv[1].rstrip("/")
key = os.environ["TRELLIS_API_KEY"].strip()
signing_key = os.environ.get("TRELLIS_BUNDLE_SIGNING_KEY", "").strip()
allow_unsigned = os.environ.get("TRELLIS_ALLOW_UNSIGNED", "").strip().lower() in ("1", "true", "yes")
if not signing_key and not allow_unsigned:
    sys.exit("Error: TRELLIS_BUNDLE_SIGNING_KEY is required (or set TRELLIS_ALLOW_UNSIGNED=1 explicitly).")

req = Request(f"{{base}}/bundle.json", headers={{"Authorization": f"Bearer {{key}}", "Accept": "application/json"}})
with urlopen(req, timeout=15) as resp:
    raw = resp.read()
    provided_sig = resp.headers.get("X-Trellis-Bundle-Signature", "")
    if signing_key:
        if not provided_sig:
            sys.exit("Error: bundle signature missing from server response; refusing install.")
        expected = hmac.new(signing_key.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, provided_sig.strip().lower()):
            sys.exit("Error: bundle signature verification failed (possible tampering); refusing install.")
    bundle = json.loads(raw.decode("utf-8"))

skills = bundle.get("skills", {{}})
for name in skills:
    if not isinstance(name, str) or not SKILL_RE.match(name):
        sys.exit(f"Error: invalid skill name in bundle: {{name!r}}")

home = Path.home()
plugin_dir = home / ".gemini" / "config" / "plugins" / "trellis"
entry = {{
    "serverUrl": f"{{base}}/mcp",
    "headers": {{"Authorization": "Bearer ${{TRELLIS_API_KEY}}"}}
}}
for cfg in (home / ".gemini" / "config" / "mcp_config.json", plugin_dir / ".mcp.json"):
    data = {{"mcpServers": {{}}}}
    if cfg.exists():
        try:
            loaded = json.loads(cfg.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("JSON root must be an object")
            data = loaded
        except Exception as exc:
            backup = cfg.with_name(f"{{cfg.name}}.bak.{{int(time.time())}}")
            shutil.copy2(cfg, backup)
            sys.exit(f"Error: malformed MCP config {{cfg}} (backup saved to {{backup.name}}): {{exc}}")
    data.setdefault("mcpServers", {{}})["trellis-mcp"] = entry
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps(data, indent=2) + "\\n", encoding="utf-8")
    try:
        os.chmod(cfg, 0o600)
    except OSError:
        pass

(plugin_dir / "rules").mkdir(parents=True, exist_ok=True)
(plugin_dir / "skills").mkdir(parents=True, exist_ok=True)
claude_skills = home / ".claude" / "skills"
claude_skills.mkdir(parents=True, exist_ok=True)

(plugin_dir / "plugin.json").write_text(json.dumps({{
    "name": "trellis",
    "version": bundle.get("version", "0.1.0"),
    "description": "Trellis AI Engineering Playbook (Remote MCP)",
    "author": {{"name": "HTA"}},
    "rules": "rules/AGENTS.md",
    "skills": "skills",
    "mcpServers": ".mcp.json",
}}, indent=2) + "\\n", encoding="utf-8")

(plugin_dir / "rules" / "AGENTS.md").write_text(bundle.get("rules_md", ""), encoding="utf-8")

for name, text in skills.items():
    for root in (plugin_dir / "skills", claude_skills):
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(text, encoding="utf-8")

print(f"Installed remote trellis-mcp -> {{base}}/mcp ({{len(skills)}} skills, mode 0600)")
PYEOF
"""
