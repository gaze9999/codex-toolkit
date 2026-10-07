#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
if [ "$#" -gt 0 ] && [ "${1#--}" = "$1" ]; then
    TOOL=$1
    shift
    set -- --tool "$TOOL" "$@"
fi
if [ "$#" -eq 0 ]; then set -- --guided; fi
for candidate in "${CODEX_SETUP_PYTHON:-}" python3 python3.13 python; do
    [ -n "$candidate" ] || continue
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
        exec "$candidate" -B "$ROOT_DIR/mcp/scripts/uninstall_mcp.py" "$@"
    fi
done
echo 'Select an existing Python 3.11+ using CODEX_SETUP_PYTHON, no packages were installed or removed' >&2
exit 2
