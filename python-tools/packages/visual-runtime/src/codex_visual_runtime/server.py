"""Thin MCP adapter around process-owned previews and scoped inspection."""
import argparse
from typing import Any
from .core import Workspace, Previews, Problem


def build_server():
    from mcp.server import MCPServer
    from mcp_types import ToolAnnotations
    previews = Previews()
    server = MCPServer("Visual Runtime", instructions="Provide an authorized project root for each inspection, artifact or preview-start call. Preview jobs keep their own file snapshots and are controlled by job_id. No shell execution, framework migration or engine installation. Preview HTML runs in the browser; approve its source and network behavior. Main selects the project toolchain.")
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)

    def run(operation, *args):
        try:
            return operation(*args)
        except (Problem, OSError, ValueError, TypeError, AttributeError):
            return {"status": "local_error"}

    @server.tool(annotations=read)
    def visual_inspect(root: str) -> dict[str, Any]:
        """Read framework/dependency declarations in this call's authorized project root; never run scripts."""
        return run(lambda: Workspace(root).inspect())

    @server.tool(annotations=read)
    def visual_artifacts(root: str, paths: list[str]) -> dict[str, Any]:
        """Hash explicit files relative to this call's authorized root; no file contents returned."""
        return run(lambda: Workspace(root).artifacts(paths))

    @server.tool(annotations=write)
    def visual_preview_start(root: str, entry: str, files: list[str]) -> dict[str, Any]:
        """Snapshot explicit files within this call's authorized root into an owned loopback preview. Select only authorized public browser assets, never secrets. No directory listing or arbitrary commands."""
        return run(lambda: previews.start(entry, files, workspace=Workspace(root)))

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
    parser.parse_args()
    server, previews = build_server()
    try:
        server.run(transport="stdio")
    finally:
        previews.close()


if __name__ == "__main__":
    main()
