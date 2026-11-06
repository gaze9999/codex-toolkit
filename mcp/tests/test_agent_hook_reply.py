"""Final-reply fullwidth review on synthetic replies; receipts must never contain reply text."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import agent_hooks as hooks
import install_agent_hooks as installer

REPLY = "完成同步。\n\n「SFAP 決定」改成排除、保留\n\n| 項目 | 狀態 |\n| --- | --- |\n| 安裝 | 已完成：讀回 |\n"


class ReplyReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="reply 空白 ")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.repo = self.base / "project"
        self.repo.mkdir()
        self.git = shutil.which("git")
        subprocess.run([self.git, "init", "-q"], cwd=self.repo, check=True)
        self.state = self.base / "state"
        self.policy = {"schema_version": 1, "entries": [], "start_note": "n", "stop_note": "s", "git": self.git,
                       "operations": "ops.md", "reply_punctuation": True}
        self.payload = {"cwd": str(self.repo), "session_id": "s1", "hook_event_name": "Stop", "stop_hook_active": False,
                        "last_assistant_message": REPLY}

    def stop(self, client="claude", **values):
        return hooks.handle(dict(self.payload, **values), self.policy, client, self.state)

    def receipts(self):
        return [path.read_text(encoding="utf-8") for path in self.state.glob("reply-*.json")]

    def test_candidates_block_once_with_locations_and_context(self):
        result = self.stop()
        self.assertEqual("block", result["decision"])
        reason = result["reason"]
        self.assertIn("4 candidate(s)", reason)
        self.assertIn("- 1:5 U+3002 near: 完成同步[[。]]", reason)
        self.assertIn("- 3:1 U+300C near: [[「]]SFAP 決定」改成排除", reason)
        self.assertIn("U+FF1A", reason)
        self.assertNotIn("U+3001", reason)  # The enumeration comma stays allowed.
        self.assertEqual({}, self.stop())
        self.assertEqual({}, self.stop(stop_hook_active=True, last_assistant_message="修正。"))
        self.assertEqual("block", self.stop("codex")["decision"])
        for receipt in self.receipts():
            self.assertNotIn("SFAP", receipt)
            self.assertNotIn("完成", receipt)
            self.assertEqual({"version", "checked", "count"}, set(json.loads(receipt)))

    def test_code_urls_and_clean_replies_stay_silent(self):
        reply = "執行 `npm test。` 完成\n\n```text\n原文。\n```\n\n見 https://example.test/a。b 與 README.md\n"
        self.assertEqual({}, self.stop(last_assistant_message=reply))
        for value in (None, "", "   "):
            self.assertEqual({}, self.stop(last_assistant_message=value))
        del self.policy["reply_punctuation"]
        self.assertEqual({}, self.stop(last_assistant_message="新回覆。"))

    def test_oversize_reply_reports_the_gap_without_blocking(self):
        result = self.stop(last_assistant_message="長" * (hooks.MAX_REPLY // 3 + 1))
        self.assertIn("未檢查全形標點", result["systemMessage"])
        self.assertNotIn("decision", result)

    def test_many_candidates_are_summarized(self):
        reply = "\n".join(f"第 {index} 行。" for index in range(1, 26))
        reason = self.stop(last_assistant_message=reply)["reason"]
        self.assertIn("25 candidate(s)", reason)
        self.assertIn("5 more candidates", reason)

    def test_subagent_stop_names_the_child_and_skips_repository_evidence(self):
        (self.repo / "new.txt").write_text("x", encoding="utf-8")
        result = hooks.handle(dict(self.payload, hook_event_name="SubagentStop", agent_id="a1", agent_type="geo-reviewer"),
                              self.policy, "claude", self.state)
        self.assertEqual("block", result["decision"])
        self.assertIn("from subagent geo-reviewer", result["reason"])
        self.assertNotIn("systemMessage", result)
        with self.assertRaises(ValueError):
            hooks.handle({"hook_event_name": "SubagentStop"}, self.policy, "claude", self.state)


class ReplyInstallTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.profile = {"schema_version": 1, "entries": ["AGENTS.md"], "start_note": "n", "stop_note": "s"}
        self.operations = self.base / "ops.md"
        self.operations.write_text("ops", encoding="utf-8")

    def plan(self, client, profile):
        home = self.base / client
        return installer.plan(client, home, profile, self.operations, Path(sys.executable), Path("git"), sys.platform, None)

    def parts(self, files):
        manifest = next(json.loads(data) for path, data in files.items() if path.name == "manifest.json")
        policy = next(json.loads(data) for path, data in files.items() if path.name == "policy.json")
        return manifest, policy

    def test_selection_adds_subagent_stop_without_external_tools(self):
        profile = dict(self.profile, reply_punctuation=True)
        installer.validate_profile(profile)
        for client in ("codex", "claude"):
            manifest, policy = self.parts(self.plan(client, profile)[0])
            self.assertEqual(["SessionStart", "PostToolUse", "Stop", "SubagentStop"], list(manifest["groups"]))
            self.assertIs(True, policy["reply_punctuation"])
            self.assertNotIn("reply_check", policy)

    def test_default_profile_keeps_existing_events(self):
        manifest, policy = self.parts(self.plan("claude", self.profile)[0])
        self.assertEqual(["SessionStart", "PostToolUse", "Stop"], list(manifest["groups"]))
        self.assertNotIn("reply_punctuation", policy)
        with self.assertRaises(ValueError):
            installer.validate_profile(dict(self.profile, reply_punctuation="yes"))


if __name__ == "__main__":
    unittest.main()
