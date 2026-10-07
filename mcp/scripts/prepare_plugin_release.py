#!/usr/bin/env python3
"""Check plugin source mappings without writes; create release archives only explicitly."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from plugin_catalog import load_catalog, payload

ROOT = Path(__file__).resolve().parents[2]


def prepare(root: Path, selected: str | None = None) -> tuple[dict, dict]:
    bundles = load_catalog(root)
    if selected:
        bundles = [bundle for bundle in bundles if bundle["id"] == selected]
        if not bundles:
            raise ValueError("Unknown plugin ID")
    packages, blocked = {}, []
    for bundle in bundles:
        files, manifest = payload(root, bundle)
        if bundle["status"] == "blocked":
            if selected:
                raise ValueError(bundle["blocked_reason"])
            blocked.append({"id": bundle["id"], "reason": bundle["blocked_reason"]})
            continue
        packages[bundle["id"]] = (files, manifest)
    return packages, {"status": "checked", "plugins": [{"id": name, "files": len(files), "version": manifest["version"]} for name, (files, manifest) in packages.items()], "blocked": blocked}


def snapshot_identity(root: Path, development: bool = False) -> dict:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=30).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root, text=True, timeout=30).strip()
    if not development and dirty:
        raise ValueError("Release archives require a committed, clean source snapshot")
    if not development:
        tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=root, timeout=30).decode("utf-8").split("\0"))
        packages, _result = prepare(root)
        if any(row["source"] not in tracked for _files, manifest in packages.values() for row in manifest["files"].values()):
            raise ValueError("Release source includes ignored or uncommitted files")
    return {"source_revision": revision, "source_state": "working-tree" if development else "committed"}


def write_zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED) as stream:
        for name, raw in sorted(files.items()):
            item = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            stream.writestr(item, raw)


def write_release(root: Path, output: Path, packages: dict, *, development: bool = False) -> None:
    if any(path.is_symlink() or getattr(path, "is_junction", lambda: False)() for path in (output, *output.absolute().parents)):
        raise ValueError("Output must not use linked directories")
    output = output.resolve()
    if output == root.resolve() or output.exists():
        raise ValueError("Use a new, dedicated release output directory")
    identity = snapshot_identity(root, development)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="plugin-build-", dir=output.parent) as temporary:
        staged = Path(temporary) / "payload"
        staged.mkdir()
        _write_release(root, staged, packages, identity)
        verify_release(root, staged, packages, development=development)
        staged.rename(output)


def _write_release(root: Path, output: Path, packages: dict, identity: dict) -> None:
    marketplace = {"name": "codex-toolkit", "interface": {"displayName": "Codex Toolkit"}, "plugins": []}
    release = {"schema_version": 1, **identity, "plugins": []}
    combined = {}
    for identifier, (files, provenance) in packages.items():
        name, version = provenance["plugin"], provenance["version"]
        provenance = {**provenance, **identity}
        files = {**files, "source-manifest.json": (json.dumps(provenance, ensure_ascii=False, indent=2) + "\n").encode()}
        archive = output / (name + "-" + version + ".zip")
        write_zip(archive, {name + "/" + path: raw for path, raw in files.items()})
        combined.update({"plugins/" + name + "/" + path: raw for path, raw in files.items()})
        sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_suffix(".zip.sha256").write_text(sha + "  " + archive.name + "\n", encoding="utf-8")
        release["plugins"].append({"name": name, "version": version, "archive": archive.name, "sha256": sha})
        marketplace["plugins"].append({"name": name, "source": {"source": "local", "path": "./plugins/" + name},
                                      "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"}, "category": "Productivity"})
    combined[".agents/plugins/marketplace.json"] = (json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n").encode()
    combined["plugin-release-manifest.json"] = (json.dumps(release, ensure_ascii=False, indent=2) + "\n").encode()
    archive = output / "codex-toolkit-plugins.zip"
    write_zip(archive, combined)
    archive.with_suffix(".zip.sha256").write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n", encoding="utf-8")


def verify_release(root: Path, output: Path, packages: dict, *, development: bool = False) -> None:
    """Read back released members, mappings, source identity and archive checksums."""
    identity = snapshot_identity(root, development)
    live_packages, _result = prepare(root)
    if any(live_packages.get(identifier) != package for identifier, package in packages.items()):
        raise ValueError("Source changed after release preparation")
    expected_combined, release = {}, {"schema_version": 1, **identity, "plugins": []}
    marketplace = {"name": "codex-toolkit", "interface": {"displayName": "Codex Toolkit"}, "plugins": []}
    expected_names = {"codex-toolkit-plugins.zip", "codex-toolkit-plugins.zip.sha256"}
    for files, provenance in packages.values():
        name, version = provenance["plugin"], provenance["version"]
        archive = output / (name + "-" + version + ".zip")
        expected_names.update({archive.name, archive.name + ".sha256"})
        expected = {name + "/" + path: raw for path, raw in files.items()}
        expected[name + "/source-manifest.json"] = (json.dumps({**provenance, **identity}, ensure_ascii=False, indent=2) + "\n").encode()
        verify_members(archive, expected)
        expected_combined.update({"plugins/" + path: raw for path, raw in expected.items()})
        release["plugins"].append({"name": name, "version": version, "archive": archive.name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()})
        marketplace["plugins"].append({"name": name, "source": {"source": "local", "path": "./plugins/" + name},
                                      "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"}, "category": "Productivity"})
    expected_combined[".agents/plugins/marketplace.json"] = (json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n").encode()
    expected_combined["plugin-release-manifest.json"] = (json.dumps(release, ensure_ascii=False, indent=2) + "\n").encode()
    verify_members(output / "codex-toolkit-plugins.zip", expected_combined)
    if {path.name for path in output.iterdir()} != expected_names:
        raise ValueError("Unexpected release output members")


def verify_members(archive: Path, expected: dict[str, bytes]) -> None:
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
    if archive.with_suffix(".zip.sha256").read_text(encoding="utf-8") != checksum:
        raise ValueError("Archive checksum mismatch")
    with zipfile.ZipFile(archive) as stream:
        names = stream.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("Archive members differ from source mappings")
        for name, raw in expected.items():
            if stream.read(name) != raw:
                raise ValueError("Archive differs from current source: " + name)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin", help="One catalog ID; default checks all bundles")
    parser.add_argument("--check", action="store_true", help="Validate mappings and references in memory")
    parser.add_argument("--output", type=Path, help="Create release ZIPs from a clean committed source")
    parser.add_argument("--development", action="store_true", help="Label archives as working-tree previews; never publish them")
    args = parser.parse_args(argv)
    if args.check and args.output:
        parser.error("--check cannot create archives")
    try:
        packages, result = prepare(ROOT, args.plugin)
        if args.output:
            write_release(ROOT, args.output, packages, development=args.development)
            result["status"] = "written"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, UnicodeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
