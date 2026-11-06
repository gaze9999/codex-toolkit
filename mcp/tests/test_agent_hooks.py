import base64
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import agent_hooks as hooks
import install_agent_hooks as installer
import verify_agent_hooks as verifier


class AgentHooksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hooks 空白 '")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "project"
        self.repo.mkdir()
        self.git = shutil.which("git")
        self.run_git("init", "-q")
        self.run_git("config", "user.name", "Fixture")
        self.run_git("config", "user.email", "fixture@example.invalid")
        (self.repo / "AGENTS.md").write_text("# Fixture\n", encoding="utf-8")
        self.run_git("add", "AGENTS.md")
        self.run_git("commit", "-qm", "fixture")
        self.profile = {"schema_version": 1, "entries": ["AGENTS.md", "AI.md"], "start_note": "Read project guidance", "stop_note": "Report actual checks"}
        self.policy = dict(self.profile, git=self.git, operations="maintained-operations.md")
        self.payload = {"cwd": str(self.repo), "session_id": "session/../../id", "hook_event_name": "SessionStart", "source": "startup"}
        self.state = self.base / "state"

    def run_git(self, *args):
        return subprocess.run([self.git, *args], cwd=self.repo, check=True, capture_output=True)

    def event(self, event, client="codex", **values):
        return hooks.handle(dict(self.payload, hook_event_name=event, **values), self.policy, client, self.state)

    def test_command_evidence_does_not_promote_silence_or_warning(self):
        for output in ({}, {"systemMessage": "tracked whitespace check failed"}):
            row = verifier.command_evidence("claude", "Stop", output)
            self.assertEqual("passed", row["command"])
            self.assertEqual("not_verified", row["project_checks"])
            self.assertEqual("not_verified", row["native_event"])
            self.assertEqual(output, row["hook_output"])
        for output in ([], {"decision": "block"}, {"continue": False}):
            with self.assertRaises(ValueError):
                verifier.command_evidence("codex", "Stop", output)

    def test_route_compaction_and_client_isolation(self):
        for client in ("codex", "claude"):
            result = self.event("SessionStart", client)
            self.assertIn("AGENTS.md", result["hookSpecificOutput"]["additionalContext"])
            self.assertEqual({}, self.event("SessionStart", client))
            self.assertTrue(self.event("SessionStart", client, source="compact"))
        self.assertEqual(2, len(list(self.state.glob("*.json"))))

    def test_edit_check_reuse_and_stale_receipt(self):
        file = self.repo / "AGENTS.md"
        file.write_text("# Changed\n", encoding="utf-8")
        self.assertEqual({}, self.event("PostToolUse"))
        receipt = next(self.state.glob("*.json"))
        before = receipt.stat().st_mtime_ns
        self.assertEqual({}, self.event("PostToolUse"))
        self.assertEqual(before, receipt.stat().st_mtime_ns)
        self.assertEqual({}, self.event("Stop"))
        file.write_text("# Other\n", encoding="utf-8")
        self.assertIn("no current", self.event("Stop")["systemMessage"])
        self.assertEqual({}, self.event("Stop"))

    def test_whitespace_failure_and_recovery(self):
        file = self.repo / "AGENTS.md"
        file.write_bytes(b"# Changed  \n")
        self.assertIn("issue", self.event("PostToolUse")["hookSpecificOutput"]["additionalContext"])
        self.assertIn("failed", self.event("Stop")["systemMessage"])
        file.write_bytes(b"# Fixed\n")
        self.assertEqual({}, self.event("PostToolUse"))
        self.assertEqual({}, self.event("Stop"))

    def test_untracked_and_reentrant_stop(self):
        (self.repo / "new.txt").write_text("new", encoding="utf-8")
        self.assertIn("untracked", self.event("Stop")["systemMessage"])
        self.assertEqual({}, self.event("Stop", stop_hook_active=True))

    def test_silent_stop_records_receipts_without_user_notice(self):
        self.policy["silent"] = True
        file = self.repo / "AGENTS.md"
        file.write_bytes(b"# Changed  \n")
        self.assertIn("issue", self.event("PostToolUse")["hookSpecificOutput"]["additionalContext"])
        (self.repo / "new.txt").write_text("new", encoding="utf-8")
        self.assertEqual({}, self.event("Stop"))
        self.policy["silent"] = False
        self.assertEqual({}, self.event("Stop"))
        installer.validate_profile(dict(self.profile, silent=True))
        with self.assertRaises(ValueError):
            installer.validate_profile(dict(self.profile, silent="yes"))

    def test_subdirectory_and_worktree_identity(self):
        nested = self.repo / "nested"
        nested.mkdir()
        self.payload["cwd"] = str(nested)
        self.assertTrue(self.event("SessionStart"))
        worktree = self.base / "other"
        self.run_git("worktree", "add", "--detach", str(worktree))
        self.payload["cwd"] = str(worktree)
        self.assertTrue(self.event("SessionStart"))
        self.assertEqual(2, len(list(self.state.glob("*.json"))))

    def test_no_repository_and_invalid_event(self):
        self.payload["cwd"] = str(self.base)
        self.assertEqual({}, self.event("Stop"))
        self.assertIn("Branch: not a Git repository", self.event("SessionStart")["hookSpecificOutput"]["additionalContext"])
        self.policy["project_checks"] = [{"root": str(self.repo), "project": {}}]
        self.assertEqual({}, self.event("PostToolUse", tool_name="Bash", tool_input={"command": "dir"}))
        self.assertEqual({}, self.event("Stop"))
        with self.assertRaises(ValueError):
            self.event("PermissionRequest")

    def test_edited_file_selects_its_repository_from_parent_cwd(self):
        self.payload["cwd"] = str(self.base)
        file = self.repo / "AGENTS.md"
        file.write_bytes(b"# Changed  \n")
        result = self.event("PostToolUse", tool_name="Edit", tool_input={"file_path": str(file)})
        self.assertIn("issue in project", result["hookSpecificOutput"]["additionalContext"])
        self.assertIn("project: tracked whitespace check failed", self.event("Stop")["systemMessage"])
        self.assertEqual({}, self.event("Stop"))
        self.assertEqual({}, self.event("Stop", client="claude"))

    def test_native_discovery_matches_encoded_command_and_owner(self):
        config = self.base / "hooks.json"
        command = "powershell.exe -EncodedCommand Zml4dHVyZQ=="
        groups = {"Stop": {"hooks": [{"command": command}]}}
        own = {"sourcePath": str(config), "command": command, "eventName": "stop", "enabled": True, "trustStatus": "untrusted"}
        foreign = dict(own, sourcePath=str(self.base / "other.json"))
        result = verifier.selected_hooks({"data": [{"hooks": [own, foreign], "errors": []}]}, groups, config)
        self.assertEqual([{"eventName": "stop", "enabled": True, "trustStatus": "untrusted"}], result)

    def test_install_preserves_settings_and_is_idempotent(self):
        for client in ("codex", "claude"):
            home = self.base / client
            home.mkdir()
            config = home / ("hooks.json" if client == "codex" else "settings.json")
            foreign = {"hooks": [{"type": "command", "command": "fixture-not-run"}]}
            original = {"enabledPlugins": {"fixture": True}, "hooks": {"Stop": [foreign]}}
            config.write_text(json.dumps(original), encoding="utf-8")
            files, expected = installer.plan(client, home, self.profile, self.repo / "AGENTS.md", Path(sys.executable), Path(self.git), sys.platform)
            installer.apply_plan(files, expected, home)
            result = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(original["enabledPlugins"], result["enabledPlugins"])
            self.assertIn(foreign, result["hooks"]["Stop"])
            repeated, baseline = installer.plan(client, home, self.profile, self.repo / "AGENTS.md", Path(sys.executable), Path(self.git), sys.platform)
            self.assertEqual(repeated, baseline)
            self.assertEqual(1, len(list((home / "managed-agent-hooks/backups").glob("*/" + config.name))))

    def test_modified_owned_hook_conflicts(self):
        home = self.base / "codex"
        args = ("codex", home, self.profile, self.repo / "AGENTS.md", Path(sys.executable), Path(self.git), sys.platform)
        files, expected = installer.plan(*args)
        installer.apply_plan(files, expected, home)
        config = home / "hooks.json"
        value = json.loads(config.read_text(encoding="utf-8"))
        value["hooks"]["Stop"][0]["hooks"][0]["timeout"] = 99
        config.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed locally"):
            installer.plan(*args)

    def test_concurrent_config_change_is_preserved(self):
        home = self.base / "codex"
        home.mkdir()
        files, expected = installer.plan("codex", home, self.profile, self.repo / "AGENTS.md", Path(sys.executable), Path(self.git), sys.platform)
        config = home / "hooks.json"
        config.write_text('{"concurrent": true}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed after preview"):
            installer.apply_plan(files, expected, home)
        self.assertEqual({"concurrent": True}, json.loads(config.read_text()))

    def test_profile_rejects_escape_and_commands(self):
        for name in ("../outside", "/absolute", "C:/path", "x\\y"):
            with self.assertRaises(ValueError):
                installer.validate_profile(dict(self.profile, entries=[name]))
        with self.assertRaises(ValueError):
            installer.validate_profile(dict(self.profile, command="echo unauthorized"))

    def test_timeout_does_not_create_success_receipt(self):
        with patch.object(hooks, "git_run", side_effect=subprocess.TimeoutExpired("git", 2)):
            with self.assertRaises(subprocess.TimeoutExpired):
                self.event("PostToolUse")
        self.assertFalse(self.state.exists())

    def test_failed_install_rolls_back_owned_writes(self):
        home = self.base / "codex"
        files, expected = installer.plan("codex", home, self.profile, self.repo / "AGENTS.md", Path(sys.executable), Path(self.git), sys.platform)
        original_write = installer.atomic_write

        def fail_config(path, data):
            if path.name == "hooks.json":
                raise OSError("fixture write failure")
            original_write(path, data)

        with patch.object(installer, "atomic_write", side_effect=fail_config):
            with self.assertRaises(OSError):
                installer.apply_plan(files, expected, home)
        self.assertFalse(any(path.exists() for path in files))

    def test_linked_config_is_preserved(self):
        home = self.base / "codex"
        home.mkdir()
        destination = self.base / "foreign.json"
        destination.write_text("{}")
        try:
            (home / "hooks.json").symlink_to(destination)
        except OSError as error:
            self.skipTest(f"Native symlink unavailable: {error.errno}")
        with self.assertRaisesRegex(ValueError, "link"):
            installer.plan("codex", home, self.profile, self.repo / "AGENTS.md", Path(sys.executable), Path(self.git), sys.platform)
        self.assertEqual("{}", destination.read_text())

    def test_four_adapters_and_native_execution(self):
        for platform in ("win32", "darwin"):
            for client in ("codex", "claude"):
                with self.subTest(platform=platform, client=client):
                    home = self.base / (client + platform)
                    files, expected = installer.plan(client, home, self.profile, self.repo / "AGENTS.md", Path(sys.executable), Path(self.git), platform)
                    installer.apply_plan(files, expected, home)
                    config = json.loads((home / ("hooks.json" if client == "codex" else "settings.json")).read_text(encoding="utf-8"))
                    handler = config["hooks"]["SessionStart"][0]["hooks"][0]
                    self.assertNotIn("decision", handler)
                    if platform == sys.platform:
                        argv = [handler["command"], *handler["args"]] if client == "claude" else shlex.split(handler["command"])
                        result = subprocess.run(argv, input=json.dumps(self.payload, ensure_ascii=False).encode(), capture_output=True, timeout=20)
                        self.assertEqual(0, result.returncode, result.stderr)
                        self.assertEqual("SessionStart", json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"])
                    elif client == "codex" and platform == "win32":
                        decoded = base64.b64decode(handler["command"].split()[-1]).decode("utf-16-le")
                        self.assertIn(str(sys.executable).replace("'", "''"), decoded)
                    elif client == "codex":
                        self.assertEqual(1, shlex.split(handler["command"]).count(str(sys.executable)))


if __name__ == "__main__":
    unittest.main()
