"""Load the installed, versioned document extraction core without repository paths."""
from __future__ import annotations

import importlib


def load_core():
    try:
        core = importlib.import_module("my_py_document_core")
    except ImportError as exc:
        raise RuntimeError("Install the my-py-document-core wheel in this MCP runtime") from exc
    if getattr(core, "API_VERSION", None) != 2:
        raise RuntimeError("Unsupported document core API; this MCP requires API_VERSION=2")
    return core.extraction
