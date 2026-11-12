"""Multi-IDE MCP configuration bridge for editors beyond Claude Code and Antigravity.

Generates editor-specific `mcpServers`/`servers` JSON from one source of truth so
VS Code, JetBrains, Cursor, Windsurf, and Claude Code all point at the same
zero-dependency `python -m trellis_mcp` server ([REQ-P3-01]).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SERVER_NAME = "trellis-mcp"

SUPPORTED_EDITORS: tuple[str, ...] = (
    "vscode",
    "jetbrains",
    "cursor",
    "windsurf",
    "claude",
)

# Workspace-relative destination for editors that support a project config file.
CONFIG_PATHS: dict[str, str] = {
    "vscode": ".vscode/mcp.json",
    "cursor": ".cursor/mcp.json",
    "windsurf": ".windsurf/mcp.json",
    "claude": ".mcp.json",
}


def _server_entry(remote_url: str | None, env_var: str, python_cmd: str) -> dict[str, Any]:
    if remote_url:
        return {
            "url": remote_url.rstrip("/") + "/mcp",
            "headers": {"Authorization": f"Bearer ${{env:{env_var}}}"},
        }
    return {
        "command": python_cmd,
        "args": ["-m", "trellis_mcp"],
        "env": {"PYTHONPATH": "."},
    }


def render_editor_config(
    editor: str,
    remote_url: str | None = None,
    env_var: str = "TRELLIS_API_KEY",
    python_cmd: str = "python",
    server_name: str = SERVER_NAME,
) -> dict[str, Any]:
    """Return the MCP configuration payload for a supported editor."""
    key = editor.strip().lower()
    if key not in SUPPORTED_EDITORS:
        raise ValueError(
            f"Unsupported editor '{editor}'. Choose one of: {', '.join(SUPPORTED_EDITORS)}"
        )

    entry = _server_entry(remote_url, env_var, python_cmd)
    if key == "vscode":
        transport = "http" if remote_url else "stdio"
        return {"servers": {server_name: {"type": transport, **entry}}}

    return {"mcpServers": {server_name: entry}}


def editor_config_path(editor: str, workspace_root: Path) -> Path | None:
    """Return the conventional workspace config path, or None for in-IDE-only editors."""
    rel = CONFIG_PATHS.get(editor.strip().lower())
    return (workspace_root / rel) if rel else None


def write_editor_config(
    editor: str,
    workspace_root: Path,
    remote_url: str | None = None,
    env_var: str = "TRELLIS_API_KEY",
    output_path: Path | None = None,
) -> Path:
    """Write the generated config and return its path (never includes secrets)."""
    config = render_editor_config(
        editor, remote_url=remote_url, env_var=env_var
    )
    target = output_path or editor_config_path(editor, workspace_root)
    if target is None:
        raise ValueError(
            f"Editor '{editor}' has no standard workspace file; pass an explicit --config-out path."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return target
