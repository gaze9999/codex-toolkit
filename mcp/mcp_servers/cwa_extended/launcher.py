"""Launch the unchanged pinned CWA source using an environment credential."""
import os
from pathlib import Path
import runpy
import sys


def main():
    key = os.environ.get("CWA_API_KEY")
    if not key:
        print("Set CWA_API_KEY in the approved local environment", file=sys.stderr)
        return 2
    source = Path(__file__).resolve().parent / "upstream"
    previous_args, previous_path = sys.argv[:], sys.path[:]
    try:
        # The upstream script reads argv in-process; no credential enters an OS command line
        sys.argv = [str(source / "server.py"), key]
        sys.path.insert(0, str(source))
        runpy.run_path(str(source / "server.py"), run_name="__main__")
    finally:
        sys.argv, sys.path[:] = previous_args, previous_path
