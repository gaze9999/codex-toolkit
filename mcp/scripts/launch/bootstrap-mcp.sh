#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
if [ -n "${CODEX_SETUP_PYTHON:-}" ]; then
    "$CODEX_SETUP_PYTHON" -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 2)' >/dev/null 2>&1 || { echo 'Selected Python must be working Python 3.11+' >&2; exit 2; }
    exec "$CODEX_SETUP_PYTHON" -X utf8 -B "$ROOT_DIR/mcp/scripts/bootstrap_mcp.py" "$@"
fi
for candidate in python3 python3.13 python; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 2)' >/dev/null 2>&1; then
        exec "$candidate" -X utf8 -B "$ROOT_DIR/mcp/scripts/bootstrap_mcp.py" "$@"
    fi
done
echo 'Select an existing Python 3.11+ using CODEX_SETUP_PYTHON' >&2
exit 2
