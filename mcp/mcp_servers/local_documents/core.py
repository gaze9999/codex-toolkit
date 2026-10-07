"""Load the installed, versioned document core without repository paths."""
from __future__ import annotations

import importlib


def load_core():
    try:
        core = importlib.import_module("my_py_document_core")
    except ImportError as exc:
        raise RuntimeError("Install the my-py-document-core wheel in this MCP runtime") from exc
    if getattr(core, "API_VERSION", None) != 1:
        raise RuntimeError("Unsupported document core API; this MCP requires API_VERSION=1")
    if not hasattr(core, "matching"):
        raise RuntimeError("Installed document core does not provide Markdown source matching")
    return core.extraction, core.matching, core.updates
