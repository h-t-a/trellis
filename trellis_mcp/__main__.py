"""CLI entrypoint for `python3 -m trellis_mcp` and the `trellis-mcp` console script."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from trellis_mcp import __version__
from trellis_mcp.http_server import TrellisHTTPServer, TrellisKeyStore
from trellis_mcp.installer import build_pyz_bundle, install_global, install_remote, sync_workspace
from trellis_mcp.server import TrellisMCPServer
from trellis_mcp.tools import PACKAGE_ROOT, tool_trellis_doctor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="trellis-mcp",
        description="Trellis AI Engineering Playbook MCP Server & Cross-Device Installer",
    )
    parser.add_argument(
        "--version", action="version", version=f"trellis-mcp {__version__}"
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace root directory (defaults to current working directory or package root).",
    )
    parser.add_argument(
        "--sync-workspace",
        action="store_true",
        help="Sync .agents/skills/ to .claude/skills/, update .mcp.json, and remove deprecated .agents/workflows/.",
    )
    parser.add_argument(
        "--install-global",
        action="store_true",
        help="Install Trellis plugin, rules, skills, and MCP server globally into ~/.gemini/config/ and ~/.claude/.",
    )
    parser.add_argument(
        "--install-remote",
        metavar="SERVER_URL",
        type=str,
        default=None,
        help="Zero-clone remote client install from a private VM URL (e.g. http://<vm-ip>:8080).",
    )
    parser.add_argument(
        "--build-pyz",
        metavar="OUTPUT_PATH",
        nargs="?",
        const="dist/trellis-mcp.pyz",
        default=None,
        help="Build a standalone single-file executable bundle (default: dist/trellis-mcp.pyz) ([REQ-MCP-09]).",
    )
    parser.add_argument(
        "--serve-http",
        action="store_true",
        help="Host trellis-mcp over HTTP with 'Authorization: Bearer <API_KEY>' authentication.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Bind host for --serve-http (default: 0.0.0.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Bind port for --serve-http (default: 8080).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Team or Admin API key for Bearer auth (defaults to TRELLIS_API_KEY env var).",
    )
    parser.add_argument(
        "--auto-generate-key",
        action="store_true",
        help="Auto-generate and persist an administrator API key on startup if TRELLIS_API_KEY is not set ([REQ-MCP-08-01]).",
    )
    parser.add_argument(
        "--generate-key",
        metavar="LABEL",
        type=str,
        default=None,
        help="Generate a new API key for a user or team (e.g. --generate-key team-ibanking) ([REQ-MCP-08-02]).",
    )
    parser.add_argument(
        "--role",
        choices=["member", "admin"],
        default="member",
        help="Role for --generate-key: 'member' (default, MCP/bundle access) or 'admin' (can also issue/revoke keys).",
    )
    parser.add_argument(
        "--list-keys",
        action="store_true",
        help="List all issued API keys (masked prefixes, labels, roles, status) ([REQ-MCP-08-04]).",
    )
    parser.add_argument(
        "--revoke-key",
        metavar="KEY_ID_OR_LABEL",
        type=str,
        default=None,
        help="Immediately revoke an API key by key_id or label ([REQ-MCP-08-04]).",
    )
    parser.add_argument(
        "--keys-file",
        type=Path,
        default=None,
        help="Path to the JSON key registry file (default: <workspace>/.trellis_keys.json or TRELLIS_KEYS_FILE).",
    )
    parser.add_argument(
        "--check",
        "--doctor",
        dest="doctor",
        action="store_true",
        help="Run Trellis workspace doctor to validate rule frontmatter, skill line budgets, and MCP setup.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix missing YAML frontmatter or deprecated workflow files when running with --check/--doctor.",
    )

    args = parser.parse_args(argv)
    default_root = Path.cwd() if (Path.cwd() / ".agents").exists() else PACKAGE_ROOT
    root = (args.workspace or default_root).resolve()
    keys_base_dir = root.parent if root.is_file() else root
    resolved_keys_file = (
        args.keys_file
        if args.keys_file is not None
        else Path(os.environ.get("TRELLIS_KEYS_FILE", str(keys_base_dir / ".trellis_keys.json")))
    ).resolve()

    if args.build_pyz:
        print(build_pyz_bundle(repo_root=root, output_path=Path(args.build_pyz)))
        return 0

    if args.generate_key:
        store = TrellisKeyStore(resolved_keys_file)
        created = store.generate_key(label=args.generate_key, role=args.role)
        print(json.dumps(created, indent=2))
        return 0

    if args.list_keys:
        store = TrellisKeyStore(resolved_keys_file)
        print(json.dumps({"keys_file": str(resolved_keys_file), "keys": store.list_keys()}, indent=2))
        return 0

    if args.revoke_key:
        store = TrellisKeyStore(resolved_keys_file)
        revoked = store.revoke_key(args.revoke_key)
        if revoked is None:
            print(f"Error: Active key not found for '{args.revoke_key}'.", file=sys.stderr)
            return 1
        print(json.dumps({"status": "revoked", "key": revoked}, indent=2))
        return 0

    if args.sync_workspace:
        print(sync_workspace(root))
        return 0

    if args.install_global:
        print(install_global(root))
        return 0

    if args.install_remote:
        print(install_remote(server_url=args.install_remote, api_key=args.api_key))
        return 0

    if args.serve_http:
        http_srv = TrellisHTTPServer(
            host=args.host,
            port=args.port,
            api_key=args.api_key,
            workspace_root=root,
            auto_generate_key=args.auto_generate_key,
            keys_file=resolved_keys_file,
        )
        http_srv.serve_forever()
        return 0

    if args.doctor:
        res = tool_trellis_doctor(
            {"workspace_path": str(root), "auto_fix": args.fix},
            workspace_root=root,
        )
        text = res["content"][0]["text"]
        print(text)
        return 1 if "ISSUES_FOUND" in text else 0

    server = TrellisMCPServer(workspace_root=root)
    server.serve_stdio()
    return 0


if __name__ == "__main__":
    sys.exit(main())
