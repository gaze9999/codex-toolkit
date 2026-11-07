"""Delivery context, compaction instructions, instruction/config logs and doc lint on synthetic repositories."""
import json
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

FAKE_TEXTLINT = """import json, sys
path = sys.argv[-1]
text = open(path, encoding="utf-8").read()
messages = [{"line": 1, "column": text.index("。") + 1, "message": "period"}] if "。" in text else []
print(json.dumps([{"filePath": path, "messages": messages}]))
sys.exit(1 if messages else 0)
"""


class SessionEventTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="session 空白 ")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.repo = self.base / "project"
        (self.repo / "docs").mkdir(parents=True)
        self.git = shutil.which("git")
        subprocess.run([self.git, "init", "-q"], cwd=self.repo, check=True)
        (self.repo / "docs/release-policy.md").write_text("policy", encoding="utf-8")
        (self.repo / "AGENTS.md").write_text("agents", encoding="utf-8")
        self.state = self.base / "state"
        self.policy = {"schema_version": 1, "entries": ["AGENTS.md", "AI.md"], "start_note": "n", "stop_note": "s",
                       "git": self.git, "operations": "ops.md", "delivery_note": "Follow the version policy.",
                       "delivery_entries": ["docs/release-policy.md", "VERSION"], "compact_note": "Preserve decisions.",
                       "instruction_log": True, "config_change_note": True, "doc_lint": True}

    def event(self, name, client="claude", **values):
        payload = dict({"hook_event_name": name, "session_id": "s1", "cwd": str(self.repo)}, **values)
        return hooks.handle(payload, self.policy, client, self.state)

    def test_delivery_keywords_add_policy_context(self):
        for prompt in ("cpt", "  CP ", "cpr 這次"):
            with self.subTest(prompt=prompt):
                text = self.event("UserPromptSubmit", "codex", prompt=prompt)["hookSpecificOutput"]["additionalContext"]
                self.assertIn("Follow the version policy.", text)
                self.assertIn("docs/release-policy.md", text)
                self.assertNotIn("VERSION", text)
        for prompt in ("copy this", "請 cpt", "cpt " + "x" * 200, None):
            with self.subTest(prompt=prompt):
                self.assertEqual({}, self.event("UserPromptSubmit", prompt=prompt))

    def test_compaction_instructions_print_plain_text(self):
        self.assertEqual({"plainText": "Preserve decisions.\nCurrent entrypoints: AGENTS.md"}, self.event("PreCompact", trigger="auto"))
        policy = self.base / "policy.json"
        policy.write_text(json.dumps(self.policy), encoding="utf-8")
        payload = {"hook_event_name": "PreCompact", "session_id": "s1", "cwd": str(self.repo), "trigger": "manual"}
        result = subprocess.run([sys.executable, str(Path(hooks.__file__)), "--client", "claude", "--policy", str(policy),
                                 "--state-dir", str(self.state)], input=json.dumps(payload).encode(), capture_output=True, check=True)
        self.assertEqual("Preserve decisions.\nCurrent entrypoints: AGENTS.md\n", result.stdout.decode("utf-8"))

    def test_codex_receives_the_compact_note_after_compaction(self):
        startup = self.event("SessionStart", "codex", source="startup")["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("Preserve decisions.", startup)
        compact = self.event("SessionStart", "codex", source="compact")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("After compaction, restore from the summary and sources: Preserve decisions.", compact)
        self.assertTrue(compact.rstrip().endswith("ops.md"))

    def test_instruction_loads_are_logged_once_with_digests(self):
        name = str(self.repo / "AGENTS.md")
        for _ in range(2):
            self.assertEqual({}, self.event("InstructionsLoaded", file_path=name, memory_type="Project", load_reason="session_start"))
        log = json.loads(next(self.state.glob("instructions-*.json")).read_text(encoding="utf-8"))
        self.assertEqual(1, len(log))
        self.assertEqual(hooks.digest(b"agents"), log[0]["sha256"])
        self.assertNotIn("agents", json.dumps(log).replace("AGENTS", ""))

    def test_config_changes_surface_once_at_stop(self):
        for _ in range(2):
            self.assertEqual({}, self.event("ConfigChange", source="user_settings", file_path="/home/x/.claude/settings.json"))
        message = self.event("Stop", stop_hook_active=False)["systemMessage"]
        self.assertIn("user_settings (settings.json)", message)
        self.assertNotIn("systemMessage", self.event("Stop", stop_hook_active=False))

    def test_doc_lint_reports_chinese_markdown_once(self):
        runner = self.base / "fake_textlint.py"
        runner.write_text(FAKE_TEXTLINT, encoding="utf-8")
        doc = self.repo / "docs/guide.md"
        doc.write_text("完成同步。\n", encoding="utf-8")
        english = self.repo / "docs/en.md"
        english.write_text("Done.\n", encoding="utf-8")
        prefix = self.base / "npm"
        for config in hooks.LINT_CONFIGS.values():
            (prefix / config).parent.mkdir(parents=True, exist_ok=True)
            (prefix / config).write_text("{}", encoding="utf-8")
        japanese = self.repo / "docs/ja.md"
        japanese.write_text("同期が完了しました。\n", encoding="utf-8")
        with patch.object(hooks, "textlint_tools", return_value=(sys.executable, runner, prefix)), \
                patch.object(hooks, "spelling", return_value=["1:1"]):
            result = self.event("PostToolUse", tool_name="Write", tool_input={"file_path": str(doc)})
            self.assertIn("guide.md (zh-TW): 1 issue(s) at 1:5", result["hookSpecificOutput"]["additionalContext"])
            self.assertEqual({}, self.event("PostToolUse", tool_name="Write", tool_input={"file_path": str(doc)}))
            note = self.event("PostToolUse", tool_name="Edit", tool_input={"file_path": str(english)})["hookSpecificOutput"]["additionalContext"]
            self.assertNotIn("en.md (en)", note)
            self.assertIn("en.md (spelling): 1 unknown word(s) at 1:1", note)
            note = self.event("PostToolUse", tool_name="Edit", tool_input={"file_path": str(japanese)})["hookSpecificOutput"]["additionalContext"]
            self.assertIn("ja.md (ja): 1 issue(s)", note)
        self.assertEqual(["ja", "zh-TW", "en", None], [hooks.doc_language(t) for t in ("テスト", "測試", "Test", "12")])
        with patch.object(hooks, "textlint_tools", return_value=None):
            doc.write_text("改過。\n", encoding="utf-8")
            note = self.event("PostToolUse", "codex", tool_name="Write", tool_input={"file_path": str(doc)})
            self.assertIn("Doc lint skipped", note["hookSpecificOutput"]["additionalContext"])
            self.assertEqual({}, self.event("PostToolUse", "codex", tool_name="Write", tool_input={"file_path": str(doc)}))

    def fake_textlint(self):
        runner = self.base / "fake_textlint.py"
        runner.write_text(FAKE_TEXTLINT, encoding="utf-8")
        prefix = self.base / "npm"
        for config in hooks.LINT_CONFIGS.values():
            (prefix / config).parent.mkdir(parents=True, exist_ok=True)
            (prefix / config).write_text("{}", encoding="utf-8")
        return patch.object(hooks, "textlint_tools", return_value=(sys.executable, runner, prefix))

    def test_shell_edits_in_a_nested_repository_are_linted_after_the_turn_baseline(self):
        nested = self.base / "nested"
        (nested / "docs").mkdir(parents=True)
        subprocess.run([self.git, "init", "-q"], cwd=nested, check=True)
        older = nested / "docs/older.md"
        older.write_text("早就改過。\n", encoding="utf-8")
        with self.fake_textlint():
            self.event("UserPromptSubmit", prompt="寫文件", cwd=str(self.base))
            # A repository first entered by a shell command has no baseline, so its existing change is linted once.
            note = self.event("PostToolUse", tool_name="Bash", cwd=str(self.base), tool_input={"command": f'cd "{nested}" && git status'})
            self.assertIn("older.md (zh-TW)", note["hookSpecificOutput"]["additionalContext"])
            self.event("UserPromptSubmit", prompt="再寫", cwd=str(self.base))
            doc = nested / "docs/new.md"
            doc.write_text("新增內容。\n", encoding="utf-8")
            note = self.event("PostToolUse", tool_name="PowerShell", cwd=str(self.base),
                              tool_input={"command": f"Set-Location '{nested}'; python write.py"})["hookSpecificOutput"]["additionalContext"]
            self.assertIn("new.md (zh-TW): 1 issue(s)", note)
            self.assertNotIn("older.md", note)
            named = self.repo / "docs/named.md"
            named.write_text("點名。\n", encoding="utf-8")
            note = self.event("PostToolUse", tool_name="Bash", tool_input={"command": "python -c 'x' > docs/named.md"})
            self.assertIn("named.md (zh-TW)", note["hookSpecificOutput"]["additionalContext"])
        self.assertEqual({}, self.event("PostToolUse", tool_name="Read", tool_input={"file_path": str(named)}))

    def test_stop_asks_once_to_fix_this_turns_documents(self):
        self.policy["doc_lint_stop"] = True
        self.policy["silent"] = True
        doc = self.repo / "docs/guide.md"
        with self.fake_textlint():
            self.event("UserPromptSubmit", prompt="寫文件")
            doc.write_text("完成同步。\n", encoding="utf-8")
            result = self.event("Stop", stop_hook_active=False)
            self.assertEqual("block", result["decision"])
            self.assertIn("guide.md (1)", result["reason"])
            self.assertNotIn("decision", self.event("Stop", stop_hook_active=False))
            doc.write_text("完成同步, 另有一處。\n", encoding="utf-8")
            self.assertNotIn("decision", self.event("Stop", stop_hook_active=True))
            doc.write_text("完成同步\n", encoding="utf-8")
            self.assertNotIn("decision", self.event("Stop", stop_hook_active=False))
            self.event("UserPromptSubmit", prompt="下一輪")
            self.assertNotIn("decision", self.event("Stop", stop_hook_active=False))
        self.policy["doc_lint_stop"] = False
        doc.write_text("又改了。\n", encoding="utf-8")
        with self.fake_textlint():
            self.assertNotIn("decision", self.event("Stop", stop_hook_active=False))

    def test_shell_targets_read_directories_and_markdown_names(self):
        directories, files = hooks.shell_targets({"tool_name": "Bash", "tool_input": {
            "command": "cd sub && git -C other diff; cat \"a b.md\" docs/x.md https://e.test/y.mdx"}}, self.base)
        self.assertEqual([self.base, self.base / "sub", self.base / "sub/other"], directories)
        self.assertEqual([self.base / "sub/docs/x.md"], files[-1:])
        self.assertEqual(([], []), hooks.shell_targets({"tool_name": "Edit", "tool_input": {"command": "cd x"}}, self.base))
        if hooks.os.name == "nt":
            self.assertEqual(Path("D:/work"), hooks.native_path("/d/work", self.base))


class SessionInstallTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.operations = self.base / "ops.md"
        self.operations.write_text("ops", encoding="utf-8")
        self.profile = {"schema_version": 1, "entries": ["AGENTS.md"], "start_note": "n", "stop_note": "s", "delivery_note": "d",
                        "delivery_entries": ["VERSION"], "compact_note": "c", "doc_lint": True, "instruction_log": True,
                        "config_change_note": True}

    def groups(self, client):
        installer.validate_profile(self.profile)
        files, _ = installer.plan(client, self.base / client, self.profile, self.operations, Path(sys.executable), Path("git"), sys.platform, None)
        return next(json.loads(data) for path, data in files.items() if path.name == "manifest.json")["groups"]

    def test_doc_lint_rules_are_bundled_and_passed_to_textlint(self):
        folder = self.base / "profile"
        (folder / "proofreading").mkdir(parents=True)
        (folder / "proofreading/personal.cjs").write_text("module.exports = () => ({});\n", encoding="utf-8")
        profile = dict(self.profile, doc_lint_rules={"zh-TW": ["proofreading/personal.cjs"]})
        installer.validate_profile(profile)
        rules = installer.read_doc_rules(profile, folder)
        files, _ = installer.plan("claude", self.base / "claude", profile, self.operations, Path(sys.executable), Path("git"), sys.platform, None, None, rules)
        bundled = [path for path in files if path.name == "zh-TW-personal.cjs"]
        self.assertEqual(1, len(bundled))
        policy = json.loads(next(data for path, data in files.items() if path.name == "policy.json"))
        self.assertEqual({"zh-TW": ["doc-lint/zh-TW-personal.cjs"]}, policy["doc_lint_rules"])
        for bad in ({"fr": ["a.cjs"]}, {"zh-TW": ["../a.cjs"]}, {"zh-TW": ["a.txt"]}):
            with self.assertRaises(ValueError):
                installer.validate_profile(dict(self.profile, doc_lint_rules=bad))

    def test_claude_only_events_stay_out_of_codex(self):
        self.assertEqual(["SessionStart", "UserPromptSubmit", "PostToolUse", "PreCompact", "InstructionsLoaded", "ConfigChange", "Stop"],
                         list(self.groups("claude")))
        codex = self.groups("codex")
        self.assertEqual(["SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"], list(codex))
        self.assertEqual(600, codex["UserPromptSubmit"]["hooks"][0]["additionalContextLimit"])

    def test_invalid_session_options_are_rejected(self):
        for change in ({"delivery_note": ""}, {"compact_note": "x" * 1001}, {"doc_lint": "yes"},
                       {"delivery_entries": ["../x"]}, {"delivery_note": None}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                installer.validate_profile(dict(self.profile, **change))
        without_note = {key: value for key, value in self.profile.items() if key != "delivery_note"}
        with self.assertRaises(ValueError):
            installer.validate_profile(without_note)
        for change in ({"doc_lint_stop": "yes"}, {"doc_lint": False, "doc_lint_stop": True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                installer.validate_profile(dict(self.profile, **change))

    def test_doc_lint_registers_shell_tools_and_the_turn_baseline(self):
        self.profile = {key: value for key, value in self.profile.items() if key not in ("delivery_note", "delivery_entries")}
        self.profile["doc_lint_stop"] = True
        for client in ("claude", "codex"):
            groups = self.groups(client)
            self.assertIn("UserPromptSubmit", groups)
            self.assertEqual(installer.SHELL_MATCHER, groups["PostToolUse"]["matcher"])
        self.profile["doc_lint"] = False
        self.profile.pop("doc_lint_stop")
        groups = self.groups("claude")
        self.assertNotIn("UserPromptSubmit", groups)
        self.assertEqual(installer.EVENTS["PostToolUse"], groups["PostToolUse"]["matcher"])


if __name__ == "__main__":
    unittest.main()
