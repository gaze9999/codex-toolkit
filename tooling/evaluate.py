#!/usr/bin/env python3
"""Inspect routing fixtures and compare explicitly supplied, content-free local run metrics."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp/scripts"))
from audit_skills import FRONTMATTER_RE, scalar
from plugin_catalog import load_catalog

METRICS = {"duration_seconds", "input_tokens", "output_tokens", "context_bytes", "tool_calls", "subagents", "retries", "human_corrections", "regressions"}
FIELDS = {"case_id", "trial", "variant", "model", "effort", "environment", "source_revision", "accepted", "first_pass", "validation"} | METRICS
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def inventory(root: Path) -> dict:
    owners = {skill: bundle["id"] for bundle in load_catalog(root) for skill in bundle["skills"]}
    rows = []
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        if match is None:
            raise ValueError("Invalid Skill frontmatter")
        folder = path.parent
        rows.append({"skill": folder.name, "plugin": owners.get(folder.name), "description": scalar(match.group(1), "description"), "metadata_bytes": len(match.group(1).encode()), "body_bytes": len(text[match.end():].encode()), "references": len(list((folder / "references").rglob("*.md"))), "scripts": len(list((folder / "scripts").rglob("*.py")))})
    return {"skills": rows, "measurement": "UTF-8 bytes and file counts; not token counts or account usage"}


def routing(root: Path, observed: Path | None = None) -> dict:
    fixtures = read_json(root / "evals/routing.json")
    skills = {path.parent.name for path in (root / "skills").glob("*/SKILL.md")}
    cases = {}
    for case in fixtures["cases"]:
        if case["id"] in cases or case["kind"] not in {"positive", "negative", "collision"} or not case["prompt"] or len(case["expected"]) != len(set(case["expected"])) or set(case["expected"]) - skills:
            raise ValueError("Invalid routing fixture")
        cases[case["id"]] = case
    if observed is None:
        return {"status": "fixtures_validated", "cases": len(cases), "behavior": "unverified; record actual agent selections before scoring"}
    answers = read_json(observed)
    if not isinstance(answers, list):
        raise ValueError("Routing observations must be an array")
    results, seen = [], set()
    for row in answers:
        if not isinstance(row, dict) or set(row) != {"case_id", "selected"} or row["case_id"] not in cases or row["case_id"] in seen or not isinstance(row["selected"], list) or any(not isinstance(item, str) for item in row["selected"]) or len(row["selected"]) != len(set(row["selected"])) or set(row["selected"]) - skills:
            raise ValueError("Invalid, unknown or duplicate routing observation")
        seen.add(row["case_id"])
        expected = set(cases[row["case_id"]]["expected"])
        selected = set(row["selected"])
        results.append({"case_id": row["case_id"], "passed": expected == selected, "missing": sorted(expected - selected), "unexpected": sorted(selected - expected)})
    missing = sorted(set(cases) - seen)
    return {"status": "passed" if not missing and all(row["passed"] for row in results) else "incomplete_or_failed", "results": results, "unobserved": missing}


def run_records(path: Path, known_cases: set[str]) -> list[dict]:
    rows, seen = [], set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or set(row) - FIELDS:
            raise ValueError("Run metrics contain unknown fields; source text, logs and credentials are not accepted")
        if row.get("case_id") not in known_cases or row.get("variant") not in {"before", "after"} or type(row.get("trial")) is not int or row["trial"] < 1:
            raise ValueError("Run needs a known case, variant and positive trial")
        identity = row["case_id"], row["trial"], row["variant"]
        if identity in seen:
            raise ValueError("Duplicate run record")
        seen.add(identity)
        for key in ("model", "effort", "environment"):
            if row.get(key) is not None and (not isinstance(row[key], str) or not IDENTIFIER.fullmatch(row[key])):
                raise ValueError("Run labels must be short opaque identifiers")
        if row.get("source_revision") is not None and (not isinstance(row["source_revision"], str) or not re.fullmatch(r"(?:[a-f0-9]{40}|[a-f0-9]{64})", row["source_revision"])):
            raise ValueError("Invalid source revision")
        for key in ("accepted", "first_pass"):
            if row.get(key) is not None and type(row[key]) is not bool:
                raise ValueError("Acceptance must be boolean or null")
        if row.get("validation") not in {None, "passed", "failed", "not_run", "blocked"}:
            raise ValueError("Invalid validation result")
        for key in METRICS:
            value = row.get(key)
            if value is not None and (type(value) not in {int, float} or not math.isfinite(value) or value < 0 or key != "duration_seconds" and type(value) is not int):
                raise ValueError("Metrics must be nonnegative measured values or null")
        rows.append(row)
    return rows


def compare(root: Path, path: Path) -> dict:
    benchmark = read_json(root / "evals/benchmark.json")
    known_cases = {row["id"] for row in benchmark["cases"]}
    rows = run_records(path, known_cases)
    variants = {variant: {(row["case_id"], row["trial"]): row for row in rows if row["variant"] == variant} for variant in ("before", "after")}
    paired = set(variants["before"]) & set(variants["after"])
    metrics = {}
    for key in sorted(METRICS | {"accepted", "first_pass"}):
        measured = [pair for pair in sorted(paired) if variants["before"][pair].get(key) is not None and variants["after"][pair].get(key) is not None]
        metrics[key] = {"paired_observations": len(measured)}
        for variant in variants:
            values = [variants[variant][pair][key] for pair in measured]
            metrics[key][variant] = (sum(values) / len(values) if key in {"accepted", "first_pass"} else statistics.median(values)) if values else None
    changed_conditions = [key for key in ("model", "effort", "environment") if any(variants["before"][pair].get(key) != variants["after"][pair].get(key) for pair in paired)]
    missing_conditions = [key for key in ("model", "effort", "environment", "source_revision") if any(variants[variant][pair].get(key) is None for pair in paired for variant in variants)]
    return {"status": "compared" if paired else "no_paired_observations", "paired_runs": len(paired), "unpaired_runs": len(rows) - 2 * len(paired), "unobserved_cases": sorted(known_cases - {pair[0] for pair in paired}), "changed_conditions": changed_conditions, "missing_conditions": missing_conditions, "metrics": metrics, "validation": {variant: {state: sum(row.get("validation") == state for pair, row in records.items() if pair in paired) for state in ("passed", "failed", "not_run", "blocked", None)} for variant, records in variants.items()}, "interpretation": "Paired medians and observed acceptance rates; bytes are a context proxy, unknown usage stays null. Changed or missing conditions limit causal claims."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inventory", "routing", "compare"))
    parser.add_argument("--observed", type=Path, help="Recorded routing selections, never automatically inferred")
    parser.add_argument("--runs", type=Path, help="Explicit content-free JSONL run measurements")
    args = parser.parse_args(argv)
    try:
        if args.action == "inventory":
            result = inventory(ROOT)
        elif args.action == "routing":
            result = routing(ROOT, args.observed)
        else:
            if args.runs is None:
                parser.error("compare requires --runs")
            result = compare(ROOT, args.runs)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(result.get("status") in {"incomplete_or_failed", "no_paired_observations"})
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
