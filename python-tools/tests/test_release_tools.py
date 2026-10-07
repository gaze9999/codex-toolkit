from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


SCRIPTS = Path(__file__).resolve().parents[1] / "src/scripts"
PREPARE_PATH = SCRIPTS / "prepare_release.py"
spec = importlib.util.spec_from_file_location("my_py_prepare_release", PREPARE_PATH)
prepare_release = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(prepare_release)
sys.path.insert(0, str(SCRIPTS))
import release  # noqa: E402


def fake_wheel(name: str, version: str) -> bytes:
    distribution = name.replace("-", "_")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(f"{distribution}-{version}.dist-info/METADATA", f"Name: {name}\nVersion: {version}\n")
    return stream.getvalue()


class ReleaseToolTests(unittest.TestCase):
    def test_independent_cli_assets_validate_platform_hash_and_permissions(self):
        for system in ("windows", "macos"):
            with self.subTest(system=system):
                directory = self.repo / system
                directory.mkdir()
                archive = directory / f"my-py-tools-0.2.0-cli-{system}-x64.zip"
                executable = "MyPyToolsCLI/launch-cli" + (".exe" if system == "windows" else "")
                info = zipfile.ZipInfo(executable)
                info.external_attr = 0o100755 << 16
                with zipfile.ZipFile(archive, "w") as zipped:
                    zipped.writestr(info, b"fixture")
                    zipped.writestr("MyPyToolsCLI/_internal/shared/resources/catalog.json", b"[]")
                    if system == "windows":
                        zipped.writestr("MyPyToolsCLI/launch-cli.cmd", b"fixture")
                        zipped.writestr("MyPyToolsCLI/launch-cli.ps1", b"fixture")
                metadata = {"product": "cli", "version": "0.2.0", "os": system, "architecture": "x64", "asset": archive.name, "entrypoints": {"cli": executable}, "size": archive.stat().st_size, "sha256": prepare_release.digest(archive.read_bytes())}
                metadata.update(modes=["terminal"])
                if system == "windows":
                    metadata["entrypoints"]["cmd"] = "MyPyToolsCLI/launch-cli.cmd"
                    metadata["entrypoints"]["ps1"] = "MyPyToolsCLI/launch-cli.ps1"
                marker = directory / f"cli-manifest-{system}-x64.json"
                marker.write_text(json.dumps(metadata), encoding="utf-8")
                self.assertEqual(release.cli_assets(directory, "0.2.0")[0], archive)
                metadata["modes"] = ["terminal", "browser"]
                marker.write_text(json.dumps(metadata), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "terminal mode only"):
                    release.cli_assets(directory, "0.2.0")
                metadata["modes"] = ["terminal"]
                metadata["sha256"] = "0" * 64
                marker.write_text(json.dumps(metadata), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    release.cli_assets(directory, "0.2.0")
                with zipfile.ZipFile(archive, "a") as zipped:
                    zipped.writestr("MyPyToolsCLI/WebView2/msedge.dll", b"fixture")
                metadata.update(size=archive.stat().st_size, sha256=prepare_release.digest(archive.read_bytes()))
                marker.write_text(json.dumps(metadata), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "GUI executable"):
                    release.cli_assets(directory, "0.2.0")

    def test_mac_cli_archive_requires_executable_permissions(self):
        directory = self.repo / "cli"
        directory.mkdir()
        archive = directory / "my-py-tools-0.2.0-cli-macos-arm64.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("MyPyToolsCLI/launch-cli", b"fixture")
            zipped.writestr("MyPyToolsCLI/_internal/shared/resources/catalog.json", b"[]")
        metadata = {"product": "cli", "version": "0.2.0", "os": "macos", "architecture": "arm64", "asset": archive.name, "entrypoints": {"cli": "MyPyToolsCLI/launch-cli"}, "size": archive.stat().st_size, "sha256": prepare_release.digest(archive.read_bytes())}
        metadata.update(modes=["terminal"])
        (directory / "cli-manifest-macos-arm64.json").write_text(json.dumps(metadata), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "executable permissions"):
            release.cli_assets(directory, "0.2.0")

    def test_source_archive_verification_uses_contents_not_compression_bytes(self):
        root = self.repo
        with patch.object(prepare_release, "build_wheels", return_value=self.wheels):
            result = prepare_release.prepare(root, "0.3.1", root / "dist")
        folder = Path(result["output"])
        source = folder / "my-py-tools-v0.3.1.zip"
        with zipfile.ZipFile(source) as archive:
            entries = [(item, archive.read(item.filename)) for item in archive.infolist()]
        with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_STORED) as archive:
            for item, data in entries:
                item.compress_type = zipfile.ZIP_STORED
                archive.writestr(item, data)
        marker = folder / prepare_release.MANIFEST
        manifest = json.loads(marker.read_text(encoding="utf-8"))
        asset = next(a for a in manifest["assets"] if a["name"] == source.name)
        asset.update(size=source.stat().st_size, sha256=prepare_release.digest(source.read_bytes()))
        marker.write_text(json.dumps(manifest), encoding="utf-8")
        with patch.object(release, "REPO", root):
            self.assertEqual(len(release.verify("v0.3.1")), 3)


    def test_direct_entrypoint_ignores_external_scripts_namespace(self):
        with tempfile.TemporaryDirectory() as temporary:
            Path(temporary, "scripts.py").write_text("unrelated = True\n", encoding="utf-8")
            environment = dict(os.environ, PYTHONPATH=temporary)
            result = subprocess.run([sys.executable, str(SCRIPTS / "release.py"), "--help"], env=environment, cwd=temporary, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("prepare", result.stdout)


    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name).resolve()
        (self.repo / "packages/workspace_core").mkdir(parents=True)
        (self.repo / "documents").mkdir()
        (self.repo / "VERSION").write_text("0.2.0\n", encoding="utf-8")
        (self.repo / "pyproject.toml").write_text('[project]\nname = "my-py-document-core"\nversion = "0.2.0"\n', encoding="utf-8")
        (self.repo / "packages/workspace_core/pyproject.toml").write_text('[project]\nname = "my-py-workspace-core"\nversion = "0.1.0"\n', encoding="utf-8")
        (self.repo / "documents/tool.py").write_text("print('ok')\n", encoding="utf-8")
        (self.repo / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
        (self.repo / ".env.example").write_text("TOKEN=\n", encoding="utf-8")
        self.wheels = {
            "my_py_document_core-0.2.0-py3-none-any.whl": fake_wheel("my-py-document-core", "0.2.0"),
            "my_py_workspace_core-0.1.0-py3-none-any.whl": fake_wheel("my-py-workspace-core", "0.1.0"),
        }

    def test_dry_run_builds_without_writing(self) -> None:
        with patch.object(prepare_release, "build_wheels", return_value=self.wheels):
            result = prepare_release.prepare(self.repo, "0.3.0", self.repo / "dist", dry_run=True)
        self.assertEqual(result["tag"], "v0.3.0")
        self.assertEqual((self.repo / "VERSION").read_text(encoding="utf-8"), "0.2.0\n")
        self.assertFalse((self.repo / "dist").exists())

    def test_prepare_and_verify_release_assets(self) -> None:
        with patch.object(prepare_release, "build_wheels", return_value=self.wheels):
            result = prepare_release.prepare(self.repo, "0.3.0", self.repo / "dist")
        self.assertEqual((self.repo / "VERSION").read_text(encoding="utf-8"), "0.3.0\n")
        folder = Path(result["output"])
        manifest = json.loads((folder / prepare_release.MANIFEST).read_text(encoding="utf-8"))
        self.assertEqual(manifest["packages"], {"my-py-document-core": "0.2.0", "my-py-workspace-core": "0.1.0"})
        source = folder / "my-py-tools-v0.3.0.zip"
        with zipfile.ZipFile(source) as archive:
            names = set(archive.namelist())
            self.assertIn("my-py-tools-v0.3.0/.env.example", names)
            self.assertNotIn("my-py-tools-v0.3.0/.env", names)
            self.assertEqual(archive.read("my-py-tools-v0.3.0/VERSION"), b"0.3.0\n")
        with patch.object(release, "REPO", self.repo):
            assets = release.verify("v0.3.0")
        self.assertEqual(len(assets), 3)

    def test_changed_managed_asset_is_rejected(self) -> None:
        with patch.object(prepare_release, "build_wheels", return_value=self.wheels):
            result = prepare_release.prepare(self.repo, None, self.repo / "dist")
        asset = Path(result["output"]) / "my-py-tools-v0.2.0.zip"
        asset.write_bytes(asset.read_bytes() + b"changed")
        with patch.object(prepare_release, "build_wheels", return_value=self.wheels):
            with self.assertRaisesRegex(ValueError, "changed independently"):
                prepare_release.prepare(self.repo, None, self.repo / "dist")


if __name__ == "__main__":
    unittest.main()
