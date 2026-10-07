"""Narrow stdio adapters. No arbitrary shell execution or terminal input."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

MAX_INPUT = 1_000_000
FILTERS = {"cargo-test", "cargo", "pytest", "go-test", "go-build", "ctest", "tsc", "vitest", "grep", "rg", "find", "fd", "git-log", "git-diff", "git-status", "log", "mypy", "ruff-check", "ruff-format", "sqlfluff-lint", "prettier", "phpunit", "pest", "paratest", "php-test", "ecs", "phpstan", "pint"}
DIAGNOSTIC = re.compile(r"error|warning|\bfail(?:ed|ure)?\b|panic|traceback|exception", re.I)
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
SESSION_WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)


def filter_output(executable, text, original_exit_code, filter_name=None):
    if len(text.encode("utf-8")) > MAX_INPUT:
        raise ToolError("Input exceeds 1 MB; select a smaller complete log segment")
    if filter_name is not None and filter_name not in FILTERS:
        raise ToolError("Unsupported RTK built-in filter")
    args = [executable, "pipe"] + (["--filter", filter_name] if filter_name else [])
    try:
        process = subprocess.run(args, input=text, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, check=False, env=dict(os.environ, RTK_TELEMETRY_DISABLED="1"))
    except (OSError, subprocess.SubprocessError):
        return {"output": text, "original_exit_code": original_exit_code, "filter_exit_code": None, "fallback": "filter_unavailable", "compressed": False}
    output = process.stdout
    diagnostics = [line for line in text.splitlines() if DIAGNOSTIC.search(line)]
    lost = bool(diagnostics and output != text)
    fallback = "filter_failed" if process.returncode else "diagnostics_changed" if lost or original_exit_code and output != text else "empty_output" if text.strip() and not output.strip() else None
    if fallback:
        output = text
    return {"output": output, "original_exit_code": original_exit_code, "filter_exit_code": process.returncode, "fallback": fallback, "compressed": len(output) < len(text), "input_chars": len(text), "output_chars": len(output)}


def read_log(path, roots):
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ToolError("Log path must be absolute")
    try:
        resolved = candidate.resolve(strict=True)
        if not any(resolved.is_relative_to(root) for root in roots):
            raise ToolError("Log path is outside the explicit read roots")
        if resolved.suffix.lower() not in {".log", ".txt", ".out"} or not resolved.is_file():
            raise ToolError("Select a regular .log, .txt or .out file")
        with resolved.open("rb") as handle:
            raw = handle.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ToolError("Log exceeds 1 MB; select a smaller complete log segment")
        return raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ToolError("Cannot read the selected UTF-8 log") from exc


def cmux_command(executable, operation, target=None, direction=None):
    if operation == "list_workspaces":
        args = ["list-workspaces", "--json"]
    elif operation == "current_workspace":
        args = ["current-workspace", "--json"]
    elif operation == "list_panels":
        args = ["list-panels", "--json"]
    elif operation == "new_workspace":
        args = ["new-workspace"]
    elif operation == "new_split" and direction in {"left", "right", "up", "down"}:
        args = ["new-split", direction]
    elif operation in {"select_workspace", "focus_panel"} and target and re.fullmatch(r"(?:workspace|surface|pane):\d+|[0-9a-fA-F-]{36}", target):
        args = ["select-workspace", "--workspace", target] if operation == "select_workspace" else ["focus-panel", "--panel", target]
    else:
        raise ToolError("Unsupported operation or invalid target; use an ID returned by cmux")
    try:
        result = subprocess.run([executable, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ToolError("cmux unavailable; launch Codex inside an approved cmux terminal session") from exc
    if result.returncode:
        raise ToolError("cmux operation failed; exit code " + str(result.returncode))
    return {"output": result.stdout, "exit_code": result.returncode}


def make_server(tool, executable, roots):
    server = MCPServer("codex-" + tool, instructions="Use only the selected tool within the user-authorized scope; returned logs remain subject to the current environment's data boundary")
    if tool == "rtk":
        @server.tool(annotations=READ_ONLY)
        def rtk_status() -> dict:
            """Check the installed RTK version without running project commands."""
            result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=10, check=False)
            return {"version": result.stdout.strip(), "exit_code": result.returncode, "read_roots": [str(root) for root in roots], "mode": "stdin_filter_only"}

        @server.tool(annotations=READ_ONLY)
        def rtk_filter_output(text: str, original_exit_code: int, filter_name: str | None = None) -> dict:
            """Filter already captured stdout. Keep the original command's exit code; changed diagnostics cause a raw-output fallback."""
            return filter_output(executable, text, original_exit_code, filter_name)

        @server.tool(annotations=READ_ONLY)
        def rtk_filter_log(path: str, original_exit_code: int, filter_name: str | None = None) -> dict:
            """Read one explicitly allowed UTF-8 log and filter it; does not execute the originating command."""
            return filter_output(executable, read_log(path, roots), original_exit_code, filter_name)
    else:
        @server.tool(annotations=READ_ONLY)
        def cmux_inspect(operation: str = "list_workspaces") -> dict:
            """Inspect list_workspaces, current_workspace or list_panels through the existing cmux CLI."""
            if operation not in {"list_workspaces", "current_workspace", "list_panels"}:
                raise ToolError("Unsupported inspection")
            return cmux_command(executable, operation)

        @server.tool(annotations=SESSION_WRITE)
        def cmux_manage(operation: str, target: str | None = None, direction: str | None = None) -> dict:
            """Create a workspace/split, select a workspace or focus a panel. No terminal text, close or delete operations."""
            return cmux_command(executable, operation, target, direction)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", required=True, choices=["rtk", "cmux"])
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--read-root", action="append", type=Path, default=[])
    args = parser.parse_args()
    if not args.executable.is_absolute() or not args.executable.is_file():
        parser.error("Select an existing absolute native executable")
    if args.tool == "cmux" and sys.platform != "darwin":
        parser.error("cmux requires macOS")
    roots = []
    for root in args.read_root:
        if not root.is_absolute() or not root.is_dir():
            parser.error("Each read root must be an existing absolute directory")
        roots.append(root.resolve())
    make_server(args.tool, str(args.executable.resolve()), roots).run(transport="stdio")


if __name__ == "__main__":
    main()
