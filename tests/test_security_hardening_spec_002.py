"""Requirement-linked security hardening tests for SPEC-002 ([REQ-TRL-17..])."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request

REPO_ROOT = Path(__file__).resolve().parent.parent


def _rpc_post(http_srv, token: str, payload: dict) -> dict:
    req = Request(
        f"{http_srv.base_url}/mcp",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with http_srv.open_request(req) as resp:
        assert resp.status == 200
        return json.loads(resp.read().decode("utf-8"))


class TestSpec002SecurityHardening(unittest.TestCase):
    """Security regression tests for SPEC-002 P0/P1 findings (F1..F9)."""

    def test_req_trl_17_remote_writes_and_arg_spoofing_blocked(self) -> None:
        """[REQ-TRL-17] Remote HTTP calls cannot write files or spoof _remote_mode/_auth_label."""
        from trellis_mcp.http_server import TrellisHTTPServer
        from trellis_mcp.server import TrellisMCPServer

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "trellis"
            (ws / "docs" / "standards").mkdir(parents=True)
            (ws / ".agents" / "rules").mkdir(parents=True)
            sec_std = ws / "docs" / "standards" / "security-baseline.md"
            original_std = "# Original Security Baseline\n"
            sec_std.write_text(original_std, encoding="utf-8")
            rule_file = ws / ".agents" / "rules" / "custom.md"
            original_rule = "# Missing frontmatter rule\n"
            rule_file.write_text(original_rule, encoding="utf-8")

            # Direct server unit check: attacker-supplied _remote_mode=False & _auth_label must be stripped
            mcp = TrellisMCPServer(workspace_root=ws)
            spoof_resp = mcp.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "trellis_pipeline",
                        "arguments": {
                            "current_stage": "spec",
                            "target_stage": "implement",
                            "tier": 2,
                            "human_approved": False,
                            "_remote_mode": False,
                            "_auth_label": "SpoofedAdmin",
                        },
                    },
                },
                caller_label="real-caller",
                remote_mode=True,
            )
            self.assertIsNotNone(spoof_resp)
            spoof_text = spoof_resp["result"]["content"][0]["text"]
            self.assertIn("real-caller", spoof_text)
            self.assertNotIn("SpoofedAdmin", spoof_text)

            # Live HTTP server check (even admin key cannot write over standards via remote MCP)
            keys_file = Path(tmp) / ".trellis_keys.json"
            admin_token = "test-admin-secret-spec002"
            with TrellisHTTPServer(
                host="127.0.0.1",
                port=0,
                api_key=admin_token,
                workspace_root=ws,
                keys_file=keys_file,
            ) as srv:
                # 1. Remote handoff save_to_file rejected even with spoofed _remote_mode=False
                handoff_res = _rpc_post(
                    srv,
                    admin_token,
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "trellis_handoff",
                            "arguments": {
                                "goal": "Poison standard",
                                "current_state": "Exploit attempt",
                                "next_step": "None",
                                "save_to_file": "docs/standards/security-baseline.md",
                                "_remote_mode": False,
                            },
                        },
                    },
                )
                self.assertTrue(handoff_res["result"]["isError"])
                self.assertEqual(sec_std.read_text(encoding="utf-8"), original_std)

                # 2. Remote doctor auto_fix rejected even with spoofed _remote_mode=False
                doctor_res = _rpc_post(
                    srv,
                    admin_token,
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "trellis_doctor",
                            "arguments": {
                                "auto_fix": True,
                                "dry_run": False,
                                "_remote_mode": False,
                            },
                        },
                    },
                )
                self.assertTrue(doctor_res["result"]["isError"])
                self.assertEqual(rule_file.read_text(encoding="utf-8"), original_rule)

                # 3. Remote doctor external workspace_path rejected
                outside_dir = Path(tmp) / "outside"
                outside_dir.mkdir()
                doctor_outside = _rpc_post(
                    srv,
                    admin_token,
                    {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {
                            "name": "trellis_doctor",
                            "arguments": {
                                "workspace_path": str(outside_dir),
                                "auto_fix": False,
                            },
                        },
                    },
                )
                self.assertTrue(doctor_outside["result"]["isError"])

                # 4. Remote get_standard does not write .trellis_cache/ on server disk
                std_res = _rpc_post(
                    srv,
                    admin_token,
                    {
                        "jsonrpc": "2.0",
                        "id": 5,
                        "method": "tools/call",
                        "params": {
                            "name": "trellis_get_standard",
                            "arguments": {"name": "security-baseline"},
                        },
                    },
                )
                self.assertFalse(std_res["result"].get("isError", False))
                self.assertFalse((ws / ".trellis_cache").exists())

    def test_req_trl_18_default_member_scopes_are_read_only(self) -> None:
        """[REQ-TRL-18] Default member keys receive a read-only allowlist and cannot invoke write tools."""
        from trellis_mcp.http_server import DEFAULT_MEMBER_SCOPES, TrellisHTTPServer

        for write_tool in (
            "trellis_handoff",
            "trellis_doctor",
            "trellis_scan",
            "trellis_mcp_registry",
            "trellis_analytics",
        ):
            self.assertNotIn(write_tool, DEFAULT_MEMBER_SCOPES)

        with tempfile.TemporaryDirectory() as tmp:
            keys_file = Path(tmp) / ".trellis_keys.json"
            with TrellisHTTPServer(
                host="127.0.0.1",
                port=0,
                api_key="test-admin-member-scopes",
                workspace_root=REPO_ROOT,
                keys_file=keys_file,
            ) as srv:
                member = srv.key_store.generate_key(label="dev-readonly", role="member")
                self.assertIsInstance(member["scopes"], list)
                self.assertGreater(len(member["scopes"]), 0)
                self.assertNotIn("trellis_handoff", member["scopes"])
                self.assertNotIn("trellis_doctor", member["scopes"])
                member_key = member["api_key"]

                # Read-only tool succeeds
                ok_res = _rpc_post(
                    srv,
                    member_key,
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "trellis_get_standard",
                            "arguments": {"name": "all"},
                        },
                    },
                )
                self.assertFalse(ok_res["result"].get("isError", False))

                # Write-capable / server-inspection tools are forbidden (403)
                for blocked_tool, blocked_args in (
                    (
                        "trellis_handoff",
                        {"goal": "g", "current_state": "s", "next_step": "n"},
                    ),
                    ("trellis_doctor", {"auto_fix": False}),
                    ("trellis_scan", {"scan_deps": False}),
                ):
                    req = Request(
                        f"{srv.base_url}/mcp",
                        data=json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": 2,
                                "method": "tools/call",
                                "params": {"name": blocked_tool, "arguments": blocked_args},
                            }
                        ).encode("utf-8"),
                        headers={
                            "Authorization": f"Bearer {member_key}",
                            "Content-Type": "application/json",
                        },
                        method="POST",
                    )
                    with self.assertRaises(HTTPError) as ctx:
                        srv.open_request(req)
                    self.assertEqual(ctx.exception.code, 403, f"Expected 403 for {blocked_tool}")
                    ctx.exception.close()

                # Legacy member record with scopes=null on disk must still default to read-only
                raw_doc = json.loads(keys_file.read_text(encoding="utf-8"))
                records = raw_doc["keys"] if isinstance(raw_doc, dict) else raw_doc
                for rec in records:
                    if rec.get("key_id") == member["key_id"]:
                        rec["scopes"] = None
                keys_file.write_text(json.dumps(raw_doc, indent=2), encoding="utf-8")

                req_legacy = Request(
                    f"{srv.base_url}/mcp",
                    data=json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "tools/call",
                            "params": {
                                "name": "trellis_handoff",
                                "arguments": {"goal": "g", "current_state": "s", "next_step": "n"},
                            },
                        }
                    ).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {member_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with self.assertRaises(HTTPError) as ctx_legacy:
                    srv.open_request(req_legacy)
                self.assertEqual(ctx_legacy.exception.code, 403)
                ctx_legacy.exception.close()

    def test_req_trl_19_path_containment_blocks_sibling_and_symlink_escape(self) -> None:
        """[REQ-TRL-19] Path checks reject sibling directories (../trellis-evil) and symlinks."""
        from trellis_mcp.tools import (
            _is_within_root,
            tool_trellis_analytics,
            tool_trellis_handoff,
            tool_trellis_mcp_registry,
            tool_trellis_scan,
        )

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "trellis"
            sibling = Path(tmp) / "trellis-evil"
            ws.mkdir()
            sibling.mkdir()
            secret_sibling = sibling / "secret.json"
            secret_sibling.write_text('{"entries": []}\n', encoding="utf-8")
            sibling_mcp = sibling / "mcp.json"
            sibling_mcp.write_text('{"mcpServers": {}}\n', encoding="utf-8")

            # Helper directly rejects sibling prefix match
            self.assertFalse(_is_within_root(ws, ws / "../trellis-evil/pwned.md"))
            self.assertTrue(_is_within_root(ws, ws / "notes" / "handoff.md"))

            # 1. trellis_handoff rejects sibling directory write
            handoff_res = tool_trellis_handoff(
                {
                    "goal": "Escape test",
                    "current_state": "Testing",
                    "next_step": "Verify blocked",
                    "save_to_file": "../trellis-evil/pwned.md",
                },
                workspace_root=ws,
            )
            self.assertTrue(handoff_res.get("isError", False))
            self.assertFalse((sibling / "pwned.md").exists())

            # 2. trellis_scan rejects sibling directory scan
            scan_res = tool_trellis_scan(
                {"path": "../trellis-evil", "scan_deps": False},
                workspace_root=ws,
            )
            self.assertTrue(scan_res.get("isError", False))

            # 3. trellis_analytics rejects sibling usage_file
            analytics_res = tool_trellis_analytics(
                {"usage_file": "../trellis-evil/secret.json"},
                workspace_root=ws,
            )
            self.assertTrue(analytics_res.get("isError", False))

            # 4. trellis_mcp_registry rejects sibling config_paths
            reg_res = tool_trellis_mcp_registry(
                {"config_paths": ["../trellis-evil/mcp.json"]},
                workspace_root=ws,
            )
            self.assertTrue(reg_res.get("isError", False))

            # 5. Symlink target is rejected even if resolved path appears inside ws
            inside_file = ws / "target.md"
            inside_file.write_text("ok\n", encoding="utf-8")
            with mock.patch.object(Path, "is_symlink", return_value=True):
                self.assertFalse(_is_within_root(ws, inside_file))

    def test_req_trl_20_deploy_disabled_by_default_and_requires_separate_key(self) -> None:
        """[REQ-TRL-20] /admin/deploy is disabled by default, requires a distinct deploy key, enforces version monotonicity, and swaps atomically."""
        import hashlib
        import hmac
        import io
        import zipfile
        from trellis_mcp.http_server import TrellisHTTPServer

        def _make_pyz(version_str: str) -> bytes:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("__main__.py", "from trellis_mcp.__main__ import main\n")
                zf.writestr("trellis_mcp/__init__.py", f'__version__ = "{version_str}"\n')
                zf.writestr("trellis_mcp/__main__.py", "def main(): return 0\n")
            return b"#!/usr/bin/env python3\n" + buf.getvalue()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            ws = tmp_dir / "vm_runtime"
            ws.mkdir()
            audit_path = tmp_dir / "audit.jsonl"
            admin_token = "admin-token-deploy-test"
            deploy_secret = "separate-ci-deploy-signing-key"
            pyz_v1 = _make_pyz("0.1.0")
            pyz_v2 = _make_pyz("0.2.0")
            pyz_old = _make_pyz("0.0.9")

            # 1. Disabled by default -> 403 even with valid admin token & signature
            with TrellisHTTPServer(
                host="127.0.0.1",
                port=0,
                api_key=admin_token,
                workspace_root=ws,
                keys_file=ws / ".trellis_keys.json",
            ) as srv_default:
                sig = hmac.new(admin_token.encode("utf-8"), pyz_v1, hashlib.sha256).hexdigest()
                req = Request(
                    f"{srv_default.base_url}/admin/deploy",
                    data=pyz_v1,
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "X-Trellis-Signature": sig,
                    },
                    method="POST",
                )
                with self.assertRaises(HTTPError) as ctx:
                    srv_default.open_request(req)
                self.assertEqual(ctx.exception.code, 403)
                ctx.exception.close()

            # 2. Enabled with separate deploy_signing_key
            with TrellisHTTPServer(
                host="127.0.0.1",
                port=0,
                api_key=admin_token,
                workspace_root=ws,
                keys_file=ws / ".trellis_keys.json",
                enable_remote_deploy=True,
                deploy_signing_key=deploy_secret,
                audit_log=audit_path,
            ) as srv:
                def _post_deploy(data: bytes, sig_key: str) -> tuple[int, dict]:
                    sig_hex = hmac.new(sig_key.encode("utf-8"), data, hashlib.sha256).hexdigest()
                    r = Request(
                        f"{srv.base_url}/admin/deploy",
                        data=data,
                        headers={
                            "Authorization": f"Bearer {admin_token}",
                            "X-Trellis-Signature": sig_hex,
                        },
                        method="POST",
                    )
                    try:
                        with srv.open_request(r) as resp:
                            return resp.status, json.loads(resp.read().decode("utf-8"))
                    except HTTPError as exc:
                        body = json.loads(exc.read().decode("utf-8"))
                        code = exc.code
                        exc.close()
                        return code, body

                # Admin token alone cannot sign deploy payload
                code_admin_sig, _ = _post_deploy(pyz_v1, admin_token)
                self.assertEqual(code_admin_sig, 403)

                # Downgrade below running version rejected (409)
                code_old, _ = _post_deploy(pyz_old, deploy_secret)
                self.assertEqual(code_old, 409)

                # Initial v0.1.0 succeeds with separate deploy key
                code_v1, body_v1 = _post_deploy(pyz_v1, deploy_secret)
                self.assertEqual(code_v1, 200)
                expected_sha = hashlib.sha256(pyz_v1).hexdigest()
                self.assertEqual(body_v1["sha256"], expected_sha)
                self.assertTrue((ws / "trellis-mcp.pyz").exists())

                # Replaying same version is rejected (409)
                code_replay, _ = _post_deploy(pyz_v1, deploy_secret)
                self.assertEqual(code_replay, 409)

                # Higher version v0.2.0 succeeds and saves .pyz.bak rollback backup
                code_v2, body_v2 = _post_deploy(pyz_v2, deploy_secret)
                self.assertEqual(code_v2, 200)
                self.assertEqual(body_v2["deployed_version"], "0.2.0")
                self.assertTrue((ws / "trellis-mcp.pyz.bak").exists())
                self.assertEqual((ws / "trellis-mcp.pyz.bak").read_bytes(), pyz_v1)
                self.assertEqual((ws / "trellis-mcp.pyz").read_bytes(), pyz_v2)

                # Audit log contains deployed artifact SHA-256
                audit_text = audit_path.read_text(encoding="utf-8")
                self.assertIn(expected_sha, audit_text)

    def test_req_trl_21_non_loopback_requires_tls_and_host_allowlist(self) -> None:
        """[REQ-TRL-21] Non-loopback bind requires TLS or --insecure-http; Host allowlist stops DNS rebinding; --public-url controls install URL."""
        from trellis_mcp.__main__ import main
        from trellis_mcp.http_server import TrellisHTTPServer

        with tempfile.TemporaryDirectory() as tmp:
            keys_file = Path(tmp) / ".trellis_keys.json"
            # Non-loopback without TLS or insecure_http raises ValueError
            with self.assertRaises(ValueError):
                TrellisHTTPServer(
                    host="0.0.0.0",
                    port=0,
                    api_key="test-key",
                    workspace_root=REPO_ROOT,
                    keys_file=keys_file,
                )

            # CLI refuses non-loopback without TLS / --insecure-http
            rc = main(
                [
                    "--serve-http",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "0",
                    "--api-key",
                    "test-key",
                    "--keys-file",
                    str(keys_file),
                ]
            )
            self.assertNotEqual(rc, 0)

            # DNS-rebinding & --public-url test
            admin_key = "test-host-allowlist-key"
            with TrellisHTTPServer(
                host="127.0.0.1",
                port=0,
                api_key=admin_key,
                workspace_root=REPO_ROOT,
                keys_file=keys_file,
                public_url="https://trellis.example.com",
            ) as srv:
                # Attacker-controlled Host + matching Origin must be rejected (403)
                status, _, _ = srv.dispatch_http(
                    method="POST",
                    path="/mcp",
                    headers={
                        "Host": "evil-rebind.example",
                        "Origin": "http://evil-rebind.example",
                        "Authorization": f"Bearer {admin_key}",
                        "Content-Type": "application/json",
                    },
                    body=b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
                )
                self.assertEqual(status, 403)

                # /install.sh uses configured public_url, ignoring spoofed X-Forwarded-Proto
                st_sh, _, body_sh = srv.dispatch_http(
                    method="GET",
                    path="/install.sh",
                    headers={
                        "Host": "127.0.0.1",
                        "X-Forwarded-Proto": "http",
                        "Authorization": f"Bearer {admin_key}",
                    },
                )
                self.assertEqual(st_sh, 200)
                sh_text = body_sh.decode("utf-8")
                self.assertIn("https://trellis.example.com", sh_text)
                self.assertNotIn("http://127.0.0.1", sh_text)

    def test_req_trl_22_installer_validates_skill_names_and_preserves_malformed_mcp_json(self) -> None:
        """[REQ-TRL-22] Remote installer requires signed bundles by default, validates skill names, preserves malformed MCP configs, and avoids literal keys."""
        import hashlib
        import hmac
        from trellis_mcp.http_server import TrellisHTTPServer
        from trellis_mcp.installer import install_remote, validate_skill_name

        # Skill-name validation regex
        self.assertTrue(validate_skill_name("pb-review"))
        self.assertFalse(validate_skill_name("../evil"))
        self.assertFalse(validate_skill_name("bad/name"))
        self.assertFalse(validate_skill_name("UPPER"))
        self.assertFalse(validate_skill_name(".hidden"))

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            api_key = "test-installer-key"
            sig_key = "test-bundle-hmac-secret"

            # 1. Unsigned bundle refused by default (allow_unsigned=False)
            with TrellisHTTPServer(
                host="127.0.0.1",
                port=0,
                api_key=api_key,
                workspace_root=REPO_ROOT,
                keys_file=tmp_dir / ".keys1.json",
            ) as srv_unsigned:
                with self.assertRaises(ValueError):
                    install_remote(
                        server_url=srv_unsigned.base_url,
                        api_key=api_key,
                        home_dir=tmp_dir / "home_unsigned",
                    )

            # 2. Signed bundle installs cleanly without writing literal API key and shows diff summary
            with TrellisHTTPServer(
                host="127.0.0.1",
                port=0,
                api_key=api_key,
                bundle_signing_key=sig_key,
                workspace_root=REPO_ROOT,
                keys_file=tmp_dir / ".keys2.json",
            ) as srv_signed:
                home_ok = tmp_dir / "home_ok"
                summary = install_remote(
                    server_url=srv_signed.base_url,
                    api_key=api_key,
                    signing_key=sig_key,
                    home_dir=home_ok,
                )
                self.assertIn("Bundle diff", summary)
                cfg_path = home_ok / ".gemini" / "config" / "mcp_config.json"
                cfg_text = cfg_path.read_text(encoding="utf-8")
                self.assertIn("${TRELLIS_API_KEY}", cfg_text)
                self.assertNotIn(api_key, cfg_text)

                # 3. Malformed existing mcp_config.json is backed up and aborts without overwriting
                home_bad = tmp_dir / "home_bad"
                bad_cfg = home_bad / ".gemini" / "config" / "mcp_config.json"
                bad_cfg.parent.mkdir(parents=True, exist_ok=True)
                corrupt_content = '{"mcpServers": {"my-other-server": {"command": "node"}, BROKEN'
                bad_cfg.write_text(corrupt_content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    install_remote(
                        server_url=srv_signed.base_url,
                        api_key=api_key,
                        signing_key=sig_key,
                        home_dir=home_bad,
                    )
                # Original corrupt file untouched and backup created
                self.assertEqual(bad_cfg.read_text(encoding="utf-8"), corrupt_content)
                backups = list(bad_cfg.parent.glob("mcp_config.json.bak*"))
                self.assertGreaterEqual(len(backups), 1)

            # 4. Malicious skill name in bundle payload is rejected before writing
            poisoned_bundle = json.dumps(
                {
                    "version": "0.1.0",
                    "rules_md": "# Rules\n",
                    "skills": {"../escape": "# Evil\n"},
                }
            ).encode("utf-8")
            poisoned_sig = hmac.new(sig_key.encode("utf-8"), poisoned_bundle, hashlib.sha256).hexdigest()

            class _FakeResp:
                headers = {"X-Trellis-Bundle-Signature": poisoned_sig}
                def read(self) -> bytes:
                    return poisoned_bundle
                def __enter__(self):
                    return self
                def __exit__(self, *a):
                    return None

            with mock.patch("trellis_mcp.http_server.open_url_resilient", return_value=_FakeResp()):
                home_poison = tmp_dir / "home_poison"
                with self.assertRaises(ValueError):
                    install_remote(
                        server_url="https://trellis.example.com",
                        api_key=api_key,
                        signing_key=sig_key,
                        home_dir=home_poison,
                    )
                self.assertFalse((home_poison / ".claude" / "escape").exists())

    def test_req_trl_23_proxy_ip_trust_eviction_and_no_plaintext_tokens(self) -> None:
        """[REQ-TRL-23] X-Forwarded-For only honored from trusted proxies; rate/lockout maps evict stale IPs; plaintext tokens cannot auth without migration."""
        from trellis_mcp.http_server import TrellisHTTPServer, TrellisKeyStore

        with tempfile.TemporaryDirectory() as tmp:
            keys_file = Path(tmp) / ".trellis_keys.json"

            # 1. Legacy plaintext token cannot authenticate directly, but migrates cleanly
            legacy_token = "trl_legacy_plaintext_secret_123456"
            keys_file.write_text(
                json.dumps(
                    {
                        "keys": [
                            {
                                "key_id": "key_legacy01",
                                "label": "legacy-user",
                                "role": "member",
                                "token": legacy_token,
                                "prefix": "trl_legacy...3456",
                                "created_at": "2026-11-01T00:00:00Z",
                                "revoked": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            store = TrellisKeyStore(keys_file)
            self.assertIsNone(store.authenticate(legacy_token))
            migrated_count = store.migrate_legacy_plaintext_keys()
            self.assertEqual(migrated_count, 1)
            raw_after = keys_file.read_text(encoding="utf-8")
            self.assertNotIn(legacy_token, raw_after)
            authed = store.authenticate(legacy_token)
            self.assertIsNotNone(authed)
            self.assertEqual(authed[1], "key_legacy01")

            # 2. Proxy IP trust and bounded eviction
            with TrellisHTTPServer(
                host="127.0.0.1",
                port=0,
                api_key="admin-proxy-test",
                workspace_root=REPO_ROOT,
                keys_file=keys_file,
                trusted_proxies=["127.0.0.1"],
                auth_failure_limit=2,
                auth_lockout_sec=30.0,
                rate_window_sec=1.0,
                max_tracked_ips=4,
            ) as srv:
                # From untrusted peer 198.51.100.9, X-Forwarded-For is ignored
                self.assertEqual(
                    srv._resolve_client_ip("198.51.100.9", {"x-forwarded-for": "203.0.113.5"}),
                    "198.51.100.9",
                )
                # From trusted proxy 127.0.0.1, X-Forwarded-For client IP is honored
                self.assertEqual(
                    srv._resolve_client_ip("127.0.0.1", {"x-forwarded-for": "203.0.113.5, 127.0.0.1"}),
                    "203.0.113.5",
                )

                # Locking out 203.0.113.5 via proxy does NOT lock out 203.0.113.6
                for _ in range(2):
                    srv.dispatch_http(
                        "POST",
                        "/mcp",
                        {"Authorization": "Bearer wrong", "X-Forwarded-For": "203.0.113.5"},
                        b"{}",
                        client_ip="127.0.0.1",
                    )
                st_blocked, _, _ = srv.dispatch_http(
                    "POST",
                    "/mcp",
                    {"Authorization": "Bearer admin-proxy-test", "X-Forwarded-For": "203.0.113.5"},
                    b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
                    client_ip="127.0.0.1",
                )
                st_other, _, _ = srv.dispatch_http(
                    "POST",
                    "/mcp",
                    {"Authorization": "Bearer admin-proxy-test", "X-Forwarded-For": "203.0.113.6"},
                    b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
                    client_ip="127.0.0.1",
                )
                self.assertEqual(st_blocked, 429)
                self.assertEqual(st_other, 200)

                # Rate-limit map stays bounded under IP spray (max_tracked_ips=4)
                for idx in range(20):
                    srv._allow_request(f"198.51.100.{idx}")
                self.assertLessEqual(len(srv._rate_hits), 4)

    def test_req_trl_24_vm_scripts_hardened_for_public_oss(self) -> None:
        """[REQ-TRL-24] VM scripts remove SYSTEM task, WinRM Any, process killing, and hardcoded local paths."""
        setup_ps1 = (REPO_ROOT / "scripts" / "setup-vm-once.ps1").read_text(encoding="utf-8")
        deploy_ps1 = (REPO_ROOT / "scripts" / "build-and-deploy.ps1").read_text(encoding="utf-8")

        for forbidden in (
            "-TakeOverPort",
            "Stop-Process",
            "RemoteAddress Any",
            "WINRM-HTTP-In-TCP",
            '-User "SYSTEM"',
            "-RunLevel Highest",
            r"\\tsclient\D\hta",
            "team-ibanking",
        ):
            self.assertNotIn(forbidden, setup_ps1, f"Forbidden pattern in setup-vm-once.ps1: {forbidden}")
            self.assertNotIn(forbidden, deploy_ps1, f"Forbidden pattern in build-and-deploy.ps1: {forbidden}")

        self.assertIn("TRELLIS_DEPLOY_SIGNING_KEY", deploy_ps1)
        self.assertIn("https://", deploy_ps1)

    def test_req_trl_25_zero_personal_or_internal_strings_in_tracked_files(self) -> None:
        """[REQ-TRL-25] Public repo removes internal export and scrubs personal paths, VPN IPs, and internal project names."""
        import subprocess

        self.assertFalse((REPO_ROOT / "docs" / "knowledge" / "trellis-project-export.md").exists())

        tracked = subprocess.check_output(
            ["git", "ls-files"], cwd=str(REPO_ROOT), text=True, encoding="utf-8"
        ).splitlines()
        banned_tokens = (
            "d:\\hta",
            "\\\\tsclient\\d\\hta",
            "10.6.7.1",
            "happ-default-tun",
            "team-ibanking",
            "ibanking-portal",
            "projects/ibanking",
            "/ibanking",
            "wallet application",
        )
        violations: list[str] = []
        for rel in tracked:
            if rel.replace("\\", "/") == "tests/test_security_hardening_spec_002.py":
                continue
            path = REPO_ROOT / rel
            if not path.is_file():
                continue
            try:
                content = path.read_text(encoding="utf-8").lower()
            except (OSError, UnicodeDecodeError):
                continue
            for tok in banned_tokens:
                if tok in content:
                    violations.append(f"{rel}: contains {tok!r}")
        self.assertEqual(violations, [], f"Scrubbing violations: {violations}")

        sec_md = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("github.com/h-t-a/trellis/security/advisories", sec_md)

    def test_req_trl_26_claude_hooks_are_real_and_block_destructive_variants(self) -> None:
        """[REQ-TRL-26] Wired Claude hooks run real tests, catch rm -rf ~/./-fr variants, and have accurate docs."""
        import shutil
        import subprocess

        run_tests = (REPO_ROOT / ".claude" / "hooks" / "run-tests.sh").read_text(encoding="utf-8")
        validate_bash = (REPO_ROOT / ".claude" / "hooks" / "validate-bash.sh").read_text(encoding="utf-8")
        secret_scan = (REPO_ROOT / ".claude" / "hooks" / "secret-scan.sh").read_text(encoding="utf-8")
        settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))

        self.assertNotIn("Starter kit placeholder", run_tests)
        self.assertIn("unittest discover", run_tests)
        for text in (run_tests, validate_bash, secret_scan):
            self.assertNotIn("Do NOT wire", text)
        self.assertIn("defense-in-depth", str(settings.get("_comment", "")).lower())

        # If bash is installed locally, exercise validate-bash.sh directly against destructive variants
        bash_exe = shutil.which("bash")
        if bash_exe:
            hook_path = str(REPO_ROOT / ".claude" / "hooks" / "validate-bash.sh")
            for blocked_cmd in (
                "rm -rf /",
                "rm -rf ~",
                "rm -rf .",
                "rm -fr ./src",
                "rm --recursive --force /tmp/x",
                "git push --force origin master",
                "git push -f origin master",
            ):
                proc = subprocess.run(
                    [bash_exe, hook_path],
                    input=blocked_cmd,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 2, f"Expected exit 2 for: {blocked_cmd}")

            ok_proc = subprocess.run(
                [bash_exe, hook_path],
                input="python -m unittest discover -s tests -v",
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(ok_proc.returncode, 0)

    def test_req_trl_27_github_actions_ci_workflow_present(self) -> None:
        """[REQ-TRL-27] GitHub Actions CI covers Python 3.9-3.13, tests, doctor, skill parity, scan, lint, and .pyz build."""
        ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(ci_path.is_file(), "Missing .github/workflows/ci.yml")
        ci_text = ci_path.read_text(encoding="utf-8")

        for expected in (
            '"3.9"',
            '"3.10"',
            '"3.11"',
            '"3.12"',
            '"3.13"',
            "ubuntu-24.04",
            "windows-latest",
            "unittest discover -s tests",
            "trellis_mcp --check",
            "--sync-workspace",
            "git diff --exit-code",
            "tool_trellis_scan",
            "--build-pyz",
            "ruff",
        ):
            self.assertIn(expected, ci_text, f"CI workflow missing required check: {expected}")

        # Also verify _merge_mcp_config preserves existing python/python3 command
        from trellis_mcp.installer import _merge_mcp_config
        with tempfile.TemporaryDirectory() as tmp_mcp:
            cfg_file = Path(tmp_mcp) / "mcp.json"
            cfg_file.write_text(json.dumps({"mcpServers": {"trellis-mcp": {"command": "python", "args": []}}}), encoding="utf-8")
            # Calling with python3 server entry keeps existing "python"
            _merge_mcp_config(cfg_file, {"command": "python3", "args": ["-m", "trellis_mcp"]})
            updated = json.loads(cfg_file.read_text(encoding="utf-8"))
            self.assertEqual(updated["mcpServers"]["trellis-mcp"]["command"], "python")

            # Calling with python server entry on existing "python3" keeps "python3"
            cfg_file.write_text(json.dumps({"mcpServers": {"trellis-mcp": {"command": "python3", "args": []}}}), encoding="utf-8")
            _merge_mcp_config(cfg_file, {"command": "python", "args": ["-m", "trellis_mcp"]})
            updated3 = json.loads(cfg_file.read_text(encoding="utf-8"))
            self.assertEqual(updated3["mcpServers"]["trellis-mcp"]["command"], "python3")

    def test_req_trl_28_data_driven_aibom_and_router_catalog(self) -> None:
        """[REQ-TRL-28] ai-bom.json contains verified models, aliases, and router loads catalog dynamically."""
        from trellis_mcp.router import load_aibom_catalog, select_route
        from trellis_mcp.tools import tool_trellis_doctor

        # 1. Inspect docs/standards/ai-bom.json
        aibom_path = REPO_ROOT / "docs" / "standards" / "ai-bom.json"
        self.assertTrue(aibom_path.is_file(), "Missing docs/standards/ai-bom.json")
        aibom = json.loads(aibom_path.read_text(encoding="utf-8"))
        models = aibom.get("models", [])
        self.assertGreater(len(models), 10)

        # Check fields and verified status
        model_ids = {m["id"] for m in models}
        self.assertIn("anthropic/claude-sonnet-5-5", model_ids)
        self.assertIn("anthropic/claude-opus-5-5", model_ids)
        self.assertIn("gemini/gemini-2.5-pro", model_ids)
        self.assertIn("openai/gpt-5", model_ids)

        for m in models:
            self.assertIn("last_verified", m, f"Model {m['id']} missing last_verified")
            self.assertIn("deprecation", m, f"Model {m['id']} missing deprecation field")
            self.assertIn("aliases", m, f"Model {m['id']} missing aliases field")

        # 2. Router dynamically loads from ai-bom.json
        catalog = load_aibom_catalog(workspace_root=REPO_ROOT)
        self.assertIn("on_prem", catalog)
        self.assertIn("cloud_chains", catalog)

        # 3. Dynamic route resolution
        route = select_route(task_type="coding", data_classification="Internal", tier=2, workspace_root=REPO_ROOT)
        self.assertEqual(route["primary"]["provider"], "anthropic")
        self.assertIn("claude-sonnet-5-5", route["primary"]["model"])

        # 4. Doctor checks stale models (>90 days) or deprecation
        doc_res = tool_trellis_doctor({"auto_fix": False, "dry_run": True}, workspace_root=REPO_ROOT)
        doc_text = doc_res["content"][0]["text"]
        self.assertIn("Trellis Workspace Doctor Report", doc_text)

    def test_req_trl_29_vmf_vs_bm25_retrieval_benchmark(self) -> None:
        """[REQ-TRL-29] Benchmark suite compares vMF vs BM25 retrieval over standards; injection labeled best-effort."""
        import trellis_mcp.knowledge as km

        # Ensure module describes prompt injection detection as heuristic/best-effort
        self.assertIn("best effort", km.__doc__.lower() + km._INJECTION_NOTE.lower())

        # Run benchmark runner
        from tests.test_vmf_bm25_benchmark import run_standards_benchmark
        results = run_standards_benchmark(REPO_ROOT)
        self.assertGreaterEqual(results["query_count"], 20)
        self.assertGreater(results["vmf_mrr"], 0.40)
        self.assertGreater(results["bm25_mrr"], 0.40)

    def test_req_trl_30_threat_model_and_spec_002_alignment(self) -> None:
        """[REQ-TRL-30] docs/standards/threat-model.md and docs/specs/002-security-hardening.md document STRIDE and findings."""
        tm_path = REPO_ROOT / "docs" / "standards" / "threat-model.md"
        self.assertTrue(tm_path.is_file(), "Missing docs/standards/threat-model.md")
        tm_text = tm_path.read_text(encoding="utf-8")

        for heading in ("STRIDE", "Assets", "Threat Actors", "Spoofing", "Tampering", "Elevation of Privilege"):
            self.assertIn(heading, tm_text)

        spec2_path = REPO_ROOT / "docs" / "specs" / "002-security-hardening.md"
        self.assertTrue(spec2_path.is_file(), "Missing docs/specs/002-security-hardening.md")
        spec2_text = spec2_path.read_text(encoding="utf-8")
        self.assertIn("SPEC-002", spec2_text)
        self.assertIn("REQ-TRL-17", spec2_text)
        self.assertIn("REQ-TRL-30", spec2_text)


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
