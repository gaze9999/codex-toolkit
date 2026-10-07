"""Load the installed workspace core without repository path coupling."""

from __future__ import annotations

import importlib


def load_core():
    try:
        core = importlib.import_module("my_py_workspace_core")
    except ImportError as exc:
        raise RuntimeError("Install the my-py-workspace-core wheel in this MCP runtime") from exc
    if getattr(core, "API_VERSION", None) != 1:
        raise RuntimeError("Unsupported workspace core API; this MCP requires API_VERSION=1")
    return core
