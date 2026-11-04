import contextlib
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import install_global_agents as installer


class GlobalReferenceChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source, self.home = self.base / "source", self.base / "home"
        self.source.mkdir()
        (self.source / "AGENTS.md").write_bytes(b"global")
        (self.source / "subagents.config.toml").write_bytes(b"model")
        (self.source / "references/nested").mkdir(parents=True)
        (self.source / "references/nested/AGENTS.md").write_bytes(b"reference")
        (self.source / "references/private.json").write_bytes(b"not selected")

    def run_installer(self, *options):
        output = io.StringIO()
        home_option = "--claude-home" if "claude" in options else "--codex-home"
        args = ["installer", "--source-root", str(self.source), home_option, str(self.home), *options]
        with patch.object(sys, "argv", args), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                result = installer.main()
            except SystemExit as error:
                result = error.code
        return result, output.getvalue()

    def test_claude_global_matches_source_and_keeps_settings(self):
        self.home.mkdir()
        (self.home / "settings.json").write_bytes(b'{"enabledPlugins": {}}')
        (self.source / "AGENTS.zh-TW.md").write_bytes(b"human guide")
        options = ("--client", "claude")
        self.assertEqual(self.run_installer(*options)[0], 1)
        self.assertFalse((self.home / "CLAUDE.md").exists())
        result, output = self.run_installer(*options, "--install")
        self.assertEqual(result, 0, output)
        self.assertEqual((self.home / "CLAUDE.md").read_bytes(), (self.source / "AGENTS.md").read_bytes())
        self.assertEqual((self.home / "CLAUDE.zh-TW.md").read_bytes(), b"human guide")
        self.assertEqual((self.home / "references/nested/AGENTS.md").read_bytes(), b"reference")
        self.assertEqual((self.home / "settings.json").read_bytes(), b'{"enabledPlugins": {}}')
        self.assertFalse((self.home / "subagents.config.toml").exists())
        self.assertFalse((self.home / "AGENTS.md").exists())
        self.assertEqual(self.run_installer(*options)[0], 0)

    def test_claude_conflict_backup_and_role_rejection(self):
        self.home.mkdir()
        (self.home / "CLAUDE.md").write_bytes(b"local customization")
        options = ("--client", "claude", "--select", "AGENTS.md", "--install")
        self.assertEqual(self.run_installer(*options)[0], 1)
        self.assertEqual((self.home / "CLAUDE.md").read_bytes(), b"local customization")
        self.assertEqual(self.run_installer(*options, "--replace")[0], 0)
        backups = list((self.home / "backups/codex-setup").glob("*/CLAUDE.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), b"local customization")
        self.assertEqual(self.run_installer("--client", "claude", "--select", "subagents.config.toml")[0], 2)

    def test_preview_includes_nested_markdown_without_writing(self):
        result, output = self.run_installer()
        self.assertEqual(result, 1)
        self.assertIn(str(self.home / "references/nested/AGENTS.md"), output)
        self.assertNotIn("private.json", output)
        self.assertFalse(self.home.exists())

    def test_install_preserves_paths_and_unrelated_settings(self):
        self.home.mkdir()
        (self.home / "config.toml").write_bytes(b"existing config")
        (self.home / "references").mkdir()
        (self.home / "references/other.md").write_bytes(b"other owner")
        result, output = self.run_installer("--install")
        self.assertEqual(result, 0, output)
        self.assertEqual((self.home / "references/nested/AGENTS.md").read_bytes(), b"reference")
        self.assertFalse((self.home / "references/private.json").exists())
        self.assertEqual((self.home / "config.toml").read_bytes(), b"existing config")
        self.assertEqual((self.home / "references/other.md").read_bytes(), b"other owner")
        self.assertEqual(self.run_installer()[0], 0)

    def test_reference_conflict_blocks_all_pending_writes(self):
        (self.home / "references/nested").mkdir(parents=True)
        (self.home / "references/nested/AGENTS.md").write_bytes(b"custom")
        result, _ = self.run_installer("--install")
        self.assertEqual(result, 1)
        self.assertFalse((self.home / "AGENTS.md").exists())
        self.assertEqual((self.home / "references/nested/AGENTS.md").read_bytes(), b"custom")

    def test_replace_keeps_distinct_nested_backups(self):
        (self.home / "references/nested").mkdir(parents=True)
        (self.home / "AGENTS.md").write_bytes(b"old global")
        (self.home / "references/nested/AGENTS.md").write_bytes(b"old reference")
        result, output = self.run_installer("--install", "--replace")
        self.assertEqual(result, 0, output)
        backups = list((self.home / "backups/codex-setup").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "AGENTS.md").read_bytes(), b"old global")
        self.assertEqual((backups[0] / "references/nested/AGENTS.md").read_bytes(), b"old reference")
        self.assertFalse(list(self.home.rglob("*.tmp")))

    def test_target_parent_file_blocks_all_writes(self):
        self.home.mkdir()
        (self.home / "references").write_bytes(b"existing file")
        result, output = self.run_installer("--install")
        self.assertEqual(result, 2, output)
        self.assertFalse((self.home / "AGENTS.md").exists())

    def create_link(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"Native symlink creation unavailable: {error}")

    def test_source_directory_link_is_rejected_before_writes(self):
        external = self.base / "external"
        external.mkdir()
        (external / "outside.md").write_bytes(b"outside")
        self.create_link(self.source / "references/linked", external, directory=True)
        result, output = self.run_installer("--install")
        self.assertEqual(result, 2, output)
        self.assertFalse(self.home.exists())

    def test_target_parent_link_is_rejected_before_writes(self):
        self.home.mkdir()
        external = self.base / "external"
        external.mkdir()
        self.create_link(self.home / "references", external, directory=True)
        result, output = self.run_installer("--install")
        self.assertEqual(result, 2, output)
        self.assertFalse((self.home / "AGENTS.md").exists())
        self.assertFalse(list(external.iterdir()))

    def test_windows_reparse_attribute_is_a_link(self):
        metadata = SimpleNamespace(st_mode=installer.stat.S_IFDIR, st_file_attributes=installer.stat.FILE_ATTRIBUTE_REPARSE_POINT)
        with patch.object(Path, "lstat", return_value=metadata):
            self.assertTrue(installer.is_link(self.source))

    def test_select_installs_only_requested_human_guide(self):
        (self.source / "AGENTS.zh-TW.md").write_bytes(b"human guide")
        result, output = self.run_installer("--select", "AGENTS.zh-TW.md", "--install")
        self.assertEqual(result, 0, output)
        self.assertEqual((self.home / "AGENTS.zh-TW.md").read_bytes(), b"human guide")
        self.assertFalse((self.home / "AGENTS.md").exists())
        self.assertEqual(self.run_installer("--select", "AGENTS.zh-TW.md")[0], 0)

    def test_selected_role_validates_before_any_write(self):
        (self.source / "agents").mkdir()
        role = self.source / "agents/reviewer.toml"
        role.write_text('name = "reviewer"', encoding="utf-8")
        options = ("--select", "AGENTS.md", "--select", "agents/reviewer.toml", "--install")
        self.assertEqual(self.run_installer(*options)[0], 2)
        self.assertFalse(self.home.exists())
        role.write_text('name = "reviewer"\ndescription = "Review"\ndeveloper_instructions = "Read only"\n', encoding="utf-8")
        result, output = self.run_installer(*options)
        self.assertEqual(result, 0, output)
        self.assertEqual((self.home / "agents/reviewer.toml").read_bytes(), role.read_bytes())

    def test_select_rejects_escape_config_duplicates_and_missing(self):
        for name in ("../AGENTS.md", "references/../AGENTS.md", "config.toml", "C:/AGENTS.md", "references/missing.md"):
            with self.subTest(name=name):
                self.assertEqual(self.run_installer("--select", name, "--install")[0], 2)
                self.assertFalse(self.home.exists())
        self.assertEqual(self.run_installer("--select", "AGENTS.md", "--select", "AGENTS.md", "--install")[0], 2)

    def test_select_conflict_keeps_unselected_files(self):
        self.home.mkdir()
        (self.home / "AGENTS.md").write_bytes(b"old")
        (self.home / "config.toml").write_bytes(b"preserve")
        self.assertEqual(self.run_installer("--select", "AGENTS.md", "--install")[0], 1)
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), b"old")
        result, output = self.run_installer("--select", "AGENTS.md", "--install", "--replace")
        self.assertEqual(result, 0, output)
        self.assertEqual((self.home / "config.toml").read_bytes(), b"preserve")
        self.assertFalse((self.home / "subagents.config.toml").exists())

if __name__ == "__main__":
    unittest.main()
