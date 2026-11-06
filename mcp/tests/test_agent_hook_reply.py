"""Final-reply punctuation diagnostics on synthetic replies; receipts must never contain reply text."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import agent_hooks as hooks
import install_agent_hooks as installer

CONFIG = Path(__file__).resolve().parents[1] / "tools/proofreading/zh-tw/.textlintrc.cjs"
REPLY = "完成同步。\n\n「SFAP 決定」改成排除\n\n| 項目 | 狀態 |\n| --- | --- |\n| 安裝 | 已完成。 |\n"


REAL_RUN = subprocess.run


def fake_textlint(messages, code=1):
    def run(command, **options):
        if "--stdin" not in command:
            return REAL_RUN(command, **options)  # Git calls keep their real behavior.
        assert options["input"]
        return subprocess.CompletedProcess(command, code, json.dumps([{"messages": messages}]).encode(), b"")
    return run


def failing_textlint(error):
    def run(command, **options):
        if "--stdin" not in command:
            return REAL_RUN(command, **options)
        raise error
    return run


class ReplyCheckTests(unittest.TestCase):
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
                       "operations": "ops.md", "reply_check": {"node": "node", "textlint": "textlint.js", "config": str(CONFIG)}}
        self.payload = {"cwd": str(self.repo), "session_id": "s1", "hook_event_name": "Stop", "stop_hook_active": False,
                        "last_assistant_message": REPLY}

    def stop(self, client="claude", **values):
        return hooks.handle(dict(self.payload, **values), self.policy, client, self.state)

    def receipts(self):
        return [path.read_text(encoding="utf-8") for path in self.state.glob("reply-*.json")]

    def test_locations_and_kinds_are_reported_once_without_storing_text(self):
        messages = [{"line": 1, "column": 5, "message": "繁中敘述不加句號, 依語意"},
                    {"line": 3, "column": 1, "message": "繁中自撰文字使用半形引號 \"...\""},
                    {"line": 7, "column": 11, "message": "繁中敘述不加句號, 依語意"}]
        with patch.object(hooks.subprocess, "run", fake_textlint(messages)):
            result = self.stop()
            self.assertEqual("最終回覆標點: 共 3 處, 句號 1:5、7:11, 引號 3:1", result["systemMessage"])
            self.assertNotIn("decision", result)
            self.assertEqual({}, self.stop())
            self.assertEqual({}, self.stop(stop_hook_active=True))
            self.assertIn("最終回覆標點", self.stop("codex")["systemMessage"])
        for receipt in self.receipts():
            self.assertNotIn("SFAP", receipt)
            self.assertNotIn("完成", receipt)
            self.assertEqual({"version", "checked", "counts"}, set(json.loads(receipt)))

    def test_clean_missing_and_disabled_replies_stay_silent(self):
        with patch.object(hooks.subprocess, "run", fake_textlint([], 0)):
            self.assertEqual({}, self.stop())
        for value in (None, "", "   "):
            self.assertEqual({}, self.stop(last_assistant_message=value))
        del self.policy["reply_check"]
        self.assertEqual({}, self.stop(last_assistant_message="新回覆。"))

    def test_failures_and_oversize_replies_report_the_gap(self):
        for side_effect in (subprocess.TimeoutExpired("node", 8), OSError("missing")):
            with self.subTest(error=type(side_effect).__name__), patch.object(hooks.subprocess, "run", failing_textlint(side_effect)):
                result = self.stop(last_assistant_message=f"{type(side_effect).__name__} 回覆。")
                self.assertIn("無法執行", result["systemMessage"])
        with patch.object(hooks.subprocess, "run", fake_textlint([], 2)):
            self.assertIn("無法執行", self.stop(last_assistant_message="結束碼 2。")["systemMessage"])
        result = self.stop(last_assistant_message="長" * (hooks.MAX_REPLY // 3 + 1))
        self.assertIn("未檢查標點", result["systemMessage"])

    def test_many_findings_are_summarized(self):
        messages = [{"line": index, "column": 1, "message": "繁中使用半形標點"} for index in range(1, 12)]
        with patch.object(hooks.subprocess, "run", fake_textlint(messages)):
            message = self.stop()["systemMessage"]
        self.assertIn("共 11 處", message)
        self.assertIn("另有 3 處", message)

    def test_subagent_stop_labels_the_child_and_skips_repository_evidence(self):
        (self.repo / "new.txt").write_text("x", encoding="utf-8")
        messages = [{"line": 2, "column": 3, "message": "不要用分號分段"}]
        with patch.object(hooks.subprocess, "run", fake_textlint(messages)):
            result = hooks.handle(dict(self.payload, hook_event_name="SubagentStop", agent_id="a1", agent_type="geo-reviewer"),
                                  self.policy, "claude", self.state)
        self.assertEqual("子代理 geo-reviewer 最終回覆標點: 共 1 處, 分號 2:3", result["systemMessage"])
        self.assertNotIn("Hook evidence", result["systemMessage"])
        with self.assertRaises(ValueError):
            hooks.handle({"hook_event_name": "SubagentStop"}, self.policy, "claude", self.state)

    @unittest.skipUnless(os.environ.get("AGENT_HOOKS_TEXTLINT") and shutil.which("node"),
                         "Set AGENT_HOOKS_TEXTLINT to an installed textlint.js")
    def test_installed_textlint_reports_table_quote_and_inline_periods(self):
        self.policy["reply_check"] = {"node": shutil.which("node"), "textlint": os.environ["AGENT_HOOKS_TEXTLINT"], "config": str(CONFIG)}
        reply = REPLY + "\n執行 `npm test`。\n\n保留 `程式碼。`、v0.4.0、https://example.test/a.b 與 README.md\n\n> 原文「保留。」\n"
        message = self.stop(last_assistant_message=reply)["systemMessage"]
        self.assertEqual("最終回覆標點: 共 4 處, 句號 1:5、7:11、9:14, 引號 3:1", message)


class ReplyInstallTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.profile = {"schema_version": 1, "entries": ["AGENTS.md"], "start_note": "n", "stop_note": "s"}
        self.operations = self.base / "ops.md"
        self.operations.write_text("ops", encoding="utf-8")
        self.check = {"node": "node", "textlint": "textlint.js", "config": "c.cjs"}

    def plan(self, client, profile, reply_check=None):
        home = self.base / client
        return installer.plan(client, home, profile, self.operations, Path(sys.executable), Path("git"), sys.platform, None, reply_check)

    def test_selection_adds_subagent_stop_and_policy_paths(self):
        profile = dict(self.profile, reply_punctuation=True)
        installer.validate_profile(profile)
        for client in ("codex", "claude"):
            files, _ = self.plan(client, profile, self.check)
            manifest = next(json.loads(data) for path, data in files.items() if path.name == "manifest.json")
            policy = next(json.loads(data) for path, data in files.items() if path.name == "policy.json")
            self.assertEqual({"SessionStart", "PostToolUse", "Stop", "SubagentStop"}, set(manifest["groups"]))
            self.assertEqual(self.check, policy["reply_check"])
        with self.assertRaisesRegex(ValueError, "textlint"):
            self.plan("claude", profile)

    def test_default_profile_keeps_existing_events(self):
        files, _ = self.plan("claude", self.profile, self.check)
        manifest = next(json.loads(data) for path, data in files.items() if path.name == "manifest.json")
        policy = next(json.loads(data) for path, data in files.items() if path.name == "policy.json")
        self.assertEqual({"SessionStart", "PostToolUse", "Stop"}, set(manifest["groups"]))
        self.assertNotIn("reply_check", policy)
        with self.assertRaises(ValueError):
            installer.validate_profile(dict(self.profile, reply_punctuation="yes"))


if __name__ == "__main__":
    unittest.main()
