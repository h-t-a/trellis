"""CLI entrypoint for `python3 -m trellis_mcp` and the `trellis-mcp` console script."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from trellis_mcp import __version__
from trellis_mcp.editors import SUPPORTED_EDITORS, render_editor_config, write_editor_config
from trellis_mcp.http_server import (
    DEFAULT_MAX_BODY_BYTES,
    DEFAULT_RATE_LIMIT,
    DEFAULT_RATE_WINDOW_SEC,
    DEFAULT_REQUEST_TIMEOUT_SEC,
    TrellisHTTPServer,
    TrellisKeyStore,
)
from trellis_mcp.installer import build_pyz_bundle, install_global, install_remote, sync_workspace
from trellis_mcp.server import TrellisMCPServer
from trellis_mcp.tools import PACKAGE_ROOT, tool_trellis_analytics, tool_trellis_doctor, tool_trellis_get_standard


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
        default="127.0.0.1",
        help="Bind host for --serve-http (default: 127.0.0.1; pass 0.0.0.0 explicitly for VM/LAN).",
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
        "--expires-days",
        type=float,
        default=None,
        help="Optional key lifetime in days for --generate-key / --rotate-key (e.g. 90).",
    )
    parser.add_argument(
        "--scopes",
        type=str,
        default=None,
        help="Comma-separated permitted MCP tool names for --generate-key (default: all tools) ([REQ-TRL-03]).",
    )
    parser.add_argument(
        "--allowed-origin",
        action="append",
        default=None,
        help="Allowed browser Origin for /mcp and /admin/* (repeatable) ([REQ-TRL-01]).",
    )
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=None,
        help="Path to redacted JSONL HTTP/MCP audit log (default: .trellis-audit.jsonl) ([REQ-TRL-02]).",
    )
    parser.add_argument(
        "--rotate-key",
        metavar="KEY_ID_OR_LABEL",
        type=str,
        default=None,
        help="Atomically revoke an existing key and issue a replacement with the same role ([REQ-MCP-08-04]).",
    )
    parser.add_argument(
        "--tls-cert",
        type=Path,
        default=os.environ.get("TRELLIS_TLS_CERT") or None,
        help="Path to a PEM TLS certificate to serve HTTPS (requires --tls-key or TRELLIS_TLS_KEY).",
    )
    parser.add_argument(
        "--tls-key",
        type=Path,
        default=os.environ.get("TRELLIS_TLS_KEY") or None,
        help="Path to the PEM private key for --tls-cert.",
    )
    parser.add_argument(
        "--bundle-signing-key",
        type=str,
        default=None,
        help="Optional HMAC key used to sign /bundle.json and /install.sh responses (or TRELLIS_BUNDLE_SIGNING_KEY).",
    )
    parser.add_argument(
        "--max-body-bytes",
        type=int,
        default=DEFAULT_MAX_BODY_BYTES,
        help=f"Maximum accepted HTTP request body size in bytes (default: {DEFAULT_MAX_BODY_BYTES}).",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=DEFAULT_RATE_LIMIT,
        help=f"Max requests per client per window (default: {DEFAULT_RATE_LIMIT}; 0 disables).",
    )
    parser.add_argument(
        "--rate-window-sec",
        type=float,
        default=DEFAULT_RATE_WINDOW_SEC,
        help=f"Rate-limit window in seconds (default: {DEFAULT_RATE_WINDOW_SEC}).",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=DEFAULT_REQUEST_TIMEOUT_SEC,
        help=f"Per-connection socket timeout in seconds (default: {DEFAULT_REQUEST_TIMEOUT_SEC}).",
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview --fix changes without writing to disk.",
    )
    parser.add_argument(
        "--emit-config",
        choices=list(SUPPORTED_EDITORS),
        default=None,
        help="Print or write an MCP config for a supported editor (vscode, jetbrains, cursor, windsurf, claude) ([REQ-P3-01]).",
    )
    parser.add_argument(
        "--config-out",
        type=Path,
        default=None,
        help="Write --emit-config output to this path instead of stdout.",
    )
    parser.add_argument(
        "--remote-url",
        type=str,
        default=None,
        help="Use a remote HTTP MCP endpoint (e.g. https://vm:8080) with --emit-config.",
    )
    parser.add_argument(
        "--sync-cache",
        action="store_true",
        help="Copy all standards into the offline cache (.trellis_cache/standards) ([REQ-P3-03]).",
    )
    parser.add_argument(
        "--usage-report",
        action="store_true",
        help="Print token/cost/quota analytics from the local usage ledger ([REQ-P3-04]).",
    )
    parser.add_argument(
        "--usage-file",
        type=Path,
        default=None,
        help="Path to the usage ledger for --usage-report (default: <workspace>/.trellis_usage.json).",
    )
    parser.add_argument(
        "--budget-tokens",
        type=int,
        default=0,
        help="Token budget for --usage-report quota utilization.",
    )
    parser.add_argument(
        "--cost-per-1k-tokens",
        type=float,
        default=0.0,
        help="Fallback cost per 1K tokens for --usage-report.",
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

    if args.emit_config:
        if args.config_out:
            target = write_editor_config(
                args.emit_config,
                root,
                remote_url=args.remote_url,
                output_path=args.config_out,
            )
            print(f"Wrote {args.emit_config} MCP config: {target}")
        else:
            print(
                json.dumps(
                    render_editor_config(args.emit_config, remote_url=args.remote_url),
                    indent=2,
                )
            )
        return 0

    if args.sync_cache:
        synced = 0
        for name in tool_trellis_get_standard({"name": "all"}, workspace_root=root)[
            "content"
        ][0]["text"].splitlines():
            if not name.startswith("- `"):
                continue
            standard = name.split("`")[1]
            result = tool_trellis_get_standard({"name": standard}, workspace_root=root)
            if not result.get("isError"):
                synced += 1
        print(f"Cached {synced} standards under {root / '.trellis_cache' / 'standards'}")
        return 0

    if args.usage_report:
        usage_path = args.usage_file
        analytics_args: dict[str, object] = {
            "budget_tokens": args.budget_tokens,
            "cost_per_1k_tokens": args.cost_per_1k_tokens,
        }
        if usage_path is not None:
            analytics_args["usage_file"] = str(usage_path)
        report = tool_trellis_analytics(analytics_args, workspace_root=root)
        print(report["content"][0]["text"])
        return 1 if report.get("metadata", {}).get("verdict") == "EXCEEDED" else 0

    if args.rotate_key:
        store = TrellisKeyStore(resolved_keys_file)
        existing = store.find_active(args.rotate_key)
        if existing is None:
            print(f"Error: Active key not found for '{args.rotate_key}'.", file=sys.stderr)
            return 1
        store.revoke_key(args.rotate_key)
        created = store.generate_key(
            label=str(existing.get("label") or args.rotate_key),
            role=str(existing.get("role") or "member"),
            expires_days=args.expires_days,
        )
        created["rotated_from"] = existing.get("key_id")
        print(json.dumps(created, indent=2))
        return 0

    if args.generate_key:
        store = TrellisKeyStore(resolved_keys_file)
        parsed_scopes = (
            [s.strip() for s in args.scopes.split(",") if s.strip()]
            if args.scopes
            else None
        )
        created = store.generate_key(
            label=args.generate_key,
            role=args.role,
            expires_days=args.expires_days,
            scopes=parsed_scopes,
        )
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
        print(
            install_remote(
                server_url=args.install_remote,
                api_key=args.api_key,
                signing_key=args.bundle_signing_key,
            )
        )
        return 0

    if args.serve_http:
        http_srv = TrellisHTTPServer(
            host=args.host,
            port=args.port,
            api_key=args.api_key,
            workspace_root=root,
            auto_generate_key=args.auto_generate_key,
            keys_file=resolved_keys_file,
            tls_cert=args.tls_cert,
            tls_key=args.tls_key,
            bundle_signing_key=args.bundle_signing_key,
            max_body_bytes=args.max_body_bytes,
            rate_limit=args.rate_limit,
            rate_window_sec=args.rate_window_sec,
            request_timeout_sec=args.request_timeout,
            allowed_origins=args.allowed_origin,
            audit_log=args.audit_log,
        )
        http_srv.serve_forever()
        return 0

    if args.doctor:
        res = tool_trellis_doctor(
            {"workspace_path": str(root), "auto_fix": args.fix, "dry_run": args.dry_run},
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
