"""Automated unit and stdio integration tests for the trellis-mcp server and installer.

Verifies requirements:
- [REQ-MCP-01]: Zero-dependency Python MCP JSON-RPC 2.0 server over stdio
- [REQ-MCP-02]: 8 callable MCP tools with P0/P1 safety & cost guards (F02, F03, F04, F10, F12)
- [REQ-MCP-03]: Cross-device workspace sync & global device installer
- [REQ-MCP-04]: Requirement-linked automated verification
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import tempfile
import unittest
from pathlib import Path

from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from trellis_mcp.http_server import TrellisHTTPServer
from trellis_mcp.installer import install_global, install_remote, sync_workspace
from trellis_mcp.server import TrellisMCPServer
from trellis_mcp.tools import (
    tool_trellis_budget,
    tool_trellis_doctor,
    tool_trellis_enhance,
    tool_trellis_get_standard,
    tool_trellis_handoff,
    tool_trellis_rca,
    tool_trellis_review,
    tool_trellis_spec,
)


class TestTrellisMCPServer(unittest.TestCase):
    """Tests for [REQ-MCP-01] through [REQ-MCP-08]."""

    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parent.parent
        self.server = TrellisMCPServer(workspace_root=self.repo_root)

    def test_req_mcp_01_initialize_and_tools_list(self) -> None:
        """[REQ-MCP-01] Verify MCP JSON-RPC initialize, tools/list, resources/list, and prompts/list."""
        init_resp = self.server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
            }
        )
        self.assertIsNotNone(init_resp)
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "trellis-mcp")
        self.assertIn("tools", init_resp["result"]["capabilities"])
        self.assertIn("resources", init_resp["result"]["capabilities"])
        self.assertIn("prompts", init_resp["result"]["capabilities"])

        tools_resp = self.server.handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        tool_names = {t["name"] for t in tools_resp["result"]["tools"]}
        expected_tools = {
            "trellis_get_standard",
            "trellis_rca",
            "trellis_spec",
            "trellis_enhance",
            "trellis_budget",
            "trellis_handoff",
            "trellis_review",
            "trellis_doctor",
        }
        self.assertEqual(tool_names, expected_tools)

        resources_resp = self.server.handle_request(
            {"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}}
        )
        uris = {r["uri"] for r in resources_resp["result"]["resources"]}
        self.assertIn("trellis://standards/testing-standard", uris)
        self.assertIn("trellis://standards/rca-playbook", uris)

        prompts_resp = self.server.handle_request(
            {"jsonrpc": "2.0", "id": 4, "method": "prompts/list", "params": {}}
        )
        prompt_names = {p["name"] for p in prompts_resp["result"]["prompts"]}
        self.assertIn("pb-rca", prompt_names)
        self.assertIn("pb-spec", prompt_names)
        self.assertIn("pb-enhance", prompt_names)
        self.assertIn("pb-review", prompt_names)

    def test_req_mcp_02_get_standard_returns_bundled_content(self) -> None:
        """[REQ-MCP-02] Verify trellis_get_standard returns authoritative standard content."""
        res = tool_trellis_get_standard(
            {"name": "rca-playbook"}, workspace_root=self.repo_root
        )
        self.assertFalse(res.get("isError", False))
        text = res["content"][0]["text"]
        self.assertIn("9-Step Fast RCA Sequence", text)
        self.assertIn("Tier 3 Log & Context Redaction Gate", text)

    def test_req_mcp_02_rca_blocks_unredacted_pii_and_secrets_f04(self) -> None:
        """[REQ-MCP-02] (F04) Verify trellis_rca blocks raw PAN/card numbers and secrets in logs."""
        unsafe_result = tool_trellis_rca(
            {
                "symptom": "Transfer endpoint returns 500 on card settlement",
                "evidence": "ERROR CardNumber=4532015112830366 Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret",
                "suspect_files": ["src/transfer/service.py"],
            }
        )
        self.assertTrue(unsafe_result.get("isError", False))
        self.assertIn("TIER 3 REDACTION BLOCK", unsafe_result["content"][0]["text"])

        safe_result = tool_trellis_rca(
            {
                "symptom": "Transfer endpoint returns 500 on concurrent settlement requests",
                "evidence": "DeadlockDetectedException at TransferRepository.java:142 (user=<USER_1>)",
                "suspect_files": ["src/transfer/TransferRepository.java"],
            }
        )
        self.assertFalse(safe_result.get("isError", False))
        self.assertIn("Hypotheses (Max 3)", safe_result["content"][0]["text"])
        self.assertIn("Concurrency, Locks & Idempotency", safe_result["content"][0]["text"])

    def test_req_mcp_02_budget_upgrades_single_file_tier2_to_class_m_f03(self) -> None:
        """[REQ-MCP-02] (F03) Verify trellis_budget refuses Class S for 1-file Tier 2/3 changes."""
        # A 1-file typo/doc fix in Tier 1 stays Class S
        tier1_res = tool_trellis_budget(
            {
                "task_description": "Rename local helper variable in date formatting utility",
                "file_count": 1,
                "touches_tier2_or_tier3": False,
            }
        )
        self.assertIn("Class S", tier1_res["content"][0]["text"])

        # A 1-file change touching auth/validation/schema must auto-upgrade to Class M!
        auth_res = tool_trellis_budget(
            {
                "task_description": "Update JWT token expiry validation in AuthFilter.java",
                "file_count": 1,
                "touches_tier2_or_tier3": False,
            }
        )
        text = auth_res["content"][0]["text"]
        self.assertIn("Class M", text)
        self.assertIn("auto-upgraded from Class S", text)

    def test_req_mcp_02_spec_supports_micro_and_full_tiers_f12(self) -> None:
        """[REQ-MCP-02] (F12) Verify trellis_spec generates Class M Micro-Spec and Class L Full Spec."""
        micro = tool_trellis_spec(
            {
                "spec_id": "SPEC-042",
                "title": "Add idempotency key header validation",
                "problem": "Duplicate transfer retries create duplicate ledger entries",
                "task_class": "M",
                "requirements": [
                    "Reject POST /transfers missing X-Idempotency-Key with HTTP 400",
                    "Replay cached response for duplicate X-Idempotency-Key within 24h",
                ],
            }
        )
        micro_text = micro["content"][0]["text"]
        self.assertIn("[REQ-042-01]", micro_text)
        self.assertIn("[REQ-042-02]", micro_text)
        self.assertIn("Part A: Core Micro-Spec", micro_text)
        self.assertNotIn("Part B: Extended Sections", micro_text)

        full = tool_trellis_spec(
            {
                "spec_id": "SPEC-099",
                "title": "Cross-region ledger shard migration",
                "problem": "Single DB shard saturates at 4,000 TPS",
                "task_class": "L",
                "requirements": ["Sustain 10,000 TPS with p95 < 500ms"],
            }
        )
        self.assertIn("Part B: Extended Sections", full["content"][0]["text"])

    def test_req_mcp_02_enhance_computes_littles_law_and_io_complexity_f10(self) -> None:
        """[REQ-MCP-02] (F10) Verify trellis_enhance computes Little's Law VUs and I/O complexity."""
        res = tool_trellis_enhance(
            {
                "target": "AccountBalanceService.getConsolidatedHistory",
                "tps": 1000,
                "response_time_sec": 0.25,
                "think_time_sec": 0.75,
                "data_size_n": 50000,
                "current_behavior": "Executes 1 query per transaction inside a for-loop (N+1)",
                "mode": "analyze",
            }
        )
        text = res["content"][0]["text"]
        self.assertIn("1000.0 VUs", text)
        self.assertIn("I/O & Lock Complexity", text)

    def test_req_mcp_02_review_detects_weakened_tests_secrets_and_bad_commit(self) -> None:
        """[REQ-MCP-02] Verify trellis_review flags skipped tests, secrets, and non-conventional commits."""
        bad_diff = """
+ @Disabled("temporarily skip failing test to unblock build")
+ const apiKey = "sk-live-1234567890abcdefghijklmnop";
"""
        res = tool_trellis_review(
            {
                "diff_text": bad_diff,
                "commit_message": "Fixed the transfer bug.",
                "spec_req_ids": ["REQ-042-01"],
            }
        )
        text = res["content"][0]["text"]
        self.assertIn("FAIL", text)
        self.assertIn("Tier 3 Test-Weakening", text)
        self.assertIn("Secret / Credential Pattern", text)
        self.assertIn("Commit Message Violation", text)
        self.assertIn("Missing Requirement Traceability", text)

    def test_req_mcp_02_doctor_detects_missing_rule_frontmatter_f02(self) -> None:
        """[REQ-MCP-02] (F02) Verify trellis_doctor flags .agents/rules/*.md missing YAML frontmatter."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules_dir = root / ".agents" / "rules"
            rules_dir.mkdir(parents=True)
            (rules_dir / "broken-rule.md").write_text("# Rule without frontmatter\n", encoding="utf-8")

            report = tool_trellis_doctor({"workspace_path": str(root), "auto_fix": False})
            self.assertIn("Missing YAML frontmatter", report["content"][0]["text"])

            fixed = tool_trellis_doctor({"workspace_path": str(root), "auto_fix": True})
            self.assertIn("Fixed", fixed["content"][0]["text"])
            updated = (rules_dir / "broken-rule.md").read_text(encoding="utf-8")
            self.assertTrue(updated.startswith("---\n"))
            self.assertIn("trigger: always_on", updated)

    def test_req_mcp_03_sync_workspace_and_install_global(self) -> None:
        """[REQ-MCP-03] Verify sync_workspace and install_global work portably across directories."""
        with tempfile.TemporaryDirectory() as tmp_home:
            home_path = Path(tmp_home)
            summary = install_global(repo_root=self.repo_root, home_dir=home_path)
            self.assertTrue(
                (home_path / ".gemini" / "config" / "plugins" / "trellis" / "plugin.json").exists()
            )
            self.assertTrue(
                (home_path / ".gemini" / "config" / "mcp_config.json").exists()
            )
            self.assertTrue(
                (home_path / ".claude" / "skills" / "pb-rca" / "SKILL.md").exists()
            )
            self.assertIn("trellis-mcp", summary)

    def test_req_mcp_05_06_http_server_bearer_auth_and_mcp_rpc(self) -> None:
        """[REQ-MCP-05, REQ-MCP-06] Verify HTTP MCP server enforces Authorization: Bearer <TEAM_API_KEY>."""
        test_key = "team-secret-key-987654321"
        with TrellisHTTPServer(
            host="127.0.0.1",
            port=0,
            api_key=test_key,
            workspace_root=self.repo_root,
        ) as http_srv:
            base_url = http_srv.base_url

            # 1. GET /healthz works without auth
            with http_srv.open_request(f"{base_url}/healthz") as health_resp:
                self.assertEqual(health_resp.status, 200)
                health_data = json.loads(health_resp.read().decode("utf-8"))
                self.assertEqual(health_data["status"], "ok")

            # 2. POST /mcp without Authorization header -> 401 Unauthorized
            unauth_req = Request(
                f"{base_url}/mcp",
                data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as ctx_missing:
                http_srv.open_request(unauth_req)
            self.assertEqual(ctx_missing.exception.code, 401)
            ctx_missing.exception.close()

            # 3. POST /mcp with wrong Bearer token -> 401 Unauthorized
            wrong_req = Request(
                f"{base_url}/mcp",
                data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer wrong-token",
                },
                method="POST",
            )
            with self.assertRaises(HTTPError) as ctx_wrong:
                http_srv.open_request(wrong_req)
            self.assertEqual(ctx_wrong.exception.code, 401)
            ctx_wrong.exception.close()

            # 4. POST /mcp with valid Authorization: Bearer <test_key> -> 200 OK
            valid_req = Request(
                f"{base_url}/mcp",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 10,
                        "method": "tools/call",
                        "params": {
                            "name": "trellis_budget",
                            "arguments": {
                                "task_description": "Add JWT bearer validation to HTTP server",
                                "file_count": 1,
                            },
                        },
                    }
                ).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {test_key}",
                },
                method="POST",
            )
            with http_srv.open_request(valid_req) as valid_resp:
                self.assertEqual(valid_resp.status, 200)
                rpc_body = json.loads(valid_resp.read().decode("utf-8"))
                self.assertIn("Class M", rpc_body["result"]["content"][0]["text"])

    def test_req_mcp_07_zero_clone_remote_bundle_and_install(self) -> None:
        """[REQ-MCP-07] Verify zero-clone remote client setup via HTTP server and remote trellis_doctor."""
        test_key = "team-secret-key-remote-install"
        with TrellisHTTPServer(
            host="127.0.0.1",
            port=0,
            api_key=test_key,
            workspace_root=self.repo_root,
        ) as http_srv:
            base_url = http_srv.base_url

            # Teammate installs from remote VM URL without cloning the repo
            with tempfile.TemporaryDirectory() as tmp_home:
                home_path = Path(tmp_home)
                summary = install_remote(
                    server_url=base_url,
                    api_key=test_key,
                    home_dir=home_path,
                )
                self.assertIn(f"{base_url}/mcp", summary)
                mcp_cfg = json.loads(
                    (home_path / ".gemini" / "config" / "mcp_config.json").read_text(encoding="utf-8")
                )
                entry = mcp_cfg["mcpServers"]["trellis-mcp"]
                self.assertEqual(entry["serverUrl"], f"{base_url}/mcp")
                self.assertIn("Authorization", entry["headers"])
                self.assertTrue(
                    (home_path / ".gemini" / "config" / "plugins" / "trellis" / "skills" / "pb-rca" / "SKILL.md").exists()
                )
                self.assertTrue(
                    (home_path / ".claude" / "skills" / "pb-rca" / "SKILL.md").exists()
                )

            # Remote trellis_doctor inspects inline files map without local disk access
            remote_doc = tool_trellis_doctor(
                {
                    "files": {
                        ".agents/rules/custom-rule.md": "# Rule missing frontmatter\n",
                    },
                    "auto_fix": True,
                }
            )
            doc_text = remote_doc["content"][0]["text"]
            self.assertIn("Missing YAML frontmatter", doc_text)
            self.assertIn("trigger: always_on", doc_text)


    def test_req_mcp_08_auto_generate_admin_key_and_issue_team_keys(self) -> None:
        """[REQ-MCP-08-01..05] Verify admin key auto-generation, team member key issuing, RBAC, and revocation."""
        with tempfile.TemporaryDirectory() as tmp:
            keys_file = Path(tmp) / ".trellis_keys.json"
            with TrellisHTTPServer(
                host="127.0.0.1",
                port=0,
                api_key=None,
                auto_generate_key=True,
                keys_file=keys_file,
                workspace_root=self.repo_root,
            ) as http_srv:
                base_url = http_srv.base_url
                admin_key = http_srv.api_key
                self.assertTrue(admin_key.startswith("trl_admin_"))
                self.assertTrue(keys_file.exists())

                # 1. Admin issues a member key for another user/team via POST /admin/keys
                issue_req = Request(
                    f"{base_url}/admin/keys",
                    data=json.dumps({"label": "team-ibanking", "role": "member"}).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {admin_key}",
                    },
                    method="POST",
                )
                with http_srv.open_request(issue_req) as issue_resp:
                    self.assertEqual(issue_resp.status, 201)
                    issued = json.loads(issue_resp.read().decode("utf-8"))
                    member_key = issued["api_key"]
                    member_key_id = issued["key_id"]
                    self.assertTrue(member_key.startswith("trl_team_ibanking_"))
                    self.assertEqual(issued["role"], "member")
                    self.assertIn("/install.sh", issued["install_command"])

                # 2. Member key can call POST /mcp and GET /bundle.json
                mcp_req = Request(
                    f"{base_url}/mcp",
                    data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {member_key}",
                    },
                    method="POST",
                )
                with http_srv.open_request(mcp_req) as mcp_resp:
                    self.assertEqual(mcp_resp.status, 200)

                # 3. Member key is forbidden (403) from calling /admin/keys
                forbid_req = Request(
                    f"{base_url}/admin/keys",
                    headers={"Authorization": f"Bearer {member_key}"},
                    method="GET",
                )
                with self.assertRaises(HTTPError) as ctx_forbid:
                    http_srv.open_request(forbid_req)
                self.assertEqual(ctx_forbid.exception.code, 403)
                ctx_forbid.exception.close()

                # 4. Admin lists keys (GET /admin/keys) and revokes member key (DELETE /admin/keys/<id>)
                list_req = Request(
                    f"{base_url}/admin/keys",
                    headers={"Authorization": f"Bearer {admin_key}"},
                    method="GET",
                )
                with http_srv.open_request(list_req) as list_resp:
                    self.assertEqual(list_resp.status, 200)
                    listed = json.loads(list_resp.read().decode("utf-8"))
                    self.assertGreaterEqual(len(listed["keys"]), 2)

                revoke_req = Request(
                    f"{base_url}/admin/keys/{member_key_id}",
                    headers={"Authorization": f"Bearer {admin_key}"},
                    method="DELETE",
                )
                with http_srv.open_request(revoke_req) as revoke_resp:
                    self.assertEqual(revoke_resp.status, 200)

                # 5. Revoked member key now receives 401 Unauthorized on POST /mcp
                with self.assertRaises(HTTPError) as ctx_revoked:
                    http_srv.open_request(mcp_req)
                self.assertEqual(ctx_revoked.exception.code, 401)
                ctx_revoked.exception.close()

    def test_req_mcp_08_cli_key_management(self) -> None:
        """[REQ-MCP-08-02, REQ-MCP-08-04] Verify CLI --generate-key, --list-keys, and --revoke-key."""
        from trellis_mcp.__main__ import main

        with tempfile.TemporaryDirectory() as tmp:
            keys_file = Path(tmp) / ".trellis_keys.json"
            rc_gen = main(["--generate-key", "alice-dev", "--role", "member", "--keys-file", str(keys_file)])
            self.assertEqual(rc_gen, 0)
            self.assertTrue(keys_file.exists())

            rc_list = main(["--list-keys", "--keys-file", str(keys_file)])
            self.assertEqual(rc_list, 0)

            rc_rev = main(["--revoke-key", "alice-dev", "--keys-file", str(keys_file)])
            self.assertEqual(rc_rev, 0)

    def test_req_mcp_09_build_and_run_standalone_pyz_bundle(self) -> None:
        """[REQ-MCP-09] Verify --build-pyz creates a standalone single-file .pyz that serves standards and skills without repo folders."""
        import subprocess
        import sys
        from trellis_mcp.__main__ import main

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            pyz_path = tmp_dir / "trellis-mcp.pyz"
            rc = main(["--build-pyz", str(pyz_path)])
            self.assertEqual(rc, 0)
            self.assertTrue(pyz_path.exists())

            # Run the standalone .pyz from tmp_dir (where no docs/ or .agents/ directories exist on disk)
            probe_code = (
                "import json, sys; "
                f"sys.path.insert(0, {str(pyz_path)!r}); "
                "from pathlib import Path; "
                "from trellis_mcp.tools import tool_trellis_get_standard; "
                "from trellis_mcp.installer import build_remote_bundle; "
                f"empty_dir = Path({str(tmp_dir)!r}); "
                "std = tool_trellis_get_standard({'name': 'testing-standard'}, workspace_root=empty_dir); "
                "bundle = build_remote_bundle(empty_dir); "
                "print(json.dumps({'isError': std.get('isError'), 'has_text': 'Testing' in std['content'][0]['text'], 'skill_count': len(bundle.get('skills', {}))}))"
            )
            proc = subprocess.run(
                [sys.executable, "-c", probe_code],
                cwd=str(tmp_dir),
                capture_output=True,
                text=True,
                check=True,
            )
            out = json.loads(proc.stdout.strip())
            self.assertFalse(out["isError"])
            self.assertTrue(out["has_text"])
            self.assertGreaterEqual(out["skill_count"], 7)

            # Verify admin-only HTTP hot-deploy endpoint (POST /admin/deploy)
            target_workspace = tmp_dir / "vm_runtime"
            target_workspace.mkdir(parents=True, exist_ok=True)
            with TrellisHTTPServer(
                host="127.0.0.1",
                port=0,
                auto_generate_key=True,
                keys_file=target_workspace / ".trellis_keys.json",
                workspace_root=target_workspace,
            ) as http_srv:
                base_url = http_srv.base_url
                admin_key = http_srv.api_key
                deploy_bytes = pyz_path.read_bytes()
                deploy_sig = hmac.new(
                    admin_key.encode("utf-8"), deploy_bytes, hashlib.sha256
                ).hexdigest()
                deploy_req = Request(
                    f"{base_url}/admin/deploy",
                    data=deploy_bytes,
                    headers={
                        "Content-Type": "application/octet-stream",
                        "Authorization": f"Bearer {admin_key}",
                        "X-Trellis-Signature": deploy_sig,
                    },
                    method="POST",
                )
                with http_srv.open_request(deploy_req) as deploy_resp:
                    self.assertEqual(deploy_resp.status, 200)
                    deploy_data = json.loads(deploy_resp.read().decode("utf-8"))
                    self.assertEqual(deploy_data["status"], "deployed")
                    self.assertTrue((target_workspace / "trellis-mcp.pyz").exists())


    def test_req_mcp_10_keys_hashed_at_rest_expiry_and_rotation(self) -> None:
        """[REQ-MCP-08-05] Verify keys are hashed at rest, honor expiry, and rotate atomically."""
        from trellis_mcp.__main__ import main
        from trellis_mcp.http_server import TrellisKeyStore

        with tempfile.TemporaryDirectory() as tmp:
            keys_file = Path(tmp) / ".trellis_keys.json"
            store = TrellisKeyStore(keys_file)

            created = store.generate_key(label="svc", role="member", expires_days=30)
            raw_key = created["api_key"]
            self.assertEqual(store.verify_token(raw_key), "member")
            file_text = keys_file.read_text(encoding="utf-8")
            self.assertNotIn(raw_key, file_text)
            self.assertIn("token_hash", file_text)

            expired = store.generate_key(label="old", role="member", expires_days=-1)
            self.assertIsNone(store.verify_token(expired["api_key"]))

            rc_rotate = main(["--rotate-key", "svc", "--keys-file", str(keys_file)])
            self.assertEqual(rc_rotate, 0)
            self.assertIsNone(store.verify_token(raw_key))

    def test_req_mcp_10_http_hardening_body_and_rate_limits(self) -> None:
        """[REQ-MCP-10] Verify max-body enforcement (413) and per-client rate limiting (429)."""
        test_key = "team-secret-hardening"
        with TrellisHTTPServer(
            host="127.0.0.1",
            port=0,
            api_key=test_key,
            workspace_root=self.repo_root,
            max_body_bytes=64,
            rate_limit=100,
        ) as srv:
            big_req = Request(
                f"{srv.base_url}/mcp",
                data=b"x" * 256,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {test_key}",
                },
                method="POST",
            )
            with self.assertRaises(HTTPError) as ctx_big:
                srv.open_request(big_req)
            self.assertEqual(ctx_big.exception.code, 413)
            ctx_big.exception.close()

        with TrellisHTTPServer(
            host="127.0.0.1",
            port=0,
            api_key=test_key,
            workspace_root=self.repo_root,
            rate_limit=2,
            rate_window_sec=60,
        ) as srv:
            payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode("utf-8")
            codes = []
            for _ in range(5):
                req = Request(
                    f"{srv.base_url}/mcp",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {test_key}",
                    },
                    method="POST",
                )
                try:
                    with srv.open_request(req) as resp:
                        codes.append(resp.status)
                except HTTPError as exc:
                    codes.append(exc.code)
                    exc.close()
            self.assertIn(429, codes)
            self.assertEqual(codes.count(200), 2)

    def test_req_mcp_10_deploy_rejects_missing_or_invalid_signature(self) -> None:
        """[REQ-MCP-10] Verify /admin/deploy refuses unsigned or incorrectly signed bundles."""
        from trellis_mcp.__main__ import main

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            pyz_path = tmp_dir / "trellis-mcp.pyz"
            self.assertEqual(main(["--build-pyz", str(pyz_path)]), 0)
            deploy_bytes = pyz_path.read_bytes()

            target_workspace = tmp_dir / "vm_runtime"
            target_workspace.mkdir(parents=True, exist_ok=True)
            with TrellisHTTPServer(
                host="127.0.0.1",
                port=0,
                auto_generate_key=True,
                keys_file=target_workspace / ".trellis_keys.json",
                workspace_root=target_workspace,
            ) as srv:
                admin_key = srv.api_key

                def deploy(headers: dict[str, str]) -> int:
                    req = Request(
                        f"{srv.base_url}/admin/deploy",
                        data=deploy_bytes,
                        headers={
                            "Content-Type": "application/octet-stream",
                            "Authorization": f"Bearer {admin_key}",
                            **headers,
                        },
                        method="POST",
                    )
                    try:
                        with srv.open_request(req) as resp:
                            return resp.status
                    except HTTPError as exc:
                        code = exc.code
                        exc.close()
                        return code

                self.assertEqual(deploy({}), 400)
                self.assertEqual(deploy({"X-Trellis-Signature": "deadbeef"}), 403)
                good_sig = hmac.new(
                    admin_key.encode("utf-8"), deploy_bytes, hashlib.sha256
                ).hexdigest()
                self.assertEqual(deploy({"X-Trellis-Signature": good_sig}), 200)


if __name__ == "__main__":
    unittest.main()
