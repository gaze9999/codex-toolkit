#!/usr/bin/env python3
"""Run language-neutral structural checks on a context brief."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
TRACE_RE = re.compile(
    r"https?://\S+|(?:[A-Za-z]:[\\/]|\.?\.?/)[^\s]+|"
    r"^\s*(?:[-*]\s*)?(?:source|來源|出處|page|頁次|section|章節|row|列)\s*[:：]",
    re.IGNORECASE | re.MULTILINE,
)
SECRET_PATTERNS = (
    r"sk-[A-Za-z0-9_-]{20,}",
    r"ghp_[A-Za-z0-9_]{20,}",
    r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----",
    r"(?i)\b(?:api[_-]?key|access[_-]?token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{16,}",
)


@dataclass
class Check:
    status: str
    name: str
    message: str


def scan_markdown(text: str) -> tuple[list[tuple[int, int, str]], bool]:
    headings: list[tuple[int, int, str]] = []
    fence: tuple[str, int] | None = None
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = FENCE_RE.match(line)
        if match:
            token = match.group(1)
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1] and not line[match.end():].strip():
                fence = None
            continue
        if fence is not None:
            continue
        match = HEADING_RE.match(line)
        if match:
            headings.append((lineno, len(match.group(1)), match.group(2).strip()))
    return headings, fence is None


def check_structure(headings: list[tuple[int, int, str]]) -> list[Check]:
    if not headings:
        return [Check("FAIL", "headings", "no Markdown headings found")]
    checks = [Check("PASS", "headings", f"found {len(headings)} headings")]
    checks.append(
        Check("PASS", "title", "first heading is H1")
        if headings[0][1] == 1
        else Check("WARN", "title", f"first heading is H{headings[0][1]}, not H1")
    )
    jumps = [
        f"line {current[0]}: H{previous[1]} to H{current[1]}"
        for previous, current in zip(headings, headings[1:])
        if current[1] > previous[1] + 1
    ]
    checks.append(
        Check("WARN", "heading_hierarchy", "; ".join(jumps[:5]))
        if jumps
        else Check("PASS", "heading_hierarchy", "no skipped heading levels")
    )
    return checks


def validate(path: Path, required: list[str], strict: bool) -> list[Check]:
    if not path.is_file():
        return [Check("FAIL", "file", f"file not found: {path}")]
    checks: list[Check] = []
    if path.suffix.lower() not in {".md", ".markdown", ".txt"}:
        checks.append(Check("WARN", "extension", "expected a Markdown-like file"))
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return [Check("FAIL", "content", "file is empty")]

    headings, fences_balanced = scan_markdown(text)
    checks.extend(check_structure(headings))
    checks.append(
        Check("PASS", "code_fences", "fenced code blocks are balanced")
        if fences_balanced
        else Check("FAIL", "code_fences", "fenced code block is not closed")
    )
    folded = [title.casefold() for _, _, title in headings]
    for expected in required:
        found = any(expected.casefold() in title for title in folded)
        checks.append(
            Check("PASS", f"required_heading:{expected}", "heading found")
            if found
            else Check("FAIL", f"required_heading:{expected}", "heading not found")
        )
    checks.append(
        Check("PASS", "source_traceability", "source location marker found")
        if TRACE_RE.search(text)
        else Check("WARN", "source_traceability", "no URL, path, page, section, row, or source marker found")
    )
    secret = next((pattern for pattern in SECRET_PATTERNS if re.search(pattern, text)), None)
    checks.append(
        Check("FAIL", "secrets", "possible secret or credential pattern found")
        if secret
        else Check("PASS", "secrets", "no common secret patterns found")
    )
    if strict:
        checks = [Check("FAIL", item.name, item.message) if item.status == "WARN" else item for item in checks]
    return checks


def emit(checks: list[Check], as_json: bool) -> None:
    state = "fail" if any(item.status == "FAIL" for item in checks) else "warn" if any(item.status == "WARN" for item in checks) else "pass"
    if as_json:
        print(json.dumps({"status": state, "checks": [asdict(item) for item in checks]}, ensure_ascii=False, indent=2))
        return
    for item in checks:
        print(f"{item.status} {item.name}: {item.message}")
    print(f"SUMMARY: {state.upper()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a reusable context brief without assuming its language.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--required-heading", action="append", default=[], help="Require a heading containing this text; repeat as needed.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    args = parser.parse_args()
    checks = validate(args.path, args.required_heading, args.strict)
    emit(checks, args.json)
    return 1 if any(item.status == "FAIL" for item in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
