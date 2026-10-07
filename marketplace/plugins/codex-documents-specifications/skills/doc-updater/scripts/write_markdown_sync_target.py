#!/usr/bin/env python3
"""Safely replace one explicit Markdown sync target after a hash check."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Write one explicit Markdown target with an optimistic-concurrency hash guard.")
    parser.add_argument("file", help="Explicit Markdown target to replace.")
    parser.add_argument("--content-file", required=True, help="UTF-8 replacement content file.")
    parser.add_argument("--expected-sha256", required=True, help="SHA-256 returned by inspect_markdown_sync_target.py.")
    parser.add_argument("--dry-run", action="store_true", help="Validate the target and content without writing.")
    args = parser.parse_args()

    target = Path(args.file)
    content = Path(args.content_file)
    if target.suffix.lower() not in {".md", ".markdown", ".mdx"}:
        print("ERROR: Target must be a Markdown file (.md, .markdown, or .mdx).", file=sys.stderr)
        return 2
    if not target.is_file() or not content.is_file():
        print("ERROR: Target or replacement content file was not found.", file=sys.stderr)
        return 2
    current = digest(target)
    if current.lower() != args.expected_sha256.lower():
        print("ERROR: Target changed after it was read; re-inspect and merge before writing.", file=sys.stderr)
        return 3
    replacement = content.read_bytes()
    try:
        replacement.decode("utf-8")
    except UnicodeDecodeError:
        print("ERROR: Replacement content must be UTF-8.", file=sys.stderr)
        return 2
    if args.dry_run:
        print(f"DRY-RUN: {target.resolve()} would be replaced ({len(replacement)} bytes).")
        return 0
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
        handle.write(replacement)
        temp_name = handle.name
    try:
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    print(f"WROTE: {target.resolve()} sha256={digest(target)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
