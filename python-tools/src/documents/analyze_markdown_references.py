"""Analyze selected local Markdown links and reverse references as JSON."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def analyzer():
    if __package__ == "my_py_document_core.documents":
        from ..references import analyze_references

        return analyze_references
    core_path = Path(__file__).resolve().parents[1] / "my_py_document_core" / "references.py"
    spec = importlib.util.spec_from_file_location("_reference_core", core_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.analyze_references


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Explicit local document root")
    parser.add_argument("--document", action="append", required=True, help="Selected document path relative to root; repeatable")
    parser.add_argument("--affected", action="append", default=[], help="Changed/renamed/deleted path relative to root; repeatable")
    args = parser.parse_args(argv)
    try:
        root = Path(args.root).resolve()
        result = analyzer()(root, args.document, args.affected)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 1 if result["partial"] else 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
