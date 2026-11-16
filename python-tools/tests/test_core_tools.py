from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from maintenance.cleanup_work_artifacts import main as cleanup_main
from maintenance.rewrite_git_history import main as rewrite_history_main
from markdown.guarded_markdown_update import main as guarded_markdown_main
from markdown.markdown_semantic_diff import main as markdown_diff_main
from text.tokenizer import main as tokenizer_main


@contextlib.contextmanager
def captured_output():
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        yield stdout, stderr


class CoreToolTests(unittest.TestCase):
    def test_markdown_tools_support_explicit_files_and_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left.md"
            right = root / "right.md"
            replacement = root / "replacement.md"
            left.write_text("# A\n\n- old\n", encoding="utf-8")
            right.write_text("# A\n\n- new\n", encoding="utf-8")
            replacement.write_text("# A\n\n- replacement\n", encoding="utf-8")

            with captured_output() as (stdout, _):
                self.assertEqual(
                    markdown_diff_main(["--left", str(left), "--right", str(right)]),
                    0,
                )
            self.assertIn("only_left", stdout.getvalue())

            before = left.read_bytes()
            expected = hashlib.sha256(before).hexdigest()
            with captured_output() as (stdout, _):
                self.assertEqual(
                    guarded_markdown_main(
                        [
                            "--target-file",
                            str(left),
                            "replace",
                            "context",
                            "--content",
                            str(replacement),
                            "--expect",
                            expected,
                            "--section",
                            "# A",
                        ]
                    ),
                    0,
                )
            self.assertEqual(json.loads(stdout.getvalue())["status"], "dry-run")
            self.assertEqual(left.read_bytes(), before)

    def test_markdown_diff_ignores_fences_and_reports_duplicate_or_order_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left.md"
            right = root / "right.md"
            left.write_text("# A\n\n- first\n- second\n- second\n```md\n# ignored\n```\n", encoding="utf-8")
            right.write_text("# A\n\n- second\n- first\n```md\n# different ignored\n```\n", encoding="utf-8")

            with captured_output() as (stdout, _):
                self.assertEqual(markdown_diff_main(["--left", str(left), "--right", str(right)]), 0)

            changes = json.loads(stdout.getvalue())["changes"]
            self.assertEqual(changes["headings"]["only_left"], [])
            self.assertEqual(changes["list_items"]["only_left"], ["- second"])

    def test_tokenizer_and_cleanup_preview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with captured_output() as (stdout, _):
                self.assertEqual(
                    tokenizer_main(["--text", "測試 text", "--encoding", "missing-encoding", "--json"]),
                    0,
                )
            self.assertEqual(json.loads(stdout.getvalue())["method"], "fallback")

            cache = root / "project" / "__pycache__"
            cache.mkdir(parents=True)
            cache.joinpath("sample.pyc").write_bytes(b"cache")
            output = root / "cleanup-output"
            with captured_output() as (stdout, _):
                self.assertEqual(
                    cleanup_main(
                        [
                            "--root",
                            str(root / "project"),
                            "--min-age-days",
                            "0",
                            "--output-dir",
                            str(output),
                        ]
                    ),
                    0,
                )
            self.assertIn('"mode": "preview"', stdout.getvalue())
            self.assertTrue(cache.is_dir())

    def test_cleanup_preserves_unowned_quarantine_and_nested_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "cleanup-output"
            unrelated = output / "quarantine" / "personal-backup"
            unrelated.mkdir(parents=True)
            unrelated.joinpath("keep.txt").write_text("keep", encoding="utf-8")

            with captured_output():
                self.assertEqual(
                    cleanup_main(
                        [
                            "--output-dir",
                            str(output),
                            "--purge-quarantine",
                            "--older-than-days",
                            "0",
                        ]
                    ),
                    0,
                )
            self.assertTrue(unrelated.is_dir())

            nested_worktree = root / "project" / "tmp"
            nested_worktree.mkdir(parents=True)
            nested_worktree.joinpath(".git").write_text("gitdir: elsewhere", encoding="utf-8")
            old = 1_600_000_000
            os.utime(nested_worktree, (old, old))
            with captured_output() as (stdout, _):
                self.assertEqual(
                    cleanup_main(
                        [
                            "--root",
                            str(root / "project"),
                            "--include-work-dirs",
                            "--min-age-days",
                            "0",
                            "--output-dir",
                            str(output),
                        ]
                    ),
                    0,
                )
            self.assertEqual(json.loads(stdout.getvalue().split("Manifest:", 1)[0])["candidate_count"], 0)

    def test_cleanup_purges_only_owned_quarantine_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            cache = project / "__pycache__"
            cache.mkdir(parents=True)
            cache.joinpath("sample.pyc").write_bytes(b"cache")
            output = root / "cleanup-output"

            with captured_output():
                self.assertEqual(
                    cleanup_main(
                        [
                            "--root",
                            str(project),
                            "--min-age-days",
                            "0",
                            "--output-dir",
                            str(output),
                            "--apply",
                        ]
                    ),
                    0,
                )
            runs = list((output / "quarantine").glob("cache-cleanup-*"))
            self.assertEqual(len(runs), 1)
            self.assertTrue(runs[0].joinpath(".my-py-tools-quarantine.json").is_file())

            with captured_output() as (stdout, _):
                self.assertEqual(
                    cleanup_main(
                        [
                            "--output-dir",
                            str(output),
                            "--purge-quarantine",
                            "--older-than-days",
                            "0",
                        ]
                    ),
                    0,
                )
            self.assertEqual(json.loads(stdout.getvalue())["removed_runs"], 1)
            self.assertFalse(runs[0].exists())

    def test_history_rewrite_cancel_does_not_modify_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test User"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)

            with patch("builtins.input", return_value="CANCEL"), captured_output():
                self.assertEqual(rewrite_history_main(["--repo", str(root)]), 0)

            self.assertFalse((root / ".bundle").exists())
            exclude = root / ".git" / "info" / "exclude"
            if exclude.is_file():
                self.assertNotIn("git-history-rewrite-helper", exclude.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
