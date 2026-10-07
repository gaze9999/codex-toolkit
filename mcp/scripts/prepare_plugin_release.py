#!/usr/bin/env python3
"""Check plugin source mappings without writes; create release archives only explicitly."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
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


def write_release(root: Path, output: Path, packages: dict) -> None:
    output = output.resolve()
    if output == root.resolve() or output.exists():
        raise ValueError("Use a new, dedicated release output directory")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root, text=True).strip():
        raise ValueError("Release archives require a committed, clean source snapshot")
    output.mkdir(parents=True)
    marketplace = {"name": "codex-toolkit", "interface": {"displayName": "Codex Toolkit"}, "plugins": []}
    release = {"schema_version": 1, "source_revision": revision, "plugins": []}
    combined = {}
    for identifier, (files, provenance) in packages.items():
        name, version = provenance["plugin"], provenance["version"]
        provenance = {**provenance, "source_revision": revision}
        files = {**files, "source-manifest.json": (json.dumps(provenance, ensure_ascii=False, indent=2) + "\n").encode()}
        archive = output / (name + "-" + version + ".zip")
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as stream:
            for path, raw in sorted(files.items()):
                stream.writestr(name + "/" + path, raw)
                combined["plugins/" + name + "/" + path] = raw
        sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_suffix(".zip.sha256").write_text(sha + "  " + archive.name + "\n", encoding="utf-8")
        release["plugins"].append({"name": name, "version": version, "archive": archive.name, "sha256": sha})
        marketplace["plugins"].append({"name": name, "source": {"source": "local", "path": "./plugins/" + name},
                                      "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"}, "category": "Productivity"})
    combined[".agents/plugins/marketplace.json"] = (json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n").encode()
    combined["plugin-release-manifest.json"] = (json.dumps(release, ensure_ascii=False, indent=2) + "\n").encode()
    archive = output / "codex-toolkit-plugins.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as stream:
        for path, raw in sorted(combined.items()):
            stream.writestr(path, raw)
    archive.with_suffix(".zip.sha256").write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n", encoding="utf-8")
    verify_release(root, output, packages)


def verify_release(root: Path, output: Path, packages: dict) -> None:
    """Read back released members, mappings, source identity and archive checksums."""
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    live_packages, _result = prepare(root)
    if any(live_packages.get(identifier) != package for identifier, package in packages.items()):
        raise ValueError("Source changed after release preparation")
    expected_combined, release = {}, {"schema_version": 1, "source_revision": revision, "plugins": []}
    marketplace = {"name": "codex-toolkit", "interface": {"displayName": "Codex Toolkit"}, "plugins": []}
    expected_names = {"codex-toolkit-plugins.zip", "codex-toolkit-plugins.zip.sha256"}
    for files, provenance in packages.values():
        name, version = provenance["plugin"], provenance["version"]
        archive = output / (name + "-" + version + ".zip")
        expected_names.update({archive.name, archive.name + ".sha256"})
        expected = {name + "/" + path: raw for path, raw in files.items()}
        expected[name + "/source-manifest.json"] = (json.dumps({**provenance, "source_revision": revision}, ensure_ascii=False, indent=2) + "\n").encode()
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
    args = parser.parse_args(argv)
    if args.check and args.output:
        parser.error("--check cannot create archives")
    try:
        packages, result = prepare(ROOT, args.plugin)
        if args.output:
            write_release(ROOT, args.output, packages)
            result["status"] = "written"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, UnicodeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
