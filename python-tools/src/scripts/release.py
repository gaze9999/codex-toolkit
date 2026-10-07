#!/usr/bin/env python3
"""Validate, prepare, and explicitly publish a my-py-tools GitHub Release."""

from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

if __package__:
    from scripts import prepare_release
else:
    import prepare_release


REPO = Path(__file__).resolve().parents[2]


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(args, cwd=REPO, text=True, encoding="utf-8", capture_output=capture, check=False)
    if result.returncode:
        detail = (result.stderr if capture else "").strip()
        raise ValueError(f"Command failed ({result.returncode}): {' '.join(args)}{': ' + detail if detail else ''}")
    return result.stdout.strip() if capture else ""


def validate_source() -> None:
    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v")
    roots = ("src", "packages", "tests")
    errors = []
    for root in roots:
        for directory, names, files in os.walk(REPO / root):
            names[:] = [name for name in names if name not in {"__pycache__", "node_modules", "resources", "vendor"} and not name.startswith(".")]
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = Path(directory, name)
                try:
                    ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
                except (OSError, SyntaxError, UnicodeError) as exc:
                    errors.append(f"{path.relative_to(REPO)}: {exc}")
    if errors:
        raise ValueError("Python syntax validation failed: " + "; ".join(errors))


def cli_assets(directory: Path, version: str) -> tuple[Path, Path, dict]:
    directory = directory.expanduser().resolve()
    markers = list(directory.glob("cli-manifest-*.json"))
    if len(markers) != 1:
        raise ValueError("Exactly one CLI manifest is required")
    marker = markers[0]
    metadata = json.loads(marker.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or metadata.get("product") != "cli":
        raise ValueError("Invalid CLI manifest")
    system, architecture = metadata.get("os"), metadata.get("architecture")
    if system not in {"windows", "macos"} or architecture not in {"x64", "arm64"}:
        raise ValueError("Unsupported CLI platform")
    if marker.name != f"cli-manifest-{system}-{architecture}.json":
        raise ValueError("CLI manifest filename does not match its platform")
    name = metadata.get("asset")
    if not isinstance(name, str) or name != f"my-py-tools-{version}-cli-{system}-{architecture}.zip":
        raise ValueError("Invalid CLI asset name or version")
    archive = directory / name
    import hashlib

    with archive.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    if metadata.get("version") != version or metadata.get("sha256") != checksum or metadata.get("size") != archive.stat().st_size:
        raise ValueError("CLI version, size or SHA-256 mismatch")
    executable = "MyPyToolsCLI/launch-cli" + (".exe" if system == "windows" else "")
    with zipfile.ZipFile(archive) as zipped:
        names = set(zipped.namelist())
        if zipped.testzip() is not None or any(name.startswith(("/", "\\")) or ".." in name.replace("\\", "/").split("/") for name in names):
            raise ValueError("CLI ZIP has invalid CRC or unsafe paths")
        if executable not in names or "MyPyToolsCLI/_internal/shared/resources/catalog.json" not in names:
            raise ValueError("CLI ZIP is missing its executable or tool catalog")
        if metadata.get("modes") != ["terminal"]:
            raise ValueError("CLI ZIP must support terminal mode only")
        entrypoints = {"cli": executable}
        if system == "windows":
            entrypoints["cmd"] = "MyPyToolsCLI/launch-cli.cmd"
            entrypoints["ps1"] = "MyPyToolsCLI/launch-cli.ps1"
            if not set(entrypoints.values()).issubset(names):
                raise ValueError("Windows CLI ZIP must include terminal CMD/PS1 launchers")
        if metadata.get("entrypoints") != entrypoints:
            raise ValueError("CLI entry point does not match its executable")
        if any("WebView2" in name.split("/") or "/gui/" in name or name.endswith(("/launch-gui.exe", "/launch-web.cmd", "/launch-web.ps1")) for name in names):
            raise ValueError("CLI ZIP must not contain a GUI executable or WebView2")
        if system == "macos" and not ((zipped.getinfo(executable).external_attr >> 16) & 0o111):
            raise ValueError("macOS CLI executable must preserve executable permissions")
    return archive, marker, metadata


def prepare_cli(args) -> tuple[Path, Path, dict]:
    version = prepare_release.normalize_version((REPO / "VERSION").read_text(encoding="utf-8"))
    if prepare_release.normalize_version(args.tag) != version:
        raise ValueError("VERSION must match the CLI release tag")
    if args.cli_assets:
        return cli_assets(args.cli_assets, version)
    import platform
    from distribution.build_cli import main as build_cli

    system = "windows" if sys.platform == "win32" else "macos"
    architecture = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64"}.get(platform.machine().lower(), platform.machine().lower())
    output = (args.asset_root or REPO / "dist/cli").resolve()
    if build_cli(["--output-root", str(output)]):
        raise ValueError("CLI build failed")
    return cli_assets(output / f"my-py-tools-{version}-cli-{system}-{architecture}", version)


def verify(tag: str, output_root: Path | None = None) -> list[Path]:
    version = prepare_release.normalize_version(tag)
    tag = "v" + version
    if prepare_release.normalize_version((REPO / "VERSION").read_text(encoding="utf-8")) != version:
        raise ValueError("VERSION does not match the release tag")
    folder = (output_root or REPO / "dist").expanduser().resolve() / tag
    manifest = json.loads((folder / prepare_release.MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("producer") != prepare_release.PRODUCER or manifest.get("tag") != tag or manifest.get("repository_version") != version:
        raise ValueError("Release manifest has the wrong producer or version")
    if manifest.get("packages") != prepare_release.project_versions(REPO):
        raise ValueError("Release package versions do not match pyproject.toml")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("Release manifest has no assets")
    expected_names = {item.get("name") for item in assets if isinstance(item, dict)}
    if len(expected_names) != len(assets) or {path.name for path in folder.iterdir()} != expected_names | {prepare_release.MANIFEST}:
        raise ValueError("Release folder contains missing or unexpected files")
    source_files = prepare_release.source_snapshot(REPO, version)
    source_name = f"my-py-tools-{tag}.zip"
    paths = []
    for item in assets:
        if not isinstance(item.get("name"), str) or Path(item["name"]).name != item["name"]:
            raise ValueError("Invalid release asset name")
        path = folder / item["name"]
        data = path.read_bytes()
        if len(data) != item.get("size") or prepare_release.digest(data) != item.get("sha256"):
            raise ValueError(f"Release asset changed: {path.name}")
        if path.name == source_name:
            expected_files = {f"my-py-tools-{tag}/{name}": content for name, (_path, content) in source_files.items()}
            with zipfile.ZipFile(path) as archive:
                if (archive.testzip() is not None or len(archive.namelist()) != len(expected_files)
                        or set(archive.namelist()) != set(expected_files)
                        or any(((item.external_attr >> 16) & 0o170000) not in {0, 0o100000} for item in archive.infolist())
                        or any(archive.read(name) != content for name, content in expected_files.items())):
                    raise ValueError("Source archive does not match the current repository")
        elif path.suffix == ".whl":
            metadata = prepare_release.wheel_metadata(data)
            expected = manifest["packages"].get(metadata["name"])
            if metadata["version"] != expected:
                raise ValueError(f"Wheel metadata does not match pyproject.toml: {path.name}")
        else:
            raise ValueError(f"Unsupported release asset: {path.name}")
        paths.append(path)
    if manifest.get("source_files") != len(source_files) or source_name not in expected_names:
        raise ValueError("Release source manifest does not match the repository")
    return sorted(paths)


def publish(tag: str, output_root: Path | None = None) -> None:
    version = prepare_release.normalize_version(tag)
    tag = "v" + version
    if run("git", "status", "--porcelain=v1", "-uall", capture=True):
        raise ValueError("Commit and review all source changes before publishing")
    branch = run("git", "branch", "--show-current", capture=True)
    if not branch:
        raise ValueError("A local branch is required")
    upstream = run("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", capture=True)
    if upstream != f"origin/{branch}":
        raise ValueError(f"Branch must track origin/{branch}")
    validate_source()
    assets = verify(tag, output_root)
    if run("git", "tag", "--list", tag, capture=True):
        raise ValueError(f"Local tag already exists: {tag}")
    if run("git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}", capture=True):
        raise ValueError(f"Remote tag already exists: {tag}")
    run("gh", "auth", "status", capture=True)
    existing = subprocess.run(["gh", "release", "view", tag, "--json", "tagName"], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    if existing.returncode == 0:
        raise ValueError(f"GitHub Release already exists: {tag}")
    head = run("git", "rev-parse", "HEAD", capture=True)
    print(f"Ready to push {branch} ({head[:12]}) and publish {tag} with {len(assets)} assets")
    if input("Type the tag to confirm: ").strip() != tag:
        print("Cancelled")
        return
    run("git", "push", "origin", branch)
    remote = run("git", "ls-remote", "origin", f"refs/heads/{branch}", capture=True)
    if not remote or remote.split()[0] != head:
        raise ValueError("Remote branch does not match the reviewed commit")
    run("gh", "release", "create", tag, *(str(path) for path in assets), "--target", head, "--title", tag, "--generate-notes")
    remote_release = json.loads(run("gh", "release", "view", tag, "--json", "tagName,assets", capture=True))
    remote_assets = remote_release.get("assets", [])
    if remote_release.get("tagName") != tag or {item.get("name"): item.get("size") for item in remote_assets} != {path.name: path.stat().st_size for path in assets}:
        raise ValueError("GitHub Release assets do not match the local release")
    print(f"Published {tag}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    prepare = subparsers.add_parser("prepare", help="Run tests, build source ZIP and independent wheels")
    prepare.add_argument("--version", help="Repository version; package versions remain independent")
    prepare.add_argument("--dry-run", action="store_true")
    prepare.add_argument("--asset-root", type=Path, help="Asset root; default: <repo>/dist")
    publish_parser = subparsers.add_parser("publish", help="Push a reviewed commit and create a GitHub Release")
    publish_parser.add_argument("tag", help="Prepared release tag, e.g. v0.2.0")
    publish_parser.add_argument("--asset-root", type=Path, help="Prepared asset root; default: <repo>/dist")
    cli_parser = subparsers.add_parser("cli", help="Build independent native CLI assets for Release CI")
    cli_parser.add_argument("tag")
    cli_parser.add_argument("--asset-root", type=Path)
    cli_parser.add_argument("--cli-assets", type=Path, help="Verify an existing native CLI build")
    args = parser.parse_args()
    try:
        if args.action == "publish":
            publish(args.tag, args.asset_root)
        elif args.action == "cli":
            validate_source()
            archive, marker, _metadata = prepare_cli(args)
            print(f"READY {archive}\nMANIFEST {marker}")
        else:
            validate_source()
            output_root = args.asset_root or REPO / "dist"
            result = prepare_release.prepare(REPO, args.version, output_root, args.dry_run)
            if not args.dry_run:
                verify(str(result["tag"]), output_root)
            print(f"{'PREVIEW' if args.dry_run else 'READY'} {result['tag']}: {result['assets']} assets")
            if not args.dry_run:
                suffix = f" --asset-root {output_root}" if args.asset_root else ""
                print(f"Review changes, commit them, then run: python launch-cli.py scripts.release publish {result['tag']}{suffix}")
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
