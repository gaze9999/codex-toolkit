"""Check interpreter selection without invoking a real installer."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
WINDOWS = os.name == "nt" and bool(shutil.which("cmd.exe"))
POSIX = os.name != "nt" and bool(shutil.which("sh"))


class BootstrapLauncherTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="bootstrap-launcher-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "fixture with spaces"
        self.launch = self.root / "mcp/scripts/launch"
        self.launch.mkdir(parents=True)
        for name in ("bootstrap-mcp.cmd", "bootstrap-mcp.sh"):
            shutil.copyfile(ROOT / "mcp/scripts/launch" / name, self.launch / name)
        (self.launch.parent / "bootstrap_mcp.py").write_text(
            "raise SystemExit('Fixture must not invoke an actual bootstrap')\n", encoding="utf-8"
        )
        self.binary = self.root / "bin"
        self.binary.mkdir()
        self.log = self.root / "calls.log"
        self.env = dict(os.environ)
        self.env.update({"PATH": str(self.binary) + os.pathsep + self.env.get("PATH", ""), "CODEX_HOME": str(self.root / "home"), "FAKE_LOG": str(self.log), "FAKE_EXIT": "7"})
        self.env.pop("CODEX_SETUP_PYTHON", None)

    def windows_commands(self, version="none", path_python=False):
        self.env["FAKE_PY_VERSION"] = version
        self.env["FAKE_PYTHON_OK"] = "1" if path_python else "0"
        (self.binary / "py.cmd").write_text(
            '@echo off\n>>"%FAKE_LOG%" echo py %*\n'
            'if "%~2"=="-I" if "%~1"=="-%FAKE_PY_VERSION%" exit /b 0\n'
            'if "%~2"=="-X" if "%~1"=="-%FAKE_PY_VERSION%" exit /b %FAKE_EXIT%\n'
            'exit /b 1\n', encoding="utf-8"
        )
        (self.binary / "python.cmd").write_text(
            '@echo off\n>>"%FAKE_LOG%" echo python %*\n'
            'if "%~1"=="-I" if "%FAKE_PYTHON_OK%"=="1" exit /b 0\n'
            'if "%~1"=="-X" exit /b %FAKE_EXIT%\n'
            'exit /b 1\n', encoding="utf-8"
        )

    def run_windows(self):
        command = subprocess.list2cmdline([os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "call", "bootstrap-mcp.cmd", "--context7", "--apply", "two words"])
        return subprocess.run(command, cwd=self.launch, env=self.env, capture_output=True, text=True, timeout=15)

    @unittest.skipUnless(WINDOWS, "Windows CMD required")
    def test_windows_default_supported_launcher_preserves_exit_code(self):
        self.windows_commands(version="3")
        result = self.run_windows()
        self.assertEqual(result.returncode, 7, result.stderr)
        calls = self.log.read_text(encoding="utf-8").lower()
        self.assertIn("py -3 -x utf8 -b", calls)
        self.assertNotIn("python -i", calls)

    @unittest.skipUnless(WINDOWS, "Windows CMD required")
    def test_windows_old_default_falls_back_to_explicit_supported_version(self):
        self.windows_commands(version="3.12")
        result = self.run_windows()
        self.assertEqual(result.returncode, 7, result.stderr)
        calls = self.log.read_text(encoding="utf-8").lower()
        self.assertIn("py -3 -i -b -c", calls)
        self.assertIn("py -3.12 -x utf8 -b", calls)
        self.assertIn('--context7 --apply "two words"', calls)
        self.assertNotIn("python -i", calls)

    @unittest.skipUnless(WINDOWS, "Windows CMD required")
    def test_windows_falls_back_to_path_python(self):
        self.windows_commands(path_python=True)
        result = self.run_windows()
        self.assertEqual(result.returncode, 7, result.stderr)
        calls = self.log.read_text(encoding="utf-8").lower()
        self.assertIn("python -i -b -c", calls)
        self.assertIn("python -x utf8 -b", calls)

    @unittest.skipUnless(WINDOWS, "Windows CMD required")
    def test_windows_rejects_only_old_interpreters(self):
        self.windows_commands()
        result = self.run_windows()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Python 3.11+", result.stderr)
        self.assertNotIn("bootstrap_mcp.py", self.log.read_text(encoding="utf-8"))

    def shell_commands(self, supported="none"):
        self.env["FAKE_OK"] = supported
        for name in ("python3", "python3.13", "python"):
            executable = self.binary / name
            executable.write_text(
                '#!/bin/sh\nprintf "%s\\0" "${0##*/}" "$@" >> "$FAKE_LOG"\nprintf "\\036" >> "$FAKE_LOG"\n'
                'if [ "$1" = "-I" ]; then [ "${0##*/}" = "$FAKE_OK" ]; exit $?; fi\n'
                'exit "$FAKE_EXIT"\n', encoding="utf-8"
            )
            executable.chmod(0o755)

    def run_shell(self):
        return subprocess.run(["sh", str(self.launch / "bootstrap-mcp.sh"), "--context7", "--apply", "two words"], cwd=self.root, env=self.env, capture_output=True, text=True, timeout=15)

    @unittest.skipUnless(POSIX, "POSIX shell required")
    def test_shell_skips_old_python_and_preserves_arguments(self):
        self.shell_commands(supported="python3.13")
        result = self.run_shell()
        self.assertEqual(result.returncode, 7, result.stderr)
        calls = [item.split(b"\0")[:-1] for item in self.log.read_bytes().split(b"\x1e") if item]
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[-1][:4], [b"python3.13", b"-X", b"utf8", b"-B"])
        self.assertEqual(calls[-1][-3:], [b"--context7", b"--apply", b"two words"])
        self.assertIn(str(self.launch.parent / "bootstrap_mcp.py").encode(), calls[-1])

    @unittest.skipUnless(POSIX, "POSIX shell required")
    def test_shell_stops_without_supported_python(self):
        self.shell_commands()
        result = self.run_shell()
        self.assertEqual(result.returncode, 2)
        self.assertIn("Python 3.11+", result.stderr)
        self.assertNotIn("bootstrap_mcp.py", self.log.read_bytes().decode())

    @unittest.skipUnless(POSIX, "POSIX shell required")
    def test_shell_respects_explicit_supported_python(self):
        self.shell_commands(supported="python3.13")
        self.env["CODEX_SETUP_PYTHON"] = str(self.binary / "python3.13")
        result = self.run_shell()
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(len([item for item in self.log.read_bytes().split(b"\x1e") if item]), 2)

    @unittest.skipUnless(POSIX, "POSIX shell required")
    def test_shell_rejects_invalid_explicit_python_without_fallback(self):
        self.shell_commands(supported="python3.13")
        self.env["CODEX_SETUP_PYTHON"] = str(self.binary / "python3")
        result = self.run_shell()
        self.assertEqual(result.returncode, 2)
        self.assertIn("Selected Python", result.stderr)


if __name__ == "__main__":
    unittest.main()
