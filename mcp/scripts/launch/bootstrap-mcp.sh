#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
exec python3 -B "$ROOT_DIR/mcp/scripts/bootstrap_mcp.py" "$@"
