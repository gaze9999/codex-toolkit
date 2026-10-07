"""Exercise Workspace Inspection stdio discovery and read-only boundaries."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile


async def verify() -> dict[str, object]:
    try:
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters
    except ModuleNotFoundError as exc:
        raise RuntimeError("Install codex-workspace-inspection-mcp and its dependencies") from exc
    with tempfile.TemporaryDirectory(prefix="workspace-inspection-verify-") as directory:
        root = Path(directory)
        source = root / "source"
        target = root / "target"
        runs = root / "runs"
        source.mkdir()
        target.mkdir()
        (runs / "run-001").mkdir(parents=True)
        (source / "same.txt").write_text("same", encoding="utf-8")
        (target / "same.txt").write_text("same", encoding="utf-8")
        (source / "changed.txt").write_text("before", encoding="utf-8")
        (target / "changed.txt").write_text("after", encoding="utf-8")
        (runs / "run-001" / "results.json").write_text(
            json.dumps({"started": "2026-10-01T12:00:00", "results": [{"name": "unit", "status": "passed", "command": "python -m unittest"}]}),
            encoding="utf-8",
        )
        params = StdioServerParameters(
            command=sys.executable,
            args=["-I", "-B", "-m", "workspace_inspection_mcp.server", "--read-root", str(root)],
            env={**os.environ, "PYTHONUTF8": "1"},
        )
        async with Client(params, read_timeout_seconds=60) as client:
            tools = sorted(tool.name for tool in (await client.list_tools()).tools)
            assert tools == ["compare_environment", "validation_evidence", "workspace_status"], tools

            async def call(name, arguments):
                result = await client.call_tool(name, arguments)
                assert not result.is_error, result.content
                return result.structured_content

            status = await call("workspace_status", {})
            comparison = await call("compare_environment", {"source": str(source), "target": str(target)})
            evidence = await call("validation_evidence", {"root": str(runs)})
            outside = await client.call_tool("validation_evidence", {"root": str(root.parent)})
            assert status["read_only"] is True
            assert comparison["status"] == "different" and comparison["changed"][0]["path"] == "changed.txt"
            assert evidence["runs"][0]["results"][0]["status"] == "passed"
            assert outside.is_error
            return {"status": "passed", "tools": tools, "guards": ["path_roots", "read_only", "bounded_limits"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        result = asyncio.run(asyncio.wait_for(verify(), timeout=90))
    except (RuntimeError, OSError, AssertionError, asyncio.TimeoutError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
