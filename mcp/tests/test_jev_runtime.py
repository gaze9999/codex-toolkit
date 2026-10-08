"""Focused portable Jev dependency and command diagnostics checks."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/jev-evaluation/scripts"
spec = importlib.util.spec_from_file_location("jev_install_test", SCRIPTS / "install_mcp.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class JevRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root / "runtime"
        self.python = installer.python_path(self.runtime)
        self.python.parent.mkdir(parents=True)
        self.python.touch()
        (self.runtime / "pyvenv.cfg").touch()
        self.requirements = self.root / "requirements.txt"
        self.requirements.write_text('mcp==2.2.0\ntomli==2.2.1; python_version < "3.11"\n', encoding="utf-8")
        self.digest = hashlib.sha256(self.requirements.read_bytes()).hexdigest()
        self.marker = self.runtime / "jev-requirements.sha256"

    def test_healthy_cached_runtime_does_not_install(self):
        self.marker.write_text(self.digest, encoding="ascii")
        with patch.object(installer, "runtime_ready", return_value=True) as ready, patch.object(installer.subprocess, "run") as run:
            self.assertEqual(installer.prepare_runtime(self.runtime, self.requirements), self.python)
        ready.assert_called_once_with(self.python, self.requirements)
        run.assert_not_called()

    def test_matching_marker_cannot_hide_missing_sdk(self):
        self.marker.write_text(self.digest, encoding="ascii")
        with patch.object(installer, "runtime_ready", side_effect=[False, True]), patch.object(installer.subprocess, "run") as run:
            installer.prepare_runtime(self.runtime, self.requirements)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0][:4], [str(self.python), "-m", "pip", "install"])
        self.assertIn("--force-reinstall", commands[0])
        self.assertEqual(commands[0][-2:], ["-r", str(self.requirements)])
        self.assertEqual(commands[1], [str(self.python), "-m", "pip", "check"])
        self.assertEqual(self.marker.read_text(encoding="ascii"), self.digest)

    def test_new_runtime_installs_pins_without_forcing_reinstall(self):
        self.runtime = self.root / "new-runtime"
        self.python = installer.python_path(self.runtime)
        self.marker = self.runtime / "jev-requirements.sha256"
        with patch.object(installer.venv, "EnvBuilder") as builder, patch.object(installer, "runtime_ready", side_effect=[False, True]), patch.object(installer.subprocess, "run") as run:
            installer.prepare_runtime(self.runtime, self.requirements)
        builder.assert_called_once_with(with_pip=True)
        builder.return_value.create.assert_called_once_with(self.runtime)
        self.assertNotIn("--force-reinstall", run.call_args_list[0].args[0])
        self.assertEqual(self.marker.read_text(encoding="ascii"), self.digest)

    def test_changed_requirements_update_marker_after_validation(self):
        self.marker.write_text("previous", encoding="ascii")
        with patch.object(installer, "runtime_ready", return_value=True), patch.object(installer.subprocess, "run") as run:
            installer.prepare_runtime(self.runtime, self.requirements)
        self.assertNotIn("--force-reinstall", run.call_args_list[0].args[0])
        self.assertEqual(self.marker.read_text(encoding="ascii"), self.digest)

    def test_missing_sdk_after_install_does_not_mark_runtime_ready(self):
        with patch.object(installer, "runtime_ready", return_value=False), patch.object(installer.subprocess, "run"):
            with self.assertRaisesRegex(ValueError, "mcp_runtime_unavailable"):
                installer.prepare_runtime(self.runtime, self.requirements)
        self.assertFalse(self.marker.exists())

    def test_unowned_runtime_is_preserved_without_installation(self):
        (self.runtime / "pyvenv.cfg").unlink()
        with patch.object(installer.venv, "EnvBuilder") as builder, patch.object(installer.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "existing_runtime_not_virtual_environment"):
                installer.prepare_runtime(self.runtime, self.requirements)
        builder.assert_not_called()
        run.assert_not_called()
        self.assertTrue(self.python.is_file())

    def test_failed_pip_check_does_not_mark_runtime_ready(self):
        failure = subprocess.CalledProcessError(1, [str(self.python), "-m", "pip", "check"])
        with patch.object(installer, "runtime_ready", return_value=False), patch.object(installer.subprocess, "run", side_effect=[SimpleNamespace(returncode=0), failure]):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.prepare_runtime(self.runtime, self.requirements)
        self.assertFalse(self.marker.exists())

    def test_probe_uses_selected_python_and_exact_sdk(self):
        with patch.object(installer.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
            self.assertTrue(installer.runtime_ready(self.python, self.requirements))
        command = run.call_args.args[0]
        self.assertEqual(command[:4], [str(self.python), "-I", "-B", "-c"])
        self.assertEqual(command[-1], "2.2.0")
        self.assertIn("from mcp.server import MCPServer", command[4])

    def test_probe_failure_returns_not_ready(self):
        with patch.object(installer.subprocess, "run", side_effect=FileNotFoundError):
            self.assertFalse(installer.runtime_ready(self.python, self.requirements))

    def test_hidden_ready_flag_cannot_bypass_dependency_check(self):
        output = io.StringIO()
        config = self.root / "config.toml"
        with patch.object(installer, "runtime_ready", return_value=False), patch.object(installer, "install") as install, redirect_stdout(output):
            status = installer.main(["--runtime", str(self.runtime), "--config", str(config), "--skill-root", str(self.root / "skills"), "--runtime-ready"])
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue())["reason"], "mcp_runtime_unavailable")
        install.assert_not_called()
        self.assertFalse(config.exists())

    def test_dry_run_does_not_prepare_or_install(self):
        output = io.StringIO()
        with patch.object(installer, "prepare_runtime") as prepare, patch.object(installer, "install") as install, redirect_stdout(output):
            self.assertEqual(installer.main(["--runtime", str(self.runtime), "--dry-run"]), 0)
        self.assertEqual(json.loads(output.getvalue())["python"], str(self.python))
        prepare.assert_not_called()
        install.assert_not_called()

    def test_platform_python_locations(self):
        for platform, suffix in [("nt", "Scripts/python.exe"), ("posix", "bin/python")]:
            with self.subTest(platform=platform), patch.object(installer, "os", SimpleNamespace(name=platform)):
                self.assertEqual(installer.python_path(self.runtime), self.runtime / suffix)

    def run_without_site_packages(self, script, *args):
        return subprocess.run([sys.executable, "-S", "-B", str(SCRIPTS / script), *args], capture_output=True, text=True, encoding="utf-8", timeout=15)

    def test_help_does_not_require_sdk(self):
        for script in ["mcp_server.py", "verify_mcp.py"]:
            with self.subTest(script=script):
                result = self.run_without_site_packages(script, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)

    def test_verifier_reports_missing_sdk_without_traceback(self):
        result = self.run_without_site_packages("verify_mcp.py")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["reason"], "mcp_sdk_missing")
        self.assertEqual(json.loads(result.stdout)["python"], sys.executable)
        self.assertEqual(result.stderr, "")

    def test_server_reports_missing_sdk_on_stderr_only(self):
        result = self.run_without_site_packages("mcp_server.py")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(json.loads(result.stderr)["reason"], "mcp_sdk_missing")

    def test_bundle_version_matches_wheel_version(self):
        import tomllib
        package = tomllib.loads((ROOT / "skills/jev-evaluation/pyproject.toml").read_text(encoding="utf-8"))["project"]
        preset = json.loads((ROOT / "mcp/mcp_servers/presets/baseline.json").read_text(encoding="utf-8"))
        jev = next(server for server in preset["servers"] if server["name"] == "jev")
        self.assertEqual(jev["packages"][package["name"]], package["version"])


if __name__ == "__main__":
    unittest.main()
