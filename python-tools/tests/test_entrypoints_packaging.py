from pathlib import Path
import base64
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import cli


ROOT = Path(__file__).resolve().parents[1]


class EntryPointTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Windows PowerShell launchers")
    def test_ps1_launchers_preserve_arguments_cwd_and_exit_codes(self):
        text = '中文 with "quotes" & symbols; trailing\\'
        with tempfile.TemporaryDirectory(prefix="PS launch ") as temporary:
            for shell in ("powershell.exe", "pwsh.exe"):
                executable = shutil.which(shell)
                if not executable:
                    continue
                for name, values, expected in (
                    ("launch-cli.ps1", ["text.tokenizer", "--text", text, "--json"], 0),
                    ("launch-cli.ps1", ["documents.convert_to_markdown", "missing file.txt"], 2),
                ):
                    with self.subTest(shell=shell, launcher=name):
                        payload = base64.b64encode(json.dumps(values, ensure_ascii=False).encode()).decode()
                        command = f"$values = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{payload}')) | ConvertFrom-Json; & '{ROOT / name}' @values; exit $LASTEXITCODE"
                        encoded = base64.b64encode(command.encode("utf-16-le")).decode()
                        result = subprocess.run([executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded], cwd=temporary, capture_output=True, encoding="utf-8", errors="replace", timeout=30)
                        self.assertEqual(result.returncode, expected, result.stderr)
                        if expected == 0:
                            self.assertEqual(json.loads(result.stdout)["chars"], len(text))

    @unittest.skipUnless(sys.platform == "win32", "Windows CMD launchers")
    def test_separate_cmd_launchers_preserve_arguments_and_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(["cmd.exe", "/d", "/c", str(ROOT / "launch-cli.cmd"), "text.tokenizer", "--text", "hello", "--json"], cwd=temporary, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"chars": 5', result.stdout)
            result = subprocess.run(["cmd.exe", "/d", "/c", str(ROOT / "launch-cli.cmd"), "os"], cwd=temporary, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Unknown tool", result.stderr)

    def test_portable_cli_rejects_source_only_execution_and_gui_builders(self):
        for arguments in (["scripts.release", "prepare", "--dry-run"], ["gui.launcher"]):
            with self.subTest(arguments=arguments), patch.dict(os.environ), patch.object(cli, "is_bundled", return_value=True), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                cli.main(list(arguments))
            self.assertEqual(error.exception.code, 2)

    def test_cli_runs_from_unrelated_directory_and_preserves_exit_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            command = [sys.executable, str(ROOT / "launch-cli.py")]
            result = subprocess.run([*command, "text.tokenizer", "--text", "hello", "--json"], cwd=temporary, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"chars": 5', result.stdout)
            result = subprocess.run([*command, "documents.convert_to_markdown", "missing.txt"], cwd=temporary, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_cli_rejects_modules_outside_the_tool_catalog(self):
        result = subprocess.run([sys.executable, str(ROOT / "launch-cli.py"), "os"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unknown tool", result.stderr)

    def test_cli_list_always_uses_utf8_even_with_legacy_python_stdio(self):
        environment = dict(os.environ, PYTHONIOENCODING="cp950")
        result = subprocess.run([sys.executable, str(ROOT / "launch-cli.py"), "--list"], env=environment, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("文件", result.stdout.decode("utf-8"))

    def test_removed_web_option_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            cli.main(["--web"])
        self.assertEqual(error.exception.code, 2)
