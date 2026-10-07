#!/usr/bin/env python3
"""Expose the existing bounded Jev client through the official MCP SDK."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from mcp.server import MCPServer
from mcp_types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, StrictBool

if __package__:
    from . import jev
else:
    import jev


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    text: str | None = None
    required: StrictBool = False


def build_server(key_file: Path | None = None) -> MCPServer:
    server = MCPServer("Jev", instructions="Optional semantic comparison after local retrieval and deterministic filtering, when reading order or an explicit finite rubric remains useful. Not routine coding preflight. Query, rubric and candidate text go to a remote API and require approval; required candidate text stays local. Main retains source authority, dependencies and acceptance; no candidate or required check is discarded.")
    annotations = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=True)

    def evaluate(data: dict, model: str | None, rank: bool) -> dict:
        try:
            with jev.source("mcp"):
                result, _ = jev.evaluate_data(data, model or os.environ.get("TYPESAFE_MODEL", "jev-latest"), rank=rank, key_file=key_file)
            return result
        except jev.Problem as exc:
            return {"status": "fallback", "reason": str(exc)}
        except (OSError, ValueError, RecursionError):
            return {"status": "fallback", "reason": "local_operation_unavailable"}

    @server.tool(annotations=annotations)
    def jev_rank(query: str, candidates: list[Candidate], model: str | None = None) -> dict[str, Any]:
        """Rank a locally retrieved shortlist for reading relevance when ordering remains uncertain. Query and optional excerpts go to Jev; send approved content only. Required text stays local and every ID is retained. Failure preserves original order; scores do not prove correctness or readiness."""
        return evaluate({"query": query, "candidates": [candidate.model_dump(exclude_none=True) for candidate in candidates]}, model, True)

    @server.tool(annotations=annotations)
    def jev_evaluate(state: str | dict[str, Any] | list[Any], questions: dict[str, dict[str, Any]], model: str | None = None) -> dict[str, Any]:
        """Compare approved summaries using an explicit atomic noul, finite choice or ordered score rubric. State and questions go to Jev. Returns validated signals, status, model and usage; Main decides priority and acceptance. Not code generation, specification resolution or a test substitute."""
        return evaluate({"state": state, "questions": questions}, model, False)

    @server.tool(annotations=annotations)
    def jev_status(online: bool = False) -> dict[str, Any]:
        """Check credential availability without revealing it; online additionally queries models and does not submit project data."""
        try:
            with jev.source("mcp"):
                return jev.run(SimpleNamespace(command="doctor", key_file=key_file, online=online, timeout=8, retries=1))[0]
        except jev.Problem as exc:
            return {"status": "fallback", "reason": str(exc)}
        except OSError:
            return {"status": "fallback", "reason": "local_operation_unavailable"}

    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-file", type=Path, help="Override the local credential file, never pass the key itself.")
    args = parser.parse_args(argv)
    build_server(args.key_file).run(transport="stdio")


if __name__ == "__main__":
    main()
