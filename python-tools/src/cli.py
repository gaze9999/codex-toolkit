"""List tools or run one tool, preserving its arguments and exit status."""

from __future__ import annotations

import argparse
import os
import runpy
import sys

from shared.tool_catalog import TOOLS
from shared.runtime import is_bundled, resource_root


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if is_bundled():
        os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(resource_root() / "tiktoken-cache"))
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__, usage="%(prog)s [--list] <module-or-id> [arguments ...]")
    parser.add_argument("--list", action="store_true", help="List tools by purpose")
    parser.add_argument("tool", nargs="?", help="Module name or CLI tool id")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    if not arguments or arguments == ["--list"]:
        for tool in TOOLS:
            print(f"{tool.category}: {tool.module} ({tool.id})\n  {tool.description}")
        return 0
    args = parser.parse_args(arguments)
    modules = {value: tool.module for tool in TOOLS for value in (tool.module, tool.id)}
    if not is_bundled():
        for name in ("distribution.build_cli", "distribution.smoke_cli"):
            modules[name] = name
    module = modules.get(args.tool)
    if module is None:
        parser.error("Unknown tool; use --list to see available tools")
    tool = next((tool for tool in TOOLS if tool.module == module), None)
    if is_bundled() and tool and tool.payload()["source_only"] and args.arguments not in (["--help"], ["-h"]):
        parser.error("This development tool requires a complete source checkout and development Python; use launch-cli.py")
    previous = sys.argv
    try:
        sys.argv = [module, *args.arguments]
        runpy.run_module(module, run_name="__main__")
    finally:
        sys.argv = previous
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
