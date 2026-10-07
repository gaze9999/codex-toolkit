"""Preview or register Workspace Inspection in Codex without changing other settings."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from .service import WorkspaceInspectionService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--config", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml")
    parser.add_argument("--read-root", type=Path, action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    executable = args.python.expanduser().resolve(strict=True)
    config = args.config.expanduser().resolve(strict=True)
    service = WorkspaceInspectionService(args.read_root)
    subprocess.run(
        [str(executable), "-I", "-B", "-c", "import mcp; from workspace_inspection_mcp.core import load_core; load_core(); from workspace_inspection_mcp.server import load_mcp_dependencies; load_mcp_dependencies()"],
        check=True,
    )
    arguments = ["-I", "-B", "-m", "workspace_inspection_mcp.server"]
    for root in service.read_roots:
        arguments.extend(("--read-root", str(root)))
    section = "[mcp_servers.workspace_inspection]\n"
    section += "command = " + json.dumps(str(executable), ensure_ascii=False) + "\n"
    section += "args = " + json.dumps(arguments, ensure_ascii=False) + "\n"
    section += 'enabled = true\nstartup_timeout_sec = 30\ntool_timeout_sec = 120\nenabled_tools = ["workspace_status", "validation_evidence", "compare_environment"]\n'
    before = config.read_bytes()
    text = before.decode("utf-8-sig")
    match = re.search(r"(?m)^\[mcp_servers\.workspace_inspection\][ \t]*\r?$", text)
    if match:
        following = re.search(r"(?m)^\[", text[match.end():])
        end = match.end() + following.start() if following else len(text)
        text = text[:match.start()] + section + "\n" + text[end:]
    else:
        text = text.rstrip() + "\n\n" + section
    parsed = tomllib.loads(text)
    original = tomllib.loads(before.decode("utf-8-sig"))
    if parsed == original:
        print(json.dumps({"status": "unchanged", "config": str(config)}, ensure_ascii=False))
        return 0
    old_servers = original.get("mcp_servers", {}).copy()
    old_servers.pop("workspace_inspection", None)
    other_servers = parsed.get("mcp_servers", {}).copy()
    other_servers.pop("workspace_inspection", None)
    if other_servers != old_servers or {key: value for key, value in parsed.items() if key != "mcp_servers"} != {key: value for key, value in original.items() if key != "mcp_servers"}:
        raise ValueError("Unrelated settings changed")
    if not args.apply:
        print(json.dumps({"status": "preview", "server": parsed["mcp_servers"]["workspace_inspection"]}, ensure_ascii=False))
        return 0
    backup = config.with_name(config.name + ".before-workspace-inspection-" + uuid.uuid4().hex[:8] + ".bak")
    with backup.open("xb") as handle:
        handle.write(before)
    after = (b"\xef\xbb\xbf" if before.startswith(b"\xef\xbb\xbf") else b"") + text.encode("utf-8")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=config.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(after)
            handle.flush()
            os.fsync(handle.fileno())
        if config.read_bytes() != before:
            raise ValueError("Config changed; inspect before retry")
        os.replace(temporary, config)
        temporary = None
        if config.read_bytes() != after:
            raise ValueError("Config readback mismatch; inspect backup")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(json.dumps({"status": "installed", "config": str(config), "backup": str(backup)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
