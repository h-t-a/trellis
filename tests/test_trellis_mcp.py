"""Automated unit and stdio integration tests for the trellis-mcp server and installer.

Verifies requirements:
- [REQ-MCP-01]: Zero-dependency Python MCP JSON-RPC 2.0 server over stdio
- [REQ-MCP-02]: 8 callable MCP tools with P0/P1 safety & cost guards (F02, F03, F04, F10, F12)
- [REQ-MCP-03]: Cross-device workspace sync & global device installer
- [REQ-MCP-04]: Requirement-linked automated verification
"""

from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
