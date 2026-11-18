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

from maintenance.rewrite_git_history import main as rewrite_history_main
from markdown.guarded_markdown_update import main as guarded_markdown_main
from text.tokenizer import main as tokenizer_main


@contextlib.contextmanager
def captured_output():
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        yield stdout, stderr


class CoreToolTests(unittest.TestCase):
    def test_guarded_markdown_update_supports_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left.md"
            replacement = root / "replacement.md"
            left.write_text("# A\n\n- old\n", encoding="utf-8")
            replacement.write_text("# A\n\n- replacement\n", encoding="utf-8")

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

    def test_tokenizer_falls_back_for_unknown_encoding(self) -> None:
        with captured_output() as (stdout, _):
            self.assertEqual(
                tokenizer_main(["--text", "測試 text", "--encoding", "missing-encoding", "--json"]),
                0,
            )
        self.assertEqual(json.loads(stdout.getvalue())["method"], "fallback")

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
