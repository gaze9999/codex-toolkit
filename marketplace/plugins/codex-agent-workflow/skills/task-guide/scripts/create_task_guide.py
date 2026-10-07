#!/usr/bin/env python3
"""Validate supplied task-guide content and create portable Markdown without overwriting."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED = {"title", "scope", "read_by_task", "source_authority"}
LIST_FIELDS = {
    "scope", "path_resolution", "source_authority", "implementation_boundaries",
    "verification", "documentation", "closeout", "open_items", "id_rules",
}
TABLE_FIELDS = {
    "read_by_task": ("need", "evidence"),
    "documentation_triggers": ("trigger", "result"),
}
SECTIONS = (
    "read_by_task", "source_authority", "decisions", "work_item_ids", "implementation_boundaries",
    "verification", "documentation", "open_items",
)


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("duplicate JSON property")
        data[key] = value
    return data


def text_value(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: expected nonempty text")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ValueError(f"{field}: unsupported control character")
    return value.strip().replace("\r\n", "\n").replace("\r", "\n")


def resolve_item_ids(value: object) -> dict:
    fields = {"registry", "separator", "digits", "groups", "reserved", "items"}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("work_item_ids: expected registry, separator, digits, groups, reserved and items")
    registry = text_value(value["registry"], "work_item_ids.registry")
    separator = value["separator"]
    digits = value["digits"]
    if separator not in ("-", "_", ".", ""):
        raise ValueError("work_item_ids.separator: expected -, _, . or an empty string")
    if type(digits) is not int or not 1 <= digits <= 12:
        raise ValueError("work_item_ids.digits: expected an integer from 1 to 12")
    if not isinstance(value["groups"], list) or not value["groups"]:
        raise ValueError("work_item_ids.groups: expected nonempty group definitions")
    groups = []
    patterns = {}
    for group in value["groups"]:
        if not isinstance(group, dict) or set(group) != {"prefix", "meaning"}:
            raise ValueError("work_item_ids.groups: each group needs exactly prefix and meaning")
        prefix = text_value(group["prefix"], "work_item_ids.prefix")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", prefix) or prefix in patterns:
            raise ValueError("work_item_ids.prefix: invalid or duplicate prefix")
        patterns[prefix] = re.compile(re.escape(prefix + separator) + r"([0-9]+)")
        groups.append({"prefix": prefix, "meaning": text_value(group["meaning"], "work_item_ids.meaning")})
    if not isinstance(value["reserved"], list) or not isinstance(value["items"], list):
        raise ValueError("work_item_ids: reserved and items must be lists")
    maximum = dict.fromkeys(patterns, 0)
    occupied = {}

    def reserve(identifier: str) -> str:
        matches = [(prefix, match) for prefix, pattern in patterns.items()
                   if (match := pattern.fullmatch(identifier))]
        if len(matches) != 1:
            raise ValueError("work_item_ids: ID does not match one declared group and format")
        prefix, match = matches[0]
        number = int(match.group(1))
        if number < 1:
            raise ValueError("work_item_ids: serial numbers must be positive")
        slot = (prefix, number)
        if slot in occupied and occupied[slot] != identifier:
            raise ValueError("work_item_ids: different IDs share the same group and serial number")
        occupied[slot] = identifier
        maximum[prefix] = max(maximum[prefix], number)
        return prefix

    reserved = []
    for identifier in value["reserved"]:
        identifier = text_value(identifier, "work_item_ids.reserved")
        if identifier.startswith("~~") and identifier.endswith("~~"):
            identifier = text_value(identifier[2:-2], "work_item_ids.reserved")
        if identifier not in reserved:
            reserved.append(identifier)
    for identifier in reserved:
        reserve(identifier)
    items = []
    keys = set()
    assigned = set()
    for item in value["items"]:
        if (not isinstance(item, dict) or not {"key", "prefix", "title"} <= item.keys()
                or item.keys() - {"key", "prefix", "title", "id"}):
            raise ValueError("work_item_ids.items: each item needs key, prefix, title and optional id")
        entry = {key: text_value(item[key], "work_item_ids.items") for key in ("key", "prefix", "title")}
        if entry["key"] in keys or entry["prefix"] not in patterns:
            raise ValueError("work_item_ids.items: duplicate key or undefined group")
        keys.add(entry["key"])
        if "id" in item:
            identifier = text_value(item["id"], "work_item_ids.items.id")
            if identifier in assigned or reserve(identifier) != entry["prefix"]:
                raise ValueError("work_item_ids.items: duplicate ID or mismatched group")
            assigned.add(identifier)
            entry["id"] = identifier
        items.append(entry)
    for item in items:
        if "id" not in item:
            prefix = item["prefix"]
            maximum[prefix] += 1
            item["id"] = prefix + separator + str(maximum[prefix]).zfill(digits)
    return {"registry": registry, "separator": separator, "digits": digits,
            "groups": groups, "reserved": reserved, "items": items}


def validate_decisions(values: object) -> list[dict]:
    if not isinstance(values, list):raise ValueError('decisions: expected an array')
    entries = {}
    for value in values:
        if not isinstance(value, dict) or not {'id', 'type', 'source', 'summary'} <= value.keys() or value.keys() - {'id', 'type', 'source', 'summary', 'supersedes'}:
            raise ValueError('decisions: each record needs id, type, source and summary')
        row = {key:text_value(value[key], 'decisions.'+key) for key in ('id', 'type', 'source', 'summary')}
        if row['id'] in entries or row['type'] not in {'specification', 'user_decision', 'execution_plan'}:
            raise ValueError('decisions: duplicate ID or unknown source type')
        targets = value.get('supersedes', [])
        if not isinstance(targets, list):raise ValueError('decisions.supersedes: expected an array')
        row['supersedes'] = [text_value(target, 'decisions.supersedes') for target in targets]
        if len(set(row['supersedes'])) != len(row['supersedes']):raise ValueError('decisions: duplicate replacement target')
        entries[row['id']] = row
    for row in entries.values():
        if any(target not in entries for target in row['supersedes']):
            raise ValueError('decisions: replacement target must retain its source record')
    incoming = dict.fromkeys(entries, 0)
    for row in entries.values():
        for target in row['supersedes']:incoming[target] += 1
    pending = [identifier for identifier, count in incoming.items() if not count]
    complete = 0
    while pending:
        identifier = pending.pop()
        complete += 1
        for target in entries[identifier]['supersedes']:
            incoming[target] -= 1
            if not incoming[target]:pending.append(target)
    if complete != len(entries):raise ValueError('decisions: replacement cycle')
    replaced = {target for row in entries.values() for target in row['supersedes']}
    return [{**row, 'status':'superseded' if row['id'] in replaced else 'active'} for row in entries.values()]


def validate(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    missing = REQUIRED - data.keys()
    if missing:
        raise ValueError("missing fields: " + ", ".join(sorted(missing)))
    if data.keys() - ({"title", "section_order", "work_item_ids", "decisions"} | LIST_FIELDS | TABLE_FIELDS.keys()):
        raise ValueError("unknown input field; see the task-guide schema")
    result = {"title": text_value(data["title"], "title")}
    if "\n" in result["title"]:
        raise ValueError("title: expected a single line")
    for field in LIST_FIELDS:
        values = data.get(field, [])
        if not isinstance(values, list) or field in REQUIRED and not values:
            raise ValueError(f"{field}: expected a list with required content")
        result[field] = [text_value(value, field) for value in values]
    for field, columns in TABLE_FIELDS.items():
        rows = data.get(field, [])
        if not isinstance(rows, list) or field in REQUIRED and not rows:
            raise ValueError(f"{field}: expected a list with required rows")
        result[field] = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(columns):
                raise ValueError(f"{field}: each row needs exactly {', '.join(columns)}")
            result[field].append({key: text_value(row[key], field) for key in columns})
    order = data.get("section_order", [])
    if (not isinstance(order, list) or any(not isinstance(key, str) or key not in SECTIONS for key in order)
            or len(order) != len(set(order))):
        raise ValueError("section_order: expected distinct known section names")
    result["section_order"] = order + [key for key in SECTIONS if key not in order]
    result["work_item_ids"] = resolve_item_ids(data["work_item_ids"]) if "work_item_ids" in data else None
    result['decisions'] = validate_decisions(data.get('decisions', []))
    return result


def bullets(values: list[str]) -> list[str]:
    return ["- " + value.replace("\n", "\n  ") for value in values]


def table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def table(rows: list[dict], columns: tuple[str, str], headers: tuple[str, str]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "| --- | --- |",
        *["| " + " | ".join(table_cell(row[key]) for key in columns) + " |" for row in rows],
    ]


def render(data: dict) -> str:
    """Render validated content in the requested heading priority order."""
    lines = ["# " + data["title"], "", *bullets(data["scope"])]
    navigation = ["## 依任務讀取", ""]
    if data["path_resolution"]:
        navigation.extend([*bullets(data["path_resolution"]), ""])
    navigation.extend(table(data["read_by_task"], TABLE_FIELDS["read_by_task"],
                            ("任務", "應讀來源與證據")))
    sections = {"read_by_task": navigation}
    if data['decisions']:
        labels = {'specification':'規格既有要求', 'user_decision':'使用者決議', 'execution_plan':'執行安排'}
        rows = [{**row, 'type':labels[row['type']], 'status':'已被取代' if row['status']=='superseded' else '有效',
                 'supersedes':'、'.join(row['supersedes']) or '--'} for row in data['decisions']]
        columns = ('id', 'type', 'source', 'summary', 'supersedes', 'status')
        sections['decisions'] = ['## 需求與決策', '', '| ID | 類型 | 來源 | 內容 | 取代 ID | 狀態 |',
                                '| --- | --- | --- | --- | --- | --- |',
                                *['| '+' | '.join(table_cell(row[key]) for key in columns)+' |' for row in rows]]
    for field, heading in (
        ("source_authority", "來源優先序"),
        ("implementation_boundaries", "實作邊界"),
        ("verification", "驗證"),
    ):
        if data[field]:
            sections[field] = ["## " + heading, "", *bullets(data[field])]
    if data["work_item_ids"] or data["id_rules"]:
        identifiers = ["## 工作項目 ID", ""]
        if data["work_item_ids"]:
            scheme = data["work_item_ids"]
            identifiers.extend(["紀錄位置: " + scheme["registry"], "",
                                *table(scheme["groups"], ("prefix", "meaning"), ("前綴", "用途")), "",
                                f"編號格式: 前綴 + {json.dumps(scheme['separator'])} + 序號; 序號至少 {scheme['digits']} 位", ""])
        identifiers.extend(bullets(data["id_rules"]))
        sections["work_item_ids"] = identifiers
    if data["documentation"] or data["documentation_triggers"] or data["closeout"]:
        records = ["## 文件與紀錄", ""]
        if data["documentation_triggers"]:
            records.extend([*table(data["documentation_triggers"], TABLE_FIELDS["documentation_triggers"],
                                  ("觸發條件", "必要結果")), ""])
        records.extend(bullets(data["documentation"] + data["closeout"]))
        sections["documentation"] = records
    if data["open_items"]:
        sections["open_items"] = ["## 未確認事項", "", *bullets(data["open_items"])]
    for key in data["section_order"]:
        if key in sections:
            lines.extend(["", *sections[key]])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 JSON with confirmed task-guide content")
    parser.add_argument("--output", type=Path, help="New Markdown file; existing files are never overwritten")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="Print Markdown without writing files")
    modes.add_argument("--check", action="store_true", help="Validate JSON structure without writing files")
    modes.add_argument("--allocate-ids", action="store_true", help="Print proposed work-item IDs without updating records")
    args = parser.parse_args()
    if not args.output and not (args.dry_run or args.check or args.allocate_ids):
        parser.error("--output is required when creating a guide")
    try:
        data = validate(json.loads(args.input.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object))
        if args.check:
            print("OK input structure; source truth is not verified")
        elif args.allocate_ids:
            scheme = data["work_item_ids"]
            if not scheme:
                raise ValueError("--allocate-ids requires work_item_ids")
            print(json.dumps({"status": "proposed", "registry": scheme["registry"],
                              "items": scheme["items"]}, ensure_ascii=False, indent=2))
        elif args.dry_run:
            print(render(data), end="")
        else:
            if args.output.suffix.lower() != ".md":
                raise ValueError("output must have a .md extension")
            if args.output.exists() or args.output.is_symlink():
                raise ValueError("output already exists; refresh affected sections directly")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(render(data))
            print(f"CREATED {args.output}")
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is required")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
