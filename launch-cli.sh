#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ACTION=${1:---help}
if [ "$#" -gt 0 ]; then shift; fi
case "$ACTION" in
    --help|-h|--list) printf '%s\n' 'Usage: sh launch-cli.sh CATEGORY [OPTIONS]' 'Categories: agents, skills, plugins, mcp' 'agents: global / desktop / subagent-profile' 'skills: NAME [--apply]' 'plugins: --list / NAME preview; install through Codex' 'mcp: TOOL / --list' 'Other actions: tool, bootstrap, check, update, uninstall, desktop, audit' 'See docs/setup/cli.md'; exit 0 ;;
    mcp|tool|uninstall)
        if [ "${1:-}" = '--help' ] || [ "${1:-}" = '-h' ]; then
            case "$ACTION" in uninstall) SCRIPT=uninstall_mcp.py ;; *) SCRIPT=install_development_tool.py ;; esac
        else
            case "$ACTION" in
                mcp) exec sh "$ROOT_DIR/mcp/scripts/launch/install-mcp.sh" "$@" ;;
                tool) exec sh "$ROOT_DIR/mcp/scripts/launch/install-development-tool.sh" "$@" ;;
                uninstall) exec sh "$ROOT_DIR/mcp/scripts/launch/uninstall-mcp.sh" "$@" ;;
            esac
        fi ;;
    bootstrap) SCRIPT=bootstrap_mcp.py ;;
    check) SCRIPT=check_development_tools.py ;;
    update) SCRIPT=update_development_tool.py ;;
    agents|skills|plugins) SCRIPT=manage_categories.py; set -- "$ACTION" "$@" ;;
    desktop) SCRIPT=render_desktop_settings.py ;;
    audit) SCRIPT=audit_skills.py ;;
    *) echo "Unknown action: $ACTION, use --help" >&2; exit 2 ;;
esac
if [ -n "${CODEX_SETUP_PYTHON:-}" ]; then
    "$CODEX_SETUP_PYTHON" -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 2)' || exit 2
    exec "$CODEX_SETUP_PYTHON" -X utf8 -B "$ROOT_DIR/mcp/scripts/$SCRIPT" "$@"
fi
for candidate in python3 python3.13 python; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 2)' >/dev/null 2>&1; then
        exec "$candidate" -X utf8 -B "$ROOT_DIR/mcp/scripts/$SCRIPT" "$@"
    fi
done
echo 'Select an existing Python 3.11+ using CODEX_SETUP_PYTHON' >&2
exit 2
