"""Thin MCP adapter around process-owned previews and scoped inspection."""
import argparse
from typing import Any
from .core import Workspace, Previews, Problem


def build_server(root):
    from mcp.server import MCPServer
    from mcp_types import ToolAnnotations
    workspace = Workspace(root)
    previews = Previews(workspace)
    server = MCPServer("Visual Runtime", instructions="Inspect the selected root and preview explicitly selected static assets. No shell execution, framework migration or engine installation. Preview HTML runs in the browser; approve its source and network behavior. Main selects the project toolchain.")
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)

    def run(operation, *args):
        try:
            return operation(*args)
        except (Problem, OSError, ValueError, TypeError, AttributeError):
            return {"status": "local_error"}

    @server.tool(annotations=read)
    def visual_inspect() -> dict[str, Any]:
        """Read framework/dependency declarations in the configured project root; never run scripts."""
        return run(workspace.inspect)

    @server.tool(annotations=read)
    def visual_artifacts(paths: list[str]) -> dict[str, Any]:
        """Hash explicit relative files for evidence; no file contents returned."""
        return run(workspace.artifacts, paths)

    @server.tool(annotations=write)
    def visual_preview_start(entry: str, files: list[str]) -> dict[str, Any]:
        """Start an owned loopback static snapshot from an explicit file manifest. Select only authorized public browser assets, never secrets. No directory listing or arbitrary commands."""
        return run(previews.start, entry, files)

    @server.tool(annotations=read)
    def visual_preview_status(job_id: str) -> dict[str, Any]:
        """Inspect a preview owned by this MCP process."""
        return previews.status(job_id)

    @server.tool(annotations=write)
    def visual_preview_stop(job_id: str) -> dict[str, Any]:
        """Stop only this process's preview job and release its listener."""
        return previews.stop(job_id)

    return server, previews


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    server, previews = build_server(args.root)
    try:
        server.run(transport="stdio")
    finally:
        previews.close()


if __name__ == "__main__":
    main()
