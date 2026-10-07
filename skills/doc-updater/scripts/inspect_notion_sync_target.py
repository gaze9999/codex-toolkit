#!/usr/bin/env python3
"""Inspect one uploaded Notion page snapshot without connecting or writing."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def inspect(snapshot_path: Path, expected_page_id: str | None) -> dict:
    if snapshot_path.suffix.lower() != ".json":
        raise ValueError("Notion input must be an uploaded JSON snapshot or export.")
    data = snapshot_path.read_bytes()
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Notion snapshot root must be a JSON object.")

    page = payload.get("page", payload)
    if not isinstance(page, dict):
        raise ValueError("Notion snapshot page must be a JSON object.")
    page_id = page.get("id") or payload.get("page_id")
    if not page_id:
        raise ValueError("Notion snapshot must include page.id or page_id.")
    if expected_page_id and page_id.replace("-", "") != expected_page_id.replace("-", ""):
        raise ValueError("Uploaded snapshot page ID does not match --page-id.")

    blocks = payload.get("blocks", [])
    if not isinstance(blocks, list):
        raise ValueError("Notion snapshot blocks must be a JSON array when provided.")
    return {
        "status": "ok",
        "target": {
            "source_file": str(snapshot_path.resolve()),
            "sha256": hashlib.sha256(data).hexdigest(),
            "page_id": page_id,
            "url": page.get("url"),
            "last_edited_time": page.get("last_edited_time"),
            "archived": page.get("archived"),
            "in_trash": page.get("in_trash"),
            "properties": page.get("properties", {}),
            "block_count": len(blocks),
            "blocks_complete": payload.get("blocks_complete"),
            "next_cursor": payload.get("next_cursor"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect one uploaded Notion page snapshot. It never connects to or writes to Notion."
    )
    parser.add_argument("snapshot", help="Explicit uploaded Notion JSON snapshot or export.")
    parser.add_argument("--page-id", help="Optional exact page ID to verify against the uploaded snapshot.")
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = parser.parse_args()
    try:
        result = inspect(Path(args.snapshot), args.page_id)
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}) if args.json else f"ERROR: {exc}")
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        target = result["target"]
        print(f"Notion sync target: {target['page_id']}")
        print(f"- sha256: {target['sha256']}")
        print(f"- last_edited_time: {target['last_edited_time']}")
        print(f"- direct_blocks: {target['block_count']}")
        print(f"- blocks_complete: {target['blocks_complete']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
