#!/usr/bin/env python3
"""Check or install portable Codex global instructions and subagent model profile."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS = ("AGENTS.md", "subagents.config.toml")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, help="Explicit personal agent source directory; defaults to neutral repository examples.")
    parser.add_argument("--codex-home", type=Path, help="Override CODEX_HOME or ~/.codex.")
    parser.add_argument("--install", action="store_true", help="Install missing or identical files.")
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
    for name in ARTIFACTS:
        source, target = source_root / name, home / name
        if not source.is_file():
            parser.error(f"source missing: {source}")
        if target.is_symlink():
            parser.error(f"target is a symlink; review it manually: {target}")
        if target.exists() and not target.is_file():
            parser.error(f"target is not a file: {target}")
        if target.is_file() and target.read_bytes() == source.read_bytes():
            print(f"CURRENT {target}")
            continue
        print(f"{'DIFFERENT' if target.exists() else 'MISSING'} {target}")
        pending.append((source, target))
        if target.exists():
            conflicts.append(target)

    if not pending:
        return 0
    if not args.install:
        return 1
    if conflicts and not args.replace:
        print("Review differing files or use --install --replace; no files were changed")
        return 1

    home.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for source, target in pending:
        if target.exists():
            backup = home / "backups" / "codex-setup" / stamp / target.name
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            print(f"BACKUP {backup}")
        with tempfile.NamedTemporaryFile(dir=home, prefix=target.name + ".", suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            file.write(source.read_bytes())
        try:
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"INSTALLED {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
