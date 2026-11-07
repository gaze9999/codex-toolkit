"""Optional stdio MCP adapter; core stays independent of MCP."""
import argparse
from typing import Any
from . import core


def build_server(config):
    from mcp.server import MCPServer
    from mcp_types import ToolAnnotations
    from pydantic import StrictBool
    server = MCPServer("Decisions", instructions="Optional bounded evaluation of authorized evidence. Main chooses tools and delegation; answers never authorize actions. No ChatGPT credential reuse or provider fallback.")
    local = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    remote = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=True)

    @server.tool(annotations=local)
    def decisions_status() -> dict[str, Any]:
        """Check selected credential variable presence, without network or secret output."""
        return core.status(config)

    @server.tool(annotations=local)
    def decisions_validate(request: dict) -> dict[str, Any]:
        """Validate bounded request JSON locally; return byte size/hash, never echo evidence."""
        try:
            return core.preview(request, config)
        except core.Problem as exc:
            return {"status": "invalid_input", "reason": str(exc)}

    @server.tool(annotations=remote)
    def decisions_evaluate(request: dict, approved: StrictBool = False) -> dict[str, Any]:
        """Send evidence and rubric to OpenAI only with scoped user authorization. Predicate, choice, score and per-question refusals retain provider meaning. approved is an assertion of existing authority, not a permission grant."""
        try:
            return core.evaluate(request, config, approved=approved)
        except core.Problem as exc:
            return {"status": "invalid_input", "reason": str(exc)}

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    args = parser.parse_args()
    build_server(core.config_from(args.config)).run(transport="stdio")


if __name__ == "__main__":
    main()
