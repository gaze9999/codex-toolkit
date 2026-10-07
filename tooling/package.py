#!/usr/bin/env python3
"""Plan or atomically assemble explicit Codex Toolkit products; never install or publish."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp/scripts"))
from plugin_catalog import NAME, safe_source, source_files
from prepare_plugin_release import prepare as prepare_plugins, write_release
from prepare_release import normalize_version, zip_bytes


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def products(root: Path, selected: list[str] | None) -> list[dict]:
    data = json.loads(safe_source(root, "tooling/products.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("products"), list):
        raise ValueError("Invalid product catalog")
    rows, seen = [], set()
    for row in data["products"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not NAME.fullmatch(row["id"]) or row["id"] in seen:
            raise ValueError("Invalid or duplicate product ID")
        seen.add(row["id"])
        if row.get("kind") not in {"source", "plugins", "mcp", "native"} or type(row.get("default")) is not bool or not isinstance(row.get("requires"), list):
            raise ValueError("Invalid product kind or prerequisites")
        if row["kind"] == "source":
            if not isinstance(row.get("sources"), list) or not row["sources"]:
                raise ValueError("Source products need explicit source paths")
            for source in row["sources"]:
                safe_source(root, source)
            if row.get("strip_prefix") and (not isinstance(row["strip_prefix"], str) or not row["strip_prefix"].endswith("/")):
                raise ValueError("Invalid source prefix")
        if row["kind"] == "native" and row.get("interface") != "cli":
            raise ValueError("Invalid native interface")
        rows.append(row)
    if selected and (len(selected) != len(set(selected)) or set(selected) - seen):
        raise ValueError("Unknown or duplicate selected product")
    return [row for row in rows if row["id"] in selected] if selected else [row for row in rows if row["default"]]


def source_payload(root: Path, product: dict) -> tuple[dict[str, bytes], dict]:
    root = root.resolve()
    files, provenance, targets = {}, {}, set()
    for source in product["sources"]:
        for path, _relative in source_files(root, source):
            original = path.relative_to(root).as_posix()
            prefix = product.get("strip_prefix", "")
            if not original.startswith(prefix):
                raise ValueError("Source does not match the selected prefix")
            target = original[len(prefix):]
            safe_source(root, target)
            if target.casefold() == "source-manifest.json" or any(target.casefold() == name or target.casefold().startswith(name + "/") or name.startswith(target.casefold() + "/") for name in targets):
                raise ValueError("Duplicate package target")
            targets.add(target.casefold())
            raw = path.read_bytes()
            files[target] = raw
            provenance[target] = {"source": original, "sha256": digest(raw)}
    if not files:
        raise ValueError("Source product is empty")
    license_path = safe_source(root, "LICENSE")
    if license_path.is_file() and "LICENSE" not in files:
        if any(name.casefold() == "license" or name.casefold().startswith("license/") for name in files):
            raise ValueError("License target collision")
        raw = license_path.read_bytes()
        files["LICENSE"] = raw
        provenance["LICENSE"] = {"source": "LICENSE", "sha256": digest(raw)}
    return files, provenance


def plan(root: Path, selected: list[str] | None = None) -> dict:
    rows = []
    for product in products(root, selected):
        row = {key: product[key] for key in ("id", "kind", "description", "requires")}
        if product["kind"] == "source":
            files, _provenance = source_payload(root, product)
            row.update(files=len(files), source_bytes=sum(map(len, files.values())))
        elif product["kind"] == "plugins":
            packages, result = prepare_plugins(root)
            row.update(plugins=len(packages), blocked=result["blocked"], files=sum(len(value[0]) for value in packages.values()))
        else:
            row["status"] = "requires_selected_builder"
        rows.append(row)
    return {"schema_version": 1, "status": "planned", "products": rows}


def source_identity(root: Path, release: bool) -> dict:
    top = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True, timeout=30).strip()
    if Path(top).resolve() != root.resolve():
        raise ValueError("Build from the complete source checkout, not an installed mirror or subdirectory")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=30).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root, text=True, timeout=30).strip()
    if release and dirty:
        raise ValueError("Release builds require a reviewed, committed and clean source tree")
    return {"base_revision": revision, "source_state": "committed" if release else "working-tree"}


def build(root: Path, selected: list[str] | None, version: str, output: Path, *, release: bool = False, python: Path | None = None) -> dict:
    tag = normalize_version(version)
    rows = products(root, selected)
    output = output.absolute()
    if output.exists() or output.resolve() == root.resolve() or any(path.is_symlink() or getattr(path, "is_junction", lambda: False)() for path in (output, *output.parents)):
        raise ValueError("Use a new, unlinked output directory; existing files are preserved")
    identity = source_identity(root, release)
    before = plan(root, selected)
    snapshots = {row["id"]: source_payload(root, row) for row in rows if row["kind"] == "source"}
    if release:
        tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=root, timeout=30).decode("utf-8").split("\0"))
        if any(item["source"] not in tracked for _files, provenance in snapshots.values() for item in provenance.values()):
            raise ValueError("Release source includes ignored or uncommitted files")
    if any(row["kind"] == "native" for row in rows) and python is None:
        raise ValueError("Native builds require an explicitly selected pinned standalone --python")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="setup-build-", dir=output.parent) as temporary:
        staged = Path(temporary) / "payload"
        staged.mkdir()
        for row in rows:
            kind, identifier = row["kind"], row["id"]
            if kind == "plugins":
                packages, _result = prepare_plugins(root)
                write_release(root, staged / identifier, packages, development=not release)
            elif kind == "source":
                files, provenance = snapshots[identifier]
                if "source-manifest.json" in files:
                    raise ValueError("Source manifest target is reserved")
                files = {**files, "source-manifest.json": encoded({"schema_version": 1, "product": identifier, "tag": tag, **identity, "files": provenance, "requires": row["requires"]})}
                raw = zip_bytes(files, (1980, 1, 1, 0, 0, 0))
                folder = staged / identifier
                folder.mkdir()
                name = "codex-toolkit-" + identifier + "-" + tag + ".zip"
                (folder / name).write_bytes(raw)
                (folder / (name + ".sha256")).write_text(digest(raw) + "  " + name + "\n", encoding="utf-8")
            elif kind == "mcp":
                from prepare_mcp_release import prepare, verify
                prepare(root, tag, staged / identifier)
                verify(root, tag, staged / identifier)
            else:
                import prepare_cli_release as native
                if root.resolve() != ROOT.resolve():
                    raise ValueError("Native builds require the current checkout")
                native.prepare(python.resolve(), tag, staged / identifier)
        if identity != source_identity(root, release) or before != plan(root, selected) or any(snapshots[row["id"]] != source_payload(root, row) for row in rows if row["kind"] == "source"):
            raise ValueError("Source changed during packaging")
        assets = [{"path": path.relative_to(staged).as_posix(), "size": path.stat().st_size, "sha256": digest(path.read_bytes())} for path in sorted(staged.rglob("*")) if path.is_file()]
        result = {"schema_version": 1, "producer": "codex-toolkit.package.v1", "tag": tag, **identity, "products": before["products"], "assets": assets}
        (staged / "package-manifest.json").write_bytes(encoded(result))
        verify_output(staged)
        staged.rename(output)
    return {"status": "built", "output": str(output), "products": [row["id"] for row in rows], "assets": len(assets), **identity}


def verify_output(output: Path) -> dict:
    manifest = json.loads((output / "package-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("producer") != "codex-toolkit.package.v1" or not isinstance(manifest.get("assets"), list):
        raise ValueError("Invalid package manifest")
    names = set()
    for row in manifest["assets"]:
        path = safe_source(output, row["path"])
        if row["path"].casefold() in names or row["path"] == "package-manifest.json":
            raise ValueError("Duplicate or reserved package asset")
        names.add(row["path"].casefold())
        raw = path.read_bytes()
        if len(raw) != row["size"] or digest(raw) != row["sha256"]:
            raise ValueError("Package asset checksum mismatch: " + row["path"])
    actual = {path.relative_to(output).as_posix().casefold() for path in output.rglob("*") if path.is_file()}
    if actual != names | {"package-manifest.json"}:
        raise ValueError("Unexpected or missing package assets")
    return {"status": "verified", "assets": len(names), "source_state": manifest["source_state"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "build", "verify"))
    parser.add_argument("--product", action="append", help="Repeat for explicitly selected product IDs; default builds source products")
    parser.add_argument("--version", help="Package tag; never changes Skill or project versions")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--release", action="store_true", help="Require clean committed source; does not publish")
    parser.add_argument("--python", type=Path, help="Pinned standalone interpreter for selected native builds")
    args = parser.parse_args(argv)
    try:
        if args.action == "plan":
            result = plan(ROOT, args.product)
        elif args.action == "verify":
            if args.output is None:
                parser.error("verify requires --output")
            result = verify_output(args.output)
        else:
            if args.version is None or args.output is None:
                parser.error("build requires --version and a new --output")
            result = build(ROOT, args.product, args.version, args.output, release=args.release, python=args.python)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
