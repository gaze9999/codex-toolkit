"""PreToolUse guards, the SessionStart environment line and the SubagentStart note on synthetic repositories."""
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import agent_hooks as hooks
import install_agent_hooks as installer

PERSONAL = "personal@example.invalid"
GUARDS = {"identity": {"owners": ["https://github.com/owner"], "email": PERSONAL}, "ai_coauthor": True, "history": True,
          "generated": [{"repository": "https://github.com/owner/distribution", "allow": ["AGENTS.override.md", ".codex/*"]}]}


class GuardTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="guards 空白 ")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.git = shutil.which("git")
        self.personal = self.repo("personal", "git@github.com:owner/personal.git", PERSONAL)
        self.company = self.repo("company", "https://git.example.invalid/team/app.git", None)
        self.generated = self.repo("distribution", "https://github.com/owner/distribution.git", PERSONAL)
        self.state = self.base / "state"
        self.policy = {"schema_version": 1, "entries": [], "start_note": "n", "stop_note": "s", "git": self.git,
                       "operations": "ops.md", "guards": GUARDS}

    def repo(self, name, origin, email):
        root = self.base / name
        root.mkdir()
        for args in (("init", "-q"), ("remote", "add", "origin", origin)):
            subprocess.run([self.git, *args], cwd=root, check=True)
        if email:
            subprocess.run([self.git, "config", "user.email", email], cwd=root, check=True)
        return root

    def pre(self, tool, tool_input, cwd=None, client="codex"):
        payload = {"hook_event_name": "PreToolUse", "session_id": "s1", "cwd": str(cwd or self.personal),
                   "tool_name": tool, "tool_input": tool_input}
        return hooks.handle(payload, self.policy, client, self.state)

    def denied(self, result):
        output = result.get("hookSpecificOutput", {})
        return output.get("permissionDecision") == "deny" and output["permissionDecisionReason"]

    def test_personal_identity_passes_and_mismatch_is_denied(self):
        self.assertEqual({}, self.pre("Bash", {"command": "git commit -m 'fix'"}))
        subprocess.run([self.git, "config", "user.email", "work@example.invalid"], cwd=self.personal, check=True)
        reason = self.denied(self.pre("Bash", {"command": "git add -A && git commit -m fix"}))
        self.assertIn("personal repository", reason)

    def test_other_repository_needs_its_own_local_identity(self):
        command = f"cd {shlex.quote(str(self.company))} && git commit -m fix"
        self.assertIn("repository-local user.email", self.denied(self.pre("Bash", {"command": command})))
        subprocess.run([self.git, "config", "user.email", "work@example.invalid"], cwd=self.company, check=True)
        self.assertEqual({}, self.pre("Bash", {"command": f"git -C {shlex.quote(str(self.company))} commit -m fix"}))

    def test_ai_trailer_and_history_rewrites_are_denied(self):
        message = "git commit -m \"$(cat <<'EOF'\nfix\n\nCo-Authored-By: Claude <noreply@anthropic.com>\nEOF\n)\""
        self.assertIn("AI co-author", self.denied(self.pre("Bash", {"command": message})))
        for command in ("git push --force origin main", "git push origin +main", "git push origin :refs/tags/v1",
                        "git push --delete origin v1", "git tag -d v1", "git tag -f v1", "git filter-repo --path x"):
            with self.subTest(command=command):
                self.assertTrue(self.denied(self.pre("Bash", {"command": command})))
        self.assertIn("/hooks", self.denied(self.pre("Bash", {"command": "git push --force"})))
        asked = self.pre("Bash", {"command": "git push --force origin main"}, client="claude")["hookSpecificOutput"]
        self.assertEqual("ask", asked["permissionDecision"])
        self.assertIn("published history", asked["permissionDecisionReason"])
        claude_trailer = self.pre("Bash", {"command": message + " && git push --force"}, client="claude")
        self.assertIn("AI co-author", self.denied(claude_trailer))
        for command in ("git push origin main", "git push -u origin feature", "git tag -a v2 -m v2", "git status", "ls -la"):
            with self.subTest(command=command):
                self.assertEqual({}, self.pre("Bash", {"command": command}))

    def test_generated_distribution_edits_are_denied_except_allowed_paths(self):
        target = self.generated / "plugins/x/SKILL.md"
        self.assertIn("generated output", self.denied(self.pre("Write", {"file_path": str(target)})))
        self.assertEqual({}, self.pre("Edit", {"file_path": str(self.generated / "AGENTS.override.md")}))
        self.assertEqual({}, self.pre("Write", {"file_path": str(self.generated / ".codex/config.toml")}))
        self.assertEqual({}, self.pre("Write", {"file_path": str(self.personal / "src/app.py")}))
        patch = "*** Begin Patch\n*** Update File: catalog.json\n@@\n-a\n+b\n*** End Patch\n"
        self.assertTrue(self.denied(self.pre("apply_patch", {"command": patch}, cwd=self.generated)))

    def test_missing_rules_or_inputs_pass_silently(self):
        del self.policy["guards"]
        self.assertEqual({}, self.pre("Bash", {"command": "git push --force"}))
        self.policy["guards"] = GUARDS
        self.assertEqual({}, self.pre("Bash", {"command": 7}))
        with self.assertRaises(ValueError):
            hooks.handle({"hook_event_name": "PreToolUse", "session_id": "s1", "cwd": "relative"}, self.policy, "codex", self.state)

    def test_session_environment_and_subagent_note(self):
        self.policy["session_environment"] = True
        start = {"hook_event_name": "SessionStart", "session_id": "s1", "cwd": str(self.personal), "source": "startup"}
        text = hooks.handle(start, self.policy, "claude", self.state)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Environment: ", text)
        self.assertIn("repository: personal", text)
        child = {"hook_event_name": "SubagentStart", "session_id": "s1", "cwd": str(self.personal), "agent_type": "Explore"}
        self.assertEqual({}, hooks.handle(child, self.policy, "codex", self.state))
        self.policy["subagent_note"] = "Use concise English."
        result = hooks.handle(child, self.policy, "codex", self.state)
        self.assertEqual("SubagentStart", result["hookSpecificOutput"]["hookEventName"])
        self.assertEqual("Use concise English.", result["hookSpecificOutput"]["additionalContext"])


class GuardInstallTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.profile = {"schema_version": 1, "entries": ["AGENTS.md"], "start_note": "n", "stop_note": "s"}
        self.operations = self.base / "ops.md"
        self.operations.write_text("ops", encoding="utf-8")

    def test_events_follow_selected_features(self):
        profile = dict(self.profile, guards=GUARDS, subagent_note="Use concise English.", session_environment=True, reply_punctuation=True)
        installer.validate_profile(profile)
        files, _ = installer.plan("codex", self.base / "codex", profile, self.operations, Path(sys.executable), Path("git"), sys.platform, None)
        manifest = next(json.loads(data) for path, data in files.items() if path.name == "manifest.json")
        self.assertEqual(["SessionStart", "PreToolUse", "PostToolUse", "SubagentStart", "Stop", "SubagentStop"], list(manifest["groups"]))
        self.assertEqual(installer.GUARD_MATCHER, manifest["groups"]["PreToolUse"]["matcher"])
        self.assertEqual(600, manifest["groups"]["SubagentStart"]["hooks"][0]["additionalContextLimit"])

    def test_invalid_guard_profiles_are_rejected(self):
        for guards in ({}, {"unknown": True}, {"history": "yes"}, {"identity": {"owners": ["github.com/x"], "email": PERSONAL}},
                       {"identity": {"owners": ["https://github.com/x"]}}, {"generated": [{"repository": "x"}]},
                       {"generated": [{"repository": "https://github.com/x/y", "allow": ["../escape"]}]}):
            with self.subTest(guards=guards), self.assertRaises(ValueError):
                installer.validate_profile(dict(self.profile, guards=guards))
        for note in ("", 7, "x" * 401):
            with self.subTest(note=note), self.assertRaises(ValueError):
                installer.validate_profile(dict(self.profile, subagent_note=note))


if __name__ == "__main__":
    unittest.main()
