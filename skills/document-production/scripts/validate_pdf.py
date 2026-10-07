#!/usr/bin/env python3
"""Lightweight PDF structural validator using only the Python standard library.

Checks file presence, PDF signature, EOF marker, approximate page objects, and obvious
truncation signals. It does not perform rendering, font inspection, or visual QA.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def result(status: str, check: str, detail: str) -> None:
    print(f"{status}: {check} - {detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate basic PDF structure.")
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    path = args.file

    failures = 0
    warnings = 0

    if not path.is_file():
        result("FAIL", "file", "file does not exist")
        return 2

    if path.suffix.lower() != ".pdf":
        result("FAIL", "extension", "expected .pdf")
        return 2

    data = path.read_bytes()
    if len(data) < 8 or not data.startswith(b"%PDF-"):
        failures += 1
        result("FAIL", "signature", "missing PDF header")
    else:
        version = data[:8].decode("ascii", errors="replace").strip()
        result("PASS", "signature", version)

    tail = data[-2048:] if len(data) > 2048 else data
    if b"%%EOF" in tail:
        result("PASS", "eof", "EOF marker detected near file end")
    else:
        failures += 1
        result("FAIL", "eof", "EOF marker not detected near file end")

    page_objects = len(re.findall(rb"/Type\s*/Page(?!s)\b", data))
    if page_objects > 0:
        result("PASS", "pages", f"approximately {page_objects} page objects detected")
    else:
        warnings += 1
        result("WARN", "pages", "could not identify page objects reliably")

    if b"/Encrypt" in data:
        warnings += 1
        result("WARN", "encryption", "PDF appears encrypted; downstream inspection may be limited")
    else:
        result("PASS", "encryption", "no encryption dictionary detected")

    if len(data) == 0:
        failures += 1
        result("FAIL", "size", "empty file")
    else:
        result("PASS", "size", f"{len(data)} bytes")

    result("INFO", "visual-qa", "render every page when possible; this script does not validate layout, fonts, TOC pagination, or clipping")
    print(f"SUMMARY: failures={failures} warnings={warnings}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
