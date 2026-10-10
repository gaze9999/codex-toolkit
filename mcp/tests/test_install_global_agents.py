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
        args = ["installer", "--source-root", str(self.source), "--codex-home", str(self.home), *options]
        with patch.object(sys, "argv", args), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                result = installer.main()
            except SystemExit as error:
                result = error.code
        return result, output.getvalue()

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

if __name__ == "__main__":
    unittest.main()
