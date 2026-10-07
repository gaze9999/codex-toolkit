#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
TOOL=${1:-}
case "$TOOL" in ""|-*|*[!a-z0-9-]*) echo "Select one tool name from the current catalog" >&2; exit 2 ;; esac
shift
case "$(uname -s)" in Darwin) SYSTEM=macos ;; Linux) SYSTEM=linux ;; *) echo 'Use launch-cli.cmd tool TOOL on Windows' >&2; exit 2 ;; esac
APPLY=no
YES=no
GUIDED=no
INTERFACE=native
EXPECT_INTERFACE=no
for arg in "$@"; do
    if [ "$EXPECT_INTERFACE" = yes ]; then INTERFACE=$arg; EXPECT_INTERFACE=no; continue; fi
    case "$arg" in --apply) APPLY=yes ;; --yes) YES=yes ;; --guided) GUIDED=yes ;; --interface) EXPECT_INTERFACE=yes ;; --interface=*) INTERFACE=${arg#--interface=} ;; --tool|--tool=*) echo 'Select one tool using the first argument only' >&2; exit 2 ;; esac
done
case "$INTERFACE" in native|mcp) ;; *) echo 'Interface must be native or mcp' >&2; exit 2 ;; esac
case "$TOOL:$SYSTEM:$INTERFACE" in repoprompt:linux:*|cmux:linux:*|conductor:linux:native) echo "$TOOL does not support this platform/interface; nothing was installed" >&2; exit 2 ;; esac
find_python() {
    for candidate in "${CODEX_SETUP_PYTHON:-}" python3 python3.13 python; do
        [ -n "$candidate" ] || continue
        command -v "$candidate" >/dev/null 2>&1 || continue
        if "$candidate" -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}
RUNTIME=$(find_python || true)
if [ -z "$RUNTIME" ]; then
    if [ -n "${CODEX_SETUP_PYTHON:-}" ]; then echo 'Selected Python must be working Python 3.11+' >&2; exit 2; fi
    if command -v brew >/dev/null 2>&1; then
        echo "Missing Python 3.11+. Source: https://www.python.org/ via Homebrew python@3.13; scope: Homebrew prefix; purpose: selected $TOOL installer"
        MANAGER=brew
    elif [ "$SYSTEM" = linux ] && command -v apt-get >/dev/null 2>&1; then
        echo "Missing Python 3.11+. Source: configured distribution repositories, python3; scope: system, sudo required; purpose: selected $TOOL installer"
        MANAGER=apt-get
    elif [ "$SYSTEM" = linux ] && command -v dnf >/dev/null 2>&1; then
        echo "Missing Python 3.11+. Source: configured distribution repositories, python3; scope: system, sudo required; purpose: selected $TOOL installer"
        MANAGER=dnf
    else
        echo 'Install Python 3.11+ from an approved source, then rerun the same tool' >&2; exit 2
    fi
    [ "$APPLY" = yes ] || [ "$GUIDED" = yes ] || { echo 'Rerun with --apply to confirm the Python bootstrap'; exit 1; }
    if [ "$YES" != yes ]; then
        [ -t 0 ] || { echo 'Interactive confirmation or explicitly authorized --yes required' >&2; exit 2; }
        printf 'Install Python for this selected tool? [y/N] '
        read -r answer
        case "$answer" in y|yes) ;; *) exit 0 ;; esac
    fi
    case "$MANAGER" in
        brew) brew install python@3.13 ;;
        apt-get) sudo apt-get install -y python3 ;;
        dnf) sudo dnf install -y python3 ;;
    esac
    RUNTIME=$(find_python || true)
    [ -n "$RUNTIME" ] || { echo 'Installed Python is below 3.11 or not visible; use an approved newer runtime' >&2; exit 2; }
fi
exec "$RUNTIME" -B "$ROOT_DIR/mcp/scripts/install_development_tool.py" --tool "$TOOL" "$@"
