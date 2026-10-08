from __future__ import annotations

import json
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

from distribution import build_cli, smoke_cli
from scripts.prepare_release import _copy_ignore, source_snapshot
from shared import runtime, tool_catalog


class DistributionTests(unittest.TestCase):
    def test_source_snapshot_excludes_legacy_gui_files_without_git(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "VERSION").write_text("0.4.2\n", encoding="utf-8")
            for name in (".workbench-ui/private.js", "src/gui/resources/web/index.html", "setup/runtime/WebView2/cache"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture", encoding="utf-8")
            self.assertEqual(set(source_snapshot(root, "0.4.2")), {"VERSION"})
            self.assertIn("gui", _copy_ignore(str(root / "src"), ["gui", "documents"]))

    def test_source_and_frozen_resource_roots(self):
        self.assertEqual(runtime.resource_root(), Path(__file__).resolve().parents[1])
        with patch("sys.frozen", True, create=True), patch("sys._MEIPASS", "runtime-root", create=True):
            self.assertTrue(runtime.is_bundled())
            self.assertEqual(runtime.resource_root(), Path("runtime-root"))

    def test_bundled_catalog_uses_shared_resources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = root / "shared/resources/catalog.json"
            catalog.parent.mkdir(parents=True)
            catalog.write_text(json.dumps([tool_catalog.TOOLS[0].payload()]), encoding="utf-8")
            with patch.object(tool_catalog, "resource_root", return_value=root):
                tools = tool_catalog.load_bundled_catalog()
            self.assertEqual(tools[0].module, tool_catalog.TOOLS[0].module)

    def test_cli_resources_seed_encodings_and_restore_environment(self):
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                calls = []

                def encoding(name):
                    calls.append((name, os.environ["TIKTOKEN_CACHE_DIR"]))
                    if fail:
                        raise RuntimeError("encoding unavailable")

                module = types.SimpleNamespace(get_encoding=encoding)
                with patch.object(build_cli, "ROOT", root), patch.dict(sys.modules, tiktoken=module), patch.dict(os.environ, TIKTOKEN_CACHE_DIR="original"):
                    if fail:
                        with self.assertRaisesRegex(RuntimeError, "encoding unavailable"):
                            build_cli.prepare_resources()
                    else:
                        resources = build_cli.prepare_resources()
                        self.assertEqual(resources, root / ".build-inputs/cli")
                        payload = json.loads((resources / "catalog.json").read_text(encoding="utf-8"))
                        self.assertEqual(len(payload), len(tool_catalog.TOOLS))
                        self.assertEqual([name for name, _cache in calls], ["o200k_base", "cl100k_base"])
                    self.assertEqual(os.environ["TIKTOKEN_CACHE_DIR"], "original")
                    self.assertTrue(all(cache == str(root / ".build-inputs/cli/tiktoken") for _name, cache in calls))

    def test_archive_preserves_application_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = root / "MyPyToolsCLI"
            app.mkdir()
            (app / "launch-cli.exe").write_bytes(b"fixture")
            with patch("sys.platform", "win32"):
                build_cli.archive_application(app, root / "cli.zip")
            with zipfile.ZipFile(root / "cli.zip") as archive:
                self.assertEqual(archive.namelist(), ["MyPyToolsCLI/launch-cli.exe"])
            with patch("sys.platform", "darwin"), patch.object(build_cli, "run") as run:
                build_cli.archive_application(app, root / "mac.zip")
            self.assertEqual(run.call_args.args[0][:5], ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent"])

    def test_build_plan_has_no_frontend_dependency(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "VERSION").write_text("0.4.2\n", encoding="utf-8")
            launchers = root / "src/distribution"
            launchers.mkdir(parents=True)
            (launchers / "launch-cli.cmd").write_text("fixture", encoding="utf-8")
            (root / "launch-cli.ps1").write_text("fixture", encoding="utf-8")
            commands = []

            def run(command):
                commands.append(command)
                destination = Path(command[command.index("--distpath") + 1]) / "MyPyToolsCLI"
                destination.mkdir(parents=True)
                (destination / "launch-cli.exe").write_bytes(b"not an executable, unit test fixture")

            def archive(_app, target):
                target.write_bytes(b"not an archive, unit test fixture")

            with patch.object(build_cli, "ROOT", root), patch.object(build_cli, "prepare_resources") as resources, patch.object(build_cli, "run", side_effect=run), patch.object(build_cli, "archive_application", side_effect=archive), patch.object(build_cli.importlib.metadata, "version", return_value="fixture"), patch("sys.platform", "win32"), patch("platform.machine", return_value="AMD64"), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(build_cli.main(["--output-root", str(root / "output")]), 0)
                resources.assert_called_once_with()
                marker = root / "output/my-py-tools-0.4.2-cli-windows-x64/cli-manifest-windows-x64.json"
                metadata = json.loads(marker.read_text(encoding="utf-8"))
                self.assertEqual(metadata["modes"], ["terminal"])
                self.assertEqual(set(metadata["entrypoints"]), {"cli", "cmd", "ps1"})
                self.assertNotIn("interface", metadata)
                self.assertEqual(len(commands), 1)
                self.assertEqual(commands[0][1:3], ["-m", "PyInstaller"])
                with self.assertRaises(SystemExit) as error:
                    build_cli.main(["--output-root", str(root / "output")])
                self.assertEqual(error.exception.code, 2)

    def test_smoke_verifies_terminal_without_background_service(self):
        commands = []

        def execute(command, **options):
            commands.append(command)
            self.assertEqual(options["timeout"], 45)
            self.assertNotIn("PYTHONPATH", options["env"])
            self.assertNotIn("PYTHONHOME", options["env"])
            self.assertNotIn("TIKTOKEN_CACHE_DIR", options["env"])
            operation = command[1]
            output, code = "", 0
            if operation == "--list":
                output = "documents.convert_to_markdown"
            elif operation == "text.tokenizer":
                output = json.dumps({"chars": 5, "method": "tiktoken"})
            elif operation == "documents.convert_to_markdown":
                Path(command[2]).with_suffix(".md").write_text("Portable CLI conversion", encoding="utf-8")
            else:
                code = 2
            return subprocess.CompletedProcess(command, code, output, "")

        with patch.object(smoke_cli.subprocess, "run", side_effect=execute):
            result = smoke_cli.verify(Path("launch-cli.exe"))
        self.assertTrue(result["passed"])
        self.assertEqual(len(commands), 5)

    def test_smoke_rejects_failures_fallback_and_timeout(self):
        results = [
            subprocess.CompletedProcess([], 1, "", "failed"),
            subprocess.CompletedProcess([], 0, "missing catalog", ""),
            [
                subprocess.CompletedProcess([], 0, "documents.convert_to_markdown", ""),
                subprocess.CompletedProcess([], 0, '{"chars": 5, "method": "fallback"}', ""),
            ],
            subprocess.TimeoutExpired("fixture", 45),
        ]
        for result in results:
            with self.subTest(result=type(result).__name__):
                options = {"side_effect": result} if isinstance(result, (list, Exception)) else {"return_value": result}
                with patch.object(smoke_cli.subprocess, "run", **options), self.assertRaises((RuntimeError, subprocess.TimeoutExpired)):
                    smoke_cli.verify(Path("launch-cli.exe"))

    def test_release_workflow_and_spec_are_terminal_only(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root.parent / ".github/workflows/python-tools-release.yml").read_text(encoding="utf-8")
        spec = (root / "src/distribution/cli.spec").read_text(encoding="utf-8")
        self.assertIn("needs: [source, cli]", workflow)
        self.assertIn("$assets.Count -ne 10", workflow)
        self.assertIn('shared/resources', spec)
        for obsolete in ("workbench-ui.json", "WORKBENCH_UI_READ_TOKEN", "setup-node", "WEBVIEW2_", "src/gui/", "launch-web", "launch-gui"):
            self.assertNotIn(obsolete, workflow)
            self.assertNotIn(obsolete, spec)
        self.assertFalse((root / "launch-gui.cmd").exists())
        self.assertFalse((root / "launch-web.cmd").exists())


if __name__ == "__main__":
    unittest.main()
