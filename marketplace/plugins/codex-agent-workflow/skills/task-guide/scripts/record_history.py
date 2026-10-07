#!/usr/bin/env python3
"""Append confirmed Traditional Chinese history snapshots, preserving existing records."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from create_task_guide import text_value, unique_object


def validate(data: object) -> dict:
    required = {"timestamp", "title", "summary"}
    allowed = required | {"commit", "repository", "uncommitted", "checks", "open_items"}
    if not isinstance(data, dict) or required - data.keys() or data.keys() - allowed:
        raise ValueError("快照需有 timestamp, title, summary; 不接受未定義欄位")
    result = {key: text_value(data[key], key) for key in required}
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", result["timestamp"]):
        raise ValueError("時間格式需為 yyyy-mm-dd hh:mm")
    datetime.strptime(result["timestamp"], "%Y-%m-%d %H:%M")
    if "\n" in result["title"]:
        raise ValueError("標題需為單行")
    result["commit"] = ""
    if "commit" in data:
        commit = text_value(data["commit"], "commit")
        if not re.fullmatch(r"[0-9a-fA-F]{4,39}", commit):
            raise ValueError("commit 需為已確認的短 SHA, 不截斷完整 SHA")
        result["commit"] = commit
    result["repository"] = text_value(data["repository"], "repository") if "repository" in data else ""
    if "\n" in result["repository"]:
        raise ValueError("repository 需為單行名稱")
    result["uncommitted"] = data.get("uncommitted", False)
    if type(result["uncommitted"]) is not bool:
        raise ValueError("uncommitted 需為 boolean")
    for key in ("checks", "open_items"):
        values = data.get(key, [])
        if not isinstance(values, list):
            raise ValueError(f"{key} 需為文字陣列")
        result[key] = [text_value(value, key) for value in values]
    return result


def render(data: dict) -> str:
    lines = [f"## {data['timestamp']} {data['title']}", ""]
    if data["commit"]:
        reference = (data["repository"] + "@" if data["repository"] else "") + data["commit"]
        lines.extend(["Git: " + reference + (" + 未提交變更" if data["uncommitted"] else ""), ""])
    lines.append(data["summary"])
    details = [*("- 驗證: " + value.replace("\n", "\n  ") for value in data["checks"]),
               *("- 未完成: " + value.replace("\n", "\n  ") for value in data["open_items"])]
    if details:
        lines.extend(["", *details])
    return "\n".join(lines) + "\n"


def record(path: Path, entry: str) -> None:
    if path.suffix.lower() != ".md" or path.is_symlink():
        raise ValueError("輸出需為一般 .md 檔案")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(("# 歷史快照\n\n" + entry).encode("utf-8"))
        return
    original = path.read_bytes()
    text = original.decode("utf-8-sig")
    if entry.splitlines()[0] in text.splitlines():
        raise ValueError("相同時間與標題的快照已存在")
    newline = "\r\n" if b"\r\n" in original else "\n"
    gap = "" if text.endswith(newline * 2) else newline if text.endswith(newline) else newline * 2
    addition = (gap + entry.replace("\n", newline)).encode("utf-8")
    if path.read_bytes() != original:
        raise ValueError("快照已由其他 owner 變更, 請重新讀取")
    with path.open("ab") as stream:
        stream.write(addition)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="已確認快照內容的 UTF-8 JSON")
    parser.add_argument("--output", type=Path, help="新增或追加的歷史快照 Markdown")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="只顯示新紀錄, 不寫檔")
    modes.add_argument("--check", action="store_true", help="只驗證輸入結構")
    args = parser.parse_args()
    if not args.output and not (args.dry_run or args.check):
        parser.error("寫入快照時需要 --output")
    try:
        data = validate(json.loads(args.input.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object))
        if args.check:
            print("輸入結構有效; 未驗證來源, 時間與 commit 證據")
        elif args.dry_run:
            print(render(data), end="")
        else:
            if args.input.resolve() == args.output.resolve():
                raise ValueError("輸出不可覆寫輸入檔案")
            record(args.output, render(data))
            print(f"已記錄 {args.output}")
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"錯誤: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if sys.version_info < (3, 10):
        raise SystemExit("需要 Python 3.10 以上")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
