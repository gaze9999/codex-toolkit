"""Versioned document extraction API for MCP servers and other local Python applications.

Markdown validation, guarded updates, reference analysis and extract lookup moved to the
native markdown-checks CLI (Toolkit tools/markdown-checks).
"""

API_VERSION = 2

from . import extraction

__all__ = ["API_VERSION", "extraction"]
