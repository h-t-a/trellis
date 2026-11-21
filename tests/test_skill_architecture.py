"""Requirement-linked tests for Skill Architecture, Index Manifest, and Linter ([REQ-TRL-31..33])."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestSkillArchitecture(unittest.TestCase):
    """Verify modular skill packs, index manifest, linter, and router ([REQ-TRL-31..33])."""

    def test_req_trl_31_skills_index_manifest_and_schema(self) -> None:
        """[REQ-TRL-31] skills/skills.index.json exists, adheres to schema, and covers all core skills."""
        index_file = REPO_ROOT / "skills" / "skills.index.json"
        self.assertTrue(index_file.is_file(), f"Missing skills index manifest at {index_file}")

        data = json.loads(index_file.read_text(encoding="utf-8"))
        self.assertIn("skills", data)
        skills = data["skills"]
        self.assertIsInstance(skills, list)
        self.assertGreaterEqual(len(skills), 18)

        known_packs = {"core", "data", "security", "network", "reverse"}
        seen_ids: set[str] = set()

        for s in skills:
            sid = s.get("id")
            self.assertIsInstance(sid, str)
            self.assertTrue(sid.startswith("pb-"), f"Skill ID must start with 'pb-': {sid}")
            self.assertNotIn(sid, seen_ids, f"Duplicate skill ID: {sid}")
            seen_ids.add(sid)

            pack = s.get("pack")
            self.assertIn(pack, known_packs, f"Invalid pack '{pack}' in skill {sid}")

            triggers = s.get("triggers")
            self.assertIsInstance(triggers, list)
            self.assertGreater(len(triggers), 0, f"Skill {sid} must have at least one trigger")

            not_for = s.get("not_for")
            self.assertIsInstance(not_for, list, f"Skill {sid} must have a 'not_for' list")

            tier = s.get("tier")
            self.assertIn(tier, (1, 2, 3), f"Skill {sid} tier must be 1, 2, or 3")

            quota = s.get("quota_class")
            self.assertIn(quota, ("S", "M", "L"), f"Skill {sid} quota_class must be S, M, or L")

            standards = s.get("standards")
            self.assertIsInstance(standards, list)
            self.assertGreater(len(standards), 0, f"Skill {sid} must reference at least one standard")

            budget = s.get("budget")
            self.assertIsInstance(budget, dict)
            self.assertGreater(budget.get("max_files", 0), 0)
            self.assertGreater(budget.get("max_tool_calls", 0), 0)

            # Check that canonical source file exists for core skills
            canonical = REPO_ROOT / "skills" / pack / sid / "SKILL.md"
            self.assertTrue(
                canonical.is_file(),
                f"Missing canonical skill file for {sid}: expected {canonical}",
            )

    def test_req_trl_32_skill_linter_and_doctor_enforcement(self) -> None:
        """[REQ-TRL-32] Doctor linter validates SKILL.md <= 40 lines, frontmatter metadata, and standards links."""
        from trellis_mcp.tools import tool_trellis_doctor

        def _get_text(res: dict) -> str:
            content = res.get("content")
            if isinstance(content, list) and content and isinstance(content[0], dict):
                return content[0].get("text", "")
            return str(res)

        # 1. Real repository doctor check must pass without skill linting errors
        res = tool_trellis_doctor({}, workspace_root=REPO_ROOT)
        self.assertIn("**HEALTHY**", _get_text(res))

        # 2. Test in an isolated temporary workspace that invalid skills trigger specific findings
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "trellis"
            skills_dir = ws / "skills" / "core" / "pb-test-fake"
            skills_dir.mkdir(parents=True)
            standards_dir = ws / "docs" / "standards"
            standards_dir.mkdir(parents=True)
            (standards_dir / "valid-standard.md").write_text("# Valid\n", encoding="utf-8")

            # Oversized skill (>40 lines)
            oversized_content = (
                "---\n"
                "name: pb-test-fake\n"
                "description: Use when testing oversized skills. Not for production use.\n"
                "metadata: {pack: core, tier: 1, quota_class: S, standards: [valid-standard]}\n"
                "---\n"
                + "\n".join(f"Line {i}" for i in range(45))
            )
            (skills_dir / "SKILL.md").write_text(oversized_content, encoding="utf-8")

            bad_res = tool_trellis_doctor({}, workspace_root=ws)
            content = _get_text(bad_res)
            self.assertIn("exceeds <=40 line budget", content)

            # Missing "Use when" or "Not for" in description
            bad_desc = (
                "---\n"
                "name: pb-test-fake\n"
                "description: Just a bad description without required phrases.\n"
                "metadata: {pack: core, tier: 1, quota_class: S, standards: [valid-standard]}\n"
                "---\n"
                "# Content\n"
            )
            (skills_dir / "SKILL.md").write_text(bad_desc, encoding="utf-8")
            bad_res2 = tool_trellis_doctor({}, workspace_root=ws)
            c2 = _get_text(bad_res2)
            self.assertTrue("Use when" in c2 or "Not for" in c2)

            # Broken standards reference in metadata
            broken_std = (
                "---\n"
                "name: pb-test-fake\n"
                "description: Use when testing broken standards. Not for production use.\n"
                "metadata: {pack: core, tier: 1, quota_class: S, standards: [non-existent-std]}\n"
                "---\n"
                "# Content\n"
            )
            (skills_dir / "SKILL.md").write_text(broken_std, encoding="utf-8")
            bad_res3 = tool_trellis_doctor({}, workspace_root=ws)
            self.assertIn("non-existent-std", _get_text(bad_res3))

    def test_req_trl_33_skill_route_tool(self) -> None:
        """[REQ-TRL-33] trellis_skill_route returns accurate skill, pack, tier, and gate recommendations."""
        from trellis_mcp.server import TrellisMCPServer
        from trellis_mcp.tools import tool_trellis_skill_route

        # Test root cause task -> pb-rca
        rca_res = tool_trellis_skill_route(
            {"task": "debug exception and find root cause of failing test"},
            workspace_root=REPO_ROOT,
        )
        self.assertIn("skills", rca_res)
        skills = rca_res["skills"]
        self.assertGreater(len(skills), 0)
        top = skills[0]
        self.assertEqual(top["id"], "pb-rca")
        self.assertEqual(top["tier"], 2)
        self.assertIn("Tier 2", rca_res.get("gate", ""))

        # Test planning task -> pb-plan
        plan_res = tool_trellis_skill_route(
            {"task": "classify task risk and draft an implementation plan"},
            workspace_root=REPO_ROOT,
        )
        self.assertEqual(plan_res["skills"][0]["id"], "pb-plan")

        # Test review task -> pb-review
        rev_res = tool_trellis_skill_route(
            {"task": "review pull request and check DoD against standards"},
            workspace_root=REPO_ROOT,
        )
        self.assertEqual(rev_res["skills"][0]["id"], "pb-review")

        # Verify tool is registered in TrellisMCPServer
        srv = TrellisMCPServer(workspace_root=REPO_ROOT)
        tools_resp = srv.handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        tool_names = {t["name"] for t in tools_resp["result"]["tools"]}
        self.assertIn("trellis_skill_route", tool_names)
        self.assertIn("trellis_skill_route", srv._tool_dispatch)

    def test_req_trl_31_pack_sync_and_installation(self) -> None:
        """[REQ-TRL-31] sync_workspace copies canonical skills/<pack>/ to mirrors and supports pack filtering."""
        from trellis_mcp.installer import install_global, sync_workspace

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "trellis"
            skills_core = ws / "skills" / "core" / "pb-sample-core"
            skills_core.mkdir(parents=True)
            (skills_core / "SKILL.md").write_text(
                "---\n"
                "name: pb-sample-core\n"
                "description: Use when sampling core. Not for data.\n"
                "metadata: {pack: core, tier: 1, quota_class: S, standards: [testing-standard]}\n"
                "---\n# Sample\n",
                encoding="utf-8",
            )
            skills_data = ws / "skills" / "data" / "pb-sample-data"
            skills_data.mkdir(parents=True)
            (skills_data / "SKILL.md").write_text(
                "---\n"
                "name: pb-sample-data\n"
                "description: Use when sampling data. Not for core.\n"
                "metadata: {pack: data, tier: 1, quota_class: S, standards: [database-standard]}\n"
                "---\n# Sample Data\n",
                encoding="utf-8",
            )

            # Sync workspace
            sync_res = sync_workspace(ws)
            self.assertIn("Synced", sync_res)
            self.assertTrue((ws / ".agents" / "skills" / "pb-sample-core" / "SKILL.md").is_file())
            self.assertTrue((ws / ".claude" / "skills" / "pb-sample-core" / "SKILL.md").is_file())
            self.assertTrue((ws / ".claude" / "commands" / "pb-sample-core.md").is_file())
            self.assertTrue((ws / ".agents" / "skills" / "pb-sample-data" / "SKILL.md").is_file())

            # Install global with pack selection
            fake_home = Path(tmp) / "home"
            inst_res = install_global(ws, home_dir=fake_home, packs=["core"])
            self.assertIn("pb-sample-core", inst_res)
            # pb-sample-data should not be installed when packs=["core"]
            self.assertTrue(
                (fake_home / ".claude" / "skills" / "pb-sample-core" / "SKILL.md").is_file()
            )
            self.assertFalse(
                (fake_home / ".claude" / "skills" / "pb-sample-data" / "SKILL.md").exists()
            )
