#!/usr/bin/env python3
"""Compactly classify changed files by likely documentation impact."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

DOC_EXTS = {".md", ".mdx", ".rst", ".txt", ".adoc"}
TEST_HINTS = {"test", "tests", "spec", "__tests__", "fixtures", "mocks"}
CONFIG_NAMES = {
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "requirements.txt", "pyproject.toml", "poetry.lock", "dockerfile",
    "docker-compose.yml", "compose.yml", ".env.example",
}
PUBLIC_HINTS = {
    "api", "routes", "controllers", "schema", "schemas", "openapi", "swagger",
    "sdk", "cli", "commands", "config", "migration", "migrations", "public",
}
UI_HINTS = {"components", "pages", "views", "ui", "screens", "routes"}
DOC_HINTS = {"readme", "docs", "documentation", "memo", "memos", "notes", "changelog"}


@dataclass
class FileImpact:
    path: str
    change_type: str
    category: str
    likely_doc_impact: str
    reason: str


def run_git(repo: Path, args: list[str]) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or "git command failed")
    return result.stdout


def decode(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def parse_name_status(data: bytes) -> list[tuple[str, str]]:
    fields = data.rstrip(b"\0").split(b"\0") if data else []
    rows: list[tuple[str, str]] = []
    index = 0
    while index < len(fields):
        status = decode(fields[index])
        index += 1
        if index >= len(fields):
            raise ValueError("incomplete git --name-status output")
        path = decode(fields[index])
        index += 1
        if status[:1] in {"R", "C"}:
            if index >= len(fields):
                raise ValueError("incomplete git rename/copy output")
            path = decode(fields[index])
            index += 1
        rows.append((status, path))
    return rows


def merge_rows(*groups: list[tuple[str, str]]) -> list[tuple[str, str]]:
    merged: dict[str, list[str]] = {}
    for group in groups:
        for status, path in group:
            states = merged.setdefault(path, [])
            if status not in states:
                states.append(status)
    return [("/".join(states), path) for path, states in merged.items()]


def changed_from_repo(repo: Path, base: str | None) -> list[tuple[str, str]]:
    if base:
        tracked = parse_name_status(run_git(repo, ["diff", "--name-status", "-z", base]))
    else:
        staged = parse_name_status(run_git(repo, ["diff", "--cached", "--name-status", "-z"]))
        unstaged = parse_name_status(run_git(repo, ["diff", "--name-status", "-z"]))
        tracked = merge_rows(staged, unstaged)
        if not tracked:
            try:
                tracked = parse_name_status(run_git(repo, ["diff", "--name-status", "-z", "HEAD~1", "HEAD"]))
            except RuntimeError:
                tracked = []
    untracked = [("??", decode(path)) for path in run_git(repo, ["ls-files", "--others", "--exclude-standard", "-z"]).rstrip(b"\0").split(b"\0") if path]
    return merge_rows(tracked, untracked)


def changed_from_diff(diff_file: Path) -> list[tuple[str, str]]:
    rows = []
    for line in diff_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("diff --git "):
            match = re.search(r" b/(.+)$", line)
            if match:
                rows.append(("M", match.group(1)))
    return merge_rows(rows)


def classify(path_text: str, status: str) -> FileImpact:
    path = Path(path_text)
    lower = path_text.lower()
    parts = {part.lower() for part in path.parts}
    tokens = set(re.split(r"[^a-z0-9]+", lower))
    ext = path.suffix.lower()
    name = path.name.lower()
    if name in CONFIG_NAMES or parts & {"config", ".github", "scripts"}:
        return FileImpact(path_text, status, "configuration", "yes", "configuration, setup, or automation path")
    if parts & TEST_HINTS or tokens & TEST_HINTS:
        return FileImpact(path_text, status, "test", "no", "test or fixture path")
    if ext in DOC_EXTS or parts & DOC_HINTS or tokens & DOC_HINTS:
        return FileImpact(path_text, status, "documentation", "yes", "documentation file")
    if tokens & PUBLIC_HINTS:
        return FileImpact(path_text, status, "public-contract", "yes", "public API, schema, CLI, config, or migration path")
    if tokens & UI_HINTS:
        return FileImpact(path_text, status, "ui-or-route", "maybe", "UI or route path")
    if ext in {".json", ".yaml", ".yml", ".toml"}:
        return FileImpact(path_text, status, "structured-data", "maybe", "structured data or metadata")
    if ext in {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".java", ".cs", ".rb", ".php"}:
        return FileImpact(path_text, status, "source", "maybe", "source file")
    return FileImpact(path_text, status, "other", "no", "no path-only documentation signal")


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify changed files by likely documentation impact.")
    parser.add_argument("--repo", default=".", help="Repository root. Default: current directory.")
    parser.add_argument("--base", help="Optional base ref compared with the current working tree.")
    parser.add_argument("--diff-file", help="Unified diff to scan instead of Git.")
    parser.add_argument("--max-files", type=int, default=80, help="Maximum detailed files; 0 means unlimited.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.max_files < 0:
        print("ERROR: --max-files must be 0 or greater")
        return 2
    try:
        rows = changed_from_diff(Path(args.diff_file)) if args.diff_file else changed_from_repo(Path(args.repo).resolve(), args.base)
        items = [classify(path, status) for status, path in rows]
    except (OSError, RuntimeError, ValueError) as exc:
        payload = {"status": "error", "message": str(exc)}
        print(json.dumps(payload, ensure_ascii=False) if args.json else f"ERROR: {exc}")
        return 2

    counts = {level: sum(item.likely_doc_impact == level for item in items) for level in ("yes", "maybe", "no")}
    shown = items if not args.max_files else items[:args.max_files]
    omitted = len(items) - len(shown)
    if args.json:
        print(json.dumps({"status": "ok", "counts": counts, "omitted": omitted, "files": [asdict(item) for item in shown]}, ensure_ascii=False, indent=2))
    else:
        print(f"files={len(items)} yes={counts['yes']} maybe={counts['maybe']} no={counts['no']} omitted={omitted}")
        for item in shown:
            print(f"- [{item.likely_doc_impact}] {item.change_type} {item.path} ({item.category}: {item.reason})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
