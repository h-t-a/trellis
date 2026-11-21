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


if __name__ == "__main__":
    unittest.main()
