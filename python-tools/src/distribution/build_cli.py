"""Build a self-contained Windows/macOS CLI ZIP on its native architecture."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile

from shared.tool_catalog import TOOLS
from shared.version import repository_version


ROOT = Path(__file__).resolve().parents[2]


def run(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def prepare_resources() -> Path:
    import tiktoken

    resources = ROOT / ".build-inputs/cli"
    resources.mkdir(parents=True, exist_ok=True)
    (resources / "catalog.json").write_text(
        json.dumps([tool.payload() for tool in TOOLS], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    previous = os.environ.get("TIKTOKEN_CACHE_DIR")
    os.environ["TIKTOKEN_CACHE_DIR"] = str(resources / "tiktoken")
    try:
        for encoding in ("o200k_base", "cl100k_base"):
            tiktoken.get_encoding(encoding)
    finally:
        if previous is None:
            os.environ.pop("TIKTOKEN_CACHE_DIR", None)
        else:
            os.environ["TIKTOKEN_CACHE_DIR"] = previous
    return resources


def archive_application(app: Path, target: Path) -> None:
    if sys.platform == "darwin":
        run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app), str(target)])
        return
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(app.rglob("*")):
            if file.is_file():
                archive.write(file, Path(app.name) / file.relative_to(app))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, help="Output root; existing builds are never overwritten")
    args = parser.parse_args(argv)
    if sys.platform not in {"win32", "darwin"}:
        parser.error("Build Windows on Windows or macOS on macOS")
    system = "windows" if sys.platform == "win32" else "macos"
    architecture = {"amd64": "x64", "aarch64": "arm64", "x86_64": "x64"}.get(platform.machine().lower(), platform.machine().lower())
    if architecture not in {"arm64", "x64"}:
        parser.error("Supported architectures: arm64, x64")
    version = repository_version(ROOT)
    label = f"my-py-tools-{version}-cli-{system}-{architecture}"
    output = (args.output_root or ROOT / "dist/cli").expanduser().resolve()
    destination = output / label
    if destination.exists():
        parser.error(f"Output already exists: {destination}")
    prepare_resources()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cli-build-", dir=output) as temporary:
        staging = Path(temporary)
        run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", str(staging / "dist"), "--workpath", str(staging / "work"), str(ROOT / "src/distribution/cli.spec")])
        destination.mkdir()
        shutil.move(str(staging / "dist/MyPyToolsCLI"), str(destination / "MyPyToolsCLI"))
    if system == "windows":
        shutil.copy2(ROOT / "src/distribution/launch-cli.cmd", destination / "MyPyToolsCLI/launch-cli.cmd")
        shutil.copy2(ROOT / "launch-cli.ps1", destination / "MyPyToolsCLI/launch-cli.ps1")
    archive = destination / f"{label}.zip"
    archive_application(destination / "MyPyToolsCLI", archive)
    with archive.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest = {
        "product": "cli", "version": version, "os": system, "architecture": architecture,
        "python": platform.python_version(), "signed": False,
        "dependencies": {name: importlib.metadata.version(name) for name in ("pyinstaller", "pypdf", "pdfplumber", "openpyxl", "python-docx", "python-pptx", "tiktoken")},
        "tools": [tool.module for tool in TOOLS], "source_only_tools": [tool.module for tool in TOOLS if tool.payload()["source_only"]],
        "entrypoints": {"cli": "MyPyToolsCLI/launch-cli" + (".exe" if system == "windows" else "")},
        "modes": ["terminal"],
        "asset": archive.name, "size": archive.stat().st_size, "sha256": checksum,
    }
    if system == "windows":
        manifest["entrypoints"]["cmd"] = "MyPyToolsCLI/launch-cli.cmd"
        manifest["entrypoints"]["ps1"] = "MyPyToolsCLI/launch-cli.ps1"
    (destination / f"cli-manifest-{system}-{architecture}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"READY {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
