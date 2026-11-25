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


@contextlib.contextmanager
def captured_output():
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        yield stdout, stderr


class CoreToolTests(unittest.TestCase):
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
