#!/usr/bin/env python3
"""Check or install Codex global instructions, model profile and Markdown references."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS = ("AGENTS.md", "subagents.config.toml")


def is_link(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except (FileNotFoundError, NotADirectoryError):
        return False
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def reference_paths(directory: Path):
    if is_link(directory):
        raise ValueError(f"reference is a link; review it manually: {directory}")
    if not directory.exists():
        return
    if not directory.is_dir():
        raise ValueError(f"references must be a directory: {directory}")
    for path in sorted(directory.iterdir()):
        if is_link(path):
            raise ValueError(f"reference is a link; review it manually: {path}")
        if path.is_dir():
            yield from reference_paths(path)
        elif path.is_file() and path.suffix.lower() == ".md":
            yield path


def check_target(path: Path, home: Path) -> None:
    for parent in (path.parent, *path.parent.parents):
        if is_link(parent):
            raise ValueError(f"target parent is a link; review it manually: {parent}")
        if parent.exists() and not parent.is_dir():
            raise ValueError(f"target parent is not a directory: {parent}")
        if parent == home:
            break
    if is_link(path):
        raise ValueError(f"target is a link; review it manually: {path}")
    if path.exists() and not path.is_file():
        raise ValueError(f"target is not a file: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, help="Explicit personal agent source directory; defaults to neutral repository examples.")
    parser.add_argument("--codex-home", type=Path, help="Override CODEX_HOME or ~/.codex.")
    parser.add_argument("--install", action="store_true", help="Install missing files and optional references/*.md, preserving relative paths.")
    parser.add_argument("--replace", action="store_true", help="Back up and replace different files; requires --install.")
    args = parser.parse_args()
    if args.replace and not args.install:
        parser.error("--replace requires --install")

    repo = Path(__file__).resolve().parents[2]
    home = (args.codex_home or Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")).expanduser().resolve()
    if home == Path(home.anchor) or home == repo or repo in home.parents:
        parser.error("Codex home must not be a filesystem root or inside this repository")

    source_root = (args.source_root or repo / "agents").expanduser().resolve()
    if source_root == Path(source_root.anchor) or source_root == home or source_root.is_relative_to(home):
        parser.error("Use an independent agent source directory outside Codex home")
    if source_root.is_symlink():
        parser.error("Agent source must not be a symlink")

    pending = []
    conflicts = []
    try:
        sources = [source_root / name for name in ARTIFACTS]
        sources.extend(reference_paths(source_root / "references"))
        for source in sources:
            target = home / source.relative_to(source_root)
            if is_link(source) or not source.is_file():
                raise ValueError(f"source missing or linked: {source}")
            check_target(target, home)
            content = source.read_bytes()
            if target.is_file() and target.read_bytes() == content:
                print(f"CURRENT {target}")
                continue
            print(f"{'DIFFERENT' if target.exists() else 'MISSING'} {target}")
            pending.append((target, content))
            if target.exists():
                conflicts.append(target)
    except ValueError as error:
        parser.error(str(error))

    if not pending:
        return 0
    if not args.install:
        return 1
    if conflicts and not args.replace:
        print("Review differing files or use --install --replace; no files were changed")
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_root = home / "backups" / "codex-setup" / stamp
    try:
        for target in conflicts:
            check_target(backup_root / target.relative_to(home), home)
    except ValueError as error:
        parser.error(str(error))
    home.mkdir(parents=True, exist_ok=True)
    for target, content in pending:
        if target.exists():
            backup = backup_root / target.relative_to(home)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            print(f"BACKUP {backup}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.name + ".", suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            file.write(content)
        try:
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"INSTALLED {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
