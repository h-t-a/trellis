"""CLI entrypoint for `python3 -m trellis_mcp` and the `trellis-mcp` console script."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trellis_mcp import __version__
from trellis_mcp.http_server import TrellisHTTPServer
from trellis_mcp.installer import install_global, install_remote, sync_workspace
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
        help="Zero-clone remote client install from a private VM URL (e.g. https://vm.internal:8080).",
    )
    parser.add_argument(
        "--serve-http",
        action="store_true",
        help="Host trellis-mcp over HTTP with 'Authorization: Bearer <TRELLIS_API_KEY>' authentication.",
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
        help="Team API key for Bearer auth (defaults to TRELLIS_API_KEY env var).",
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
    root = (args.workspace or (Path.cwd() if (Path.cwd() / ".agents").exists() else PACKAGE_ROOT)).resolve()

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
