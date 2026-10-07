#!/usr/bin/env python3
"""Verify stdio MCP discovery; --online uses only built-in public sample text."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def verify(online: bool) -> int:
    arguments = ["-I", "-B", "-m", __package__ + ".mcp_server"] if __package__ else ["-B", str(Path(__file__).with_name("mcp_server.py"))]
    server = StdioServerParameters(command=sys.executable, args=arguments, env=os.environ.copy())
    async with Client(server, read_timeout_seconds=30) as client:
        names = sorted(tool.name for tool in (await client.list_tools()).tools)
        if names != ["jev_evaluate", "jev_rank", "jev_status"]:
            raise ValueError("unexpected_tools")
        candidates = [{"id": "required-guidance", "required": True}]
        if online:
            candidates += [{"id": "validation", "text": "The form validator checks required fields before submission."}, {"id": "theme", "text": "Theme settings control page colors and fonts."}]
        result = await client.call_tool("jev_rank", {"query": "Where is form validation implemented?", "candidates": candidates})
        data = result.structured_content
        if result.is_error or not isinstance(data, dict):
            raise ValueError("invalid_tool_response")
        print(json.dumps({"status": "ok" if data.get("status") in {"ok", "skipped"} else "fallback", "protocol": client.protocol_version, "tools": names, "rank": data}, ensure_ascii=False, separators=(",", ":")))
        return 0 if data.get("status") in {"ok", "skipped"} else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", help="Submit a small public English example to Jev.")
    args = parser.parse_args(argv)
    try:
        return asyncio.run(asyncio.wait_for(verify(args.online), timeout=45))
    except Exception:
        print('{"status":"fallback","reason":"mcp_verification_unavailable"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
