#!/usr/bin/env python3
"""Prepare a Skill release, then publish a reviewed commit through GitHub CLI."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import prepare_release
import prepare_mcp_release


REPO = Path(__file__).resolve().parents[2]


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(args, cwd=REPO, text=True, encoding="utf-8",
                            capture_output=capture, check=False)
    if result.returncode:
        raise ValueError(f"Command failed ({result.returncode}): {' '.join(args)}")
    return result.stdout.strip() if capture else ""


def verify(tag: str, output_root: Path | None = None, *, repo: Path | None = None) -> list[Path]:
    repo = repo or REPO
    tag = prepare_release.normalize_version(tag)
    folder = (output_root or repo / "dist").expanduser().resolve() / tag
    manifest = json.loads((folder / prepare_release.MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("producer") != prepare_release.PRODUCER or manifest.get("tag") != tag:
        raise ValueError("Release manifest has the wrong producer or tag")
    skills = [prepare_release.read_skill(path) for path in sorted((repo / "skills").glob("*/SKILL.md"))]
    versions = {skill["path"].parent.name: prepare_release.skill_version(skill["metadata"]["version"] or "") for skill in skills}
    if not skills or manifest.get("skill_versions") != versions:
        raise ValueError("Skill metadata versions do not match the release manifest")
    files = {name: data for name, (_, data) in prepare_release.snapshot(repo, skills).items()}
    names = [skill["path"].parent.name for skill in skills]
    expected = {f"all-skills-{tag}.zip"}
    assets = manifest.get("assets")
    if (manifest.get("skills") != names or manifest.get("skill_count") != len(names)
            or manifest.get("source_files") != len(files) or not isinstance(assets, list)
            or {asset.get("name") for asset in assets if isinstance(asset, dict)} != expected
            or len(assets) != len(expected)):
        raise ValueError("Release manifest does not match the current Skill set")
    if {path.name for path in folder.iterdir()} != expected | {prepare_release.MANIFEST}:
        raise ValueError("Release folder contains missing or unexpected files")
    for asset in assets:
        path = folder / asset["name"]
        data = path.read_bytes()
        if len(data) != asset.get("size") or prepare_release.digest(data) != asset.get("sha256"):
            raise ValueError(f"Release asset changed: {path.name}")
        expected_files = files
        with zipfile.ZipFile(path) as archive:
            if (archive.testzip() is not None or set(archive.namelist()) != set(expected_files)
                    or any(archive.read(name) != content for name, content in expected_files.items())):
                raise ValueError(f"Release ZIP content does not match committed source: {path.name}")
    return [folder / name for name in sorted(expected)]


def publish(tag: str, asset_root: Path | None = None) -> None:
    tag = prepare_release.normalize_version(tag)
    if run("git", "status", "--porcelain=v1", "-uall", capture=True):
        raise ValueError("Commit and review all source changes before publishing")
    branch = run("git", "branch", "--show-current", capture=True)
    if not branch:
        raise ValueError("A local branch is required")
    upstream = run("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", capture=True)
    if upstream != f"origin/{branch}":
        raise ValueError(f"Branch must track origin/{branch}")
    skill_root = (asset_root or REPO / "dist").expanduser().resolve()
    mcp_assets = prepare_mcp_release.verify(REPO, tag, skill_root / "mcp")
    assets = verify(tag, skill_root) + mcp_assets + [skill_root / "mcp" / tag / prepare_mcp_release.MANIFEST]
    run(sys.executable, str(REPO / "mcp/scripts" / "audit_skills.py"), "--release-tag", tag)
    if run("git", "tag", "--list", tag, capture=True):
        raise ValueError(f"Local tag already exists: {tag}")
    if run("git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}", capture=True):
        raise ValueError(f"Remote tag already exists: {tag}")
    run("gh", "auth", "status", capture=True)
    existing = subprocess.run(["gh", "release", "view", tag, "--json", "tagName"], cwd=REPO,
                              capture_output=True, text=True, encoding="utf-8")
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
    run("gh", "release", "create", tag, *(str(path) for path in assets),
        "--target", head, "--title", tag, "--generate-notes")
    remote_release = json.loads(run("gh", "release", "view", tag, "--json", "tagName,assets", capture=True))
    remote_assets = remote_release.get("assets", [])
    if (remote_release.get("tagName") != tag
            or {asset.get("name"): asset.get("size") for asset in remote_assets}
            != {path.name: path.stat().st_size for path in assets}):
        raise ValueError("GitHub Release assets do not match the local assets; inspect the release")
    print(f"Published {tag}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare", help="Update versions, build ZIPs, and audit Skills")
    prepare.add_argument("--version", help="Version to use; default increments patch")
    prepare.add_argument("--dry-run", action="store_true")
    prepare.add_argument("--asset-root", type=Path, help="Asset root; default: <repo>/dist")
    publish_parser = sub.add_parser("publish", help="Push a reviewed commit and create a GitHub Release")
    publish_parser.add_argument("tag", help="Prepared release tag, e.g. v0.5.0")
    publish_parser.add_argument("--asset-root", type=Path, help="Prepared asset root; default: <repo>/dist")
    args = parser.parse_args()
    try:
        if args.action == "publish":
            publish(args.tag, args.asset_root)
        else:
            asset_root = (args.asset_root or REPO / "dist").expanduser().resolve()
            result = prepare_release.prepare(REPO, args.version, asset_root, args.dry_run)
            mcp_result = prepare_mcp_release.prepare(REPO, result["tag"], asset_root / "mcp", args.dry_run)
            if not args.dry_run:
                verify(result["tag"], asset_root)
                prepare_mcp_release.verify(REPO, result["tag"], asset_root / "mcp")
                run(sys.executable, str(REPO / "mcp/scripts" / "audit_skills.py"),
                    "--release-tag", result["tag"])
            print(f"{'PREVIEW' if args.dry_run else 'READY'} {result['tag']}: "
                  f"{result['skills']} Skills, {result['zip_count']} Skill ZIPs, {mcp_result['assets']} wheels, {mcp_result.get('extra_assets', 0)} installer/notice ZIPs")
            if not args.dry_run:
                suffix = f" --asset-root {asset_root}" if args.asset_root else ""
                print(f"Review changes, commit them, then run: python mcp/scripts/release.py publish {result['tag']}{suffix}")
    except (OSError, ValueError, AssertionError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
