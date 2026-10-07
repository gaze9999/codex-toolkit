#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
if [ "$#" -gt 0 ] && [ "${1#--}" = "$1" ]; then
    TOOL=$1
    shift
    exec sh "$ROOT_DIR/mcp/scripts/launch/install-development-tool.sh" "$TOOL" --interface mcp --guided "$@"
fi
# Resolve an existing interpreter before showing the Python catalog menu
for candidate in "${CODEX_SETUP_PYTHON:-}" python3 python3.13 python; do
    [ -n "$candidate" ] || continue
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
        exec "$candidate" -B "$ROOT_DIR/mcp/scripts/install_development_tool.py" --guided --interface mcp "$@"
    fi
done
echo 'Python 3.11+ is missing. Select one tool first; its entry will preview and confirm the approved Python bootstrap'
if [ -t 0 ]; then
    printf 'Tool name (for example context7, playwright, rtk, notion; Enter to cancel): '
    read -r selected_tool
    [ -n "$selected_tool" ] || exit 0
    exec sh "$ROOT_DIR/mcp/scripts/launch/install-development-tool.sh" "$selected_tool" --interface mcp --guided "$@"
fi
echo 'See docs/tools/catalog.md and run: sh launch-cli.sh mcp TOOL --apply'
exit 1
