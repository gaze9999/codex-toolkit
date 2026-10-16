"""Resolve resources for source and standalone command-line applications."""

from pathlib import Path
import sys


def is_bundled() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
