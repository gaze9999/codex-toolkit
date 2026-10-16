from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from text.context_budget import estimate_context, format_budget, project_chain, skill_metadata
from text.token_count import count_text


@unittest.skipUnless(importlib.util.find_spec("tiktoken"), "Requires tiktoken")
class ContextBudgetTests(unittest.TestCase):
    def setup_tree(self, root):
        home, project = root / "home", root / "repo"
        home.mkdir()
        project.mkdir()
        (project / ".git").mkdir()
        (home / "AGENTS.md").write_text("global rules", encoding="utf-8")
        (project / "AGENTS.md").write_text("project rules", encoding="utf-8")
        return home, project

    def test_override_fallback_and_nested_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, project = self.setup_tree(Path(tmp))
            (project / "AGENTS.override.md").write_text("override", encoding="utf-8")
            nested = project / "src"
            nested.mkdir()
            (nested / "TEAM.md").write_text("team", encoding="utf-8")
            self.assertEqual([p.name for p in project_chain(nested, ["TEAM.md"])], ["AGENTS.override.md", "TEAM.md"])
            report = estimate_context(nested, home, builtin_tools=0)
            rows = {row["category"]: row for row in report["components"]}
            self.assertEqual(rows["Global Agent"]["low"], count_text("global rules")["tokens"])
            self.assertEqual(rows["Project Agent"]["low"], count_text("override")["tokens"])
            self.assertEqual(report["total"]["low"], sum(row["low"] for row in report["components"]))

    def test_skill_metadata_body_activation_disabled_and_latest_plugin(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, project = self.setup_tree(Path(tmp))
            (home / "config.toml").write_text('[plugins."off@market"]\nenabled=false\n', encoding="utf-8")
            for name, version in (("on", "1.0.0"), ("on", "2.0.0"), ("off", "1.0.0")):
                folder = home / "plugins/cache/market" / name / version / "skills/example"
                folder.mkdir(parents=True)
                (folder / "SKILL.md").write_text('---\nname: example\ndescription: Count examples\n---\n' + 'BODY ' * 100, encoding="utf-8")
            report = estimate_context(project, home, builtin_tools=0)
            row = next(row for row in report["components"] if row["category"] == "Skills 探索清單")
            self.assertEqual(report["skill_count"], 1)
            self.assertIn("2.0.0", row["sources"][0])
            path = Path(row["sources"][0])
            self.assertNotIn("BODY", skill_metadata(path))
            active = estimate_context(project, home, builtin_tools=0, active_skills=[path])
            self.assertGreater(active["total"]["low"], report["total"]["low"])

    def test_combined_instruction_limit_and_file_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, project = self.setup_tree(Path(tmp))
            (home / "config.toml").write_text('project_doc_max_bytes=6\n', encoding="utf-8")
            report = estimate_context(project, home, builtin_tools=0, instructions=[project / "AGENTS.md"])
            rows = {row["category"]: row for row in report["components"]}
            self.assertEqual(rows["Global Agent"]["low"], count_text("global")["tokens"])
            self.assertEqual(rows["Project Agent"]["low"], 0)
            self.assertNotIn("其他指示與參考", rows)

    def test_tool_definitions_replace_per_tool_estimates(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, project = self.setup_tree(Path(tmp))
            (home / "config.toml").write_text('[mcp_servers.active]\ncommand="local"\n[mcp_servers.off]\nenabled=false\n', encoding="utf-8")
            tools = project / "tools.json"
            tools.write_text('[{"name":"local"}]', encoding="utf-8")
            report = estimate_context(project, home, tool_schemas=[tools], builtin_tools=100, mcp_tools=100)
            rows = {row["category"]: row for row in report["components"]}
            self.assertEqual(report["mcp_servers"], ["active"])
            self.assertEqual(rows["選定工具定義"]["low"], count_text(tools.read_text(encoding="utf-8"))["tokens"])
            self.assertFalse(any("工具預估" in category for category in rows))
            self.assertEqual(report["total"]["high"] - report["total"]["low"], 300)
            self.assertIn("來源:", format_budget(report))

    def test_missing_explicit_source_and_bad_profile_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, project = self.setup_tree(Path(tmp))
            with self.assertRaises(FileNotFoundError):
                estimate_context(project, home, contents=[project / "missing.txt"])
            profile = project / "profile.json"
            profile.write_text(json.dumps({"system_tokens": -1}), encoding="utf-8")
            with self.assertRaises(ValueError):
                estimate_context(project, home, profile_path=profile)

    def test_project_config_overrides_home_server_enablement(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, project = self.setup_tree(Path(tmp))
            (home / "config.toml").write_text('[mcp_servers.example]\ncommand="local"\n', encoding="utf-8")
            (project / ".codex").mkdir()
            (project / ".codex/config.toml").write_text('[mcp_servers.example]\nenabled=false\n', encoding="utf-8")
            nested = project / "src"
            nested.mkdir()
            report = estimate_context(nested, home)
            self.assertEqual(report["mcp_servers"], [])


if __name__ == "__main__":
    unittest.main()
