#!/usr/bin/env python3
"""Preview or install selected Codex/Claude hooks, preserving independent settings."""

from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import sys
import uuid

from agent_hooks import VERSION, atomic_write, digest
from install_global_agents import check_target

EVENTS = {"SessionStart": "startup|resume|clear|compact|fork", "PostToolUse": "^(Edit|Write|MultiEdit|apply_patch)$", "Stop": None}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def read_json(path):
    value = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def validate_profile(value):
    if set(value) != {"schema_version", "entries", "start_note", "stop_note"} or value["schema_version"] != 1:
        raise ValueError("Unsupported hook profile")
    entries = value["entries"]
    if not isinstance(entries, list) or len(entries) > 12:
        raise ValueError("Profile entries must contain at most 12 relative paths")
    for name in entries:
        if not isinstance(name, str) or not name or "\\" in name or ":" in name or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
            raise ValueError("Hook entrypoints must be relative paths inside the project")
    for key in ("start_note", "stop_note"):
        if not isinstance(value[key], str) or len(value[key]) > 400:
            raise ValueError("Hook notes must be strings of at most 400 characters")


def handlers(client, executable, runner, policy, state, platform):
    argv = [str(executable), "-I", "-B", str(runner), "--client", client, "--policy", str(policy), "--state-dir", str(state)]
    if client == "claude":
        handler = {"type": "command", "command": argv[0], "args": argv[1:], "timeout": 20}
    elif platform == "win32":
        quoted = "& " + " ".join("'" + part.replace("'", "''") + "'" for part in argv)
        command = "powershell.exe -NoProfile -NonInteractive -EncodedCommand " + base64.b64encode(quoted.encode("utf-16-le")).decode()
        handler = {"type": "command", "command": command, "commandWindows": command, "timeout": 20}
    else:
        handler = {"type": "command", "command": shlex.join(argv), "timeout": 20}
    groups = {}
    for event, matcher in EVENTS.items():
        item = copy.deepcopy(handler)
        if client == "codex" and event in ("SessionStart", "PostToolUse"):
            item["additionalContextLimit"] = 600
        group = {"hooks": [item]}
        if matcher:
            group["matcher"] = matcher
        groups[event] = group
    return groups


def plan(client, home, profile, operations, executable, git, platform):
    config = home / ("hooks.json" if client == "codex" else "settings.json")
    managed = home / "managed-agent-hooks"
    manifest = managed / "manifest.json"
    for path in (config, manifest):
        check_target(path, home)
    original = config.read_bytes() if config.exists() else None
    value = read_json(config)
    prior = read_json(manifest)
    policy = dict(profile, operations=str(operations), git=str(git))
    runner_bytes = Path(__file__).with_name("agent_hooks.py").read_bytes()
    policy_bytes = encoded(policy)
    bundle = managed / (VERSION + "-" + digest(runner_bytes + policy_bytes)[:16])
    runner, settings = bundle / "agent_hooks.py", bundle / "policy.json"
    groups = handlers(client, executable, runner, settings, managed / "state", platform)
    hooks = value.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"hooks must be an object: {config}")
    for event, old_group in prior.get("groups", {}).items():
        existing = hooks.get(event, [])
        if not isinstance(existing, list) or existing.count(old_group) != 1:
            raise ValueError(f"Managed hook changed locally; reconcile {client} {event} before installing")
        existing.remove(old_group)
    for event, group in groups.items():
        existing = hooks.setdefault(event, [])
        if not isinstance(existing, list):
            raise ValueError(f"Hook event must be an array: {event}")
        if group in existing:
            raise ValueError("An unowned identical hook exists; review ownership before installing")
        existing.append(group)
    data = original if original is not None and read_json(config) == value else encoded(value)
    files = {runner: runner_bytes, settings: policy_bytes,
             manifest: encoded({"version": VERSION, "groups": groups, "bundle": bundle.name}), config: data}
    expected = {}
    for path in files:
        check_target(path, home)
        expected[path] = path.read_bytes() if path.exists() else None
        if path in (runner, settings) and expected[path] not in (None, files[path]):
            raise ValueError(f"Installed immutable bundle differs: {path}")
    return files, expected


def apply_plan(files, expected, home):
    changes = {path: data for path, data in files.items() if expected[path] != data}
    if not changes:
        return
    backup = home / "managed-agent-hooks" / "backups" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    for path in changes:
        check_target(path, home)
        current = path.read_bytes() if path.exists() else None
        if current != expected[path]:
            raise ValueError(f"Destination changed after preview: {path}")
    written = []
    try:
        for path, data in changes.items():
            current = path.read_bytes() if path.exists() else None
            if current != expected[path]:
                raise ValueError(f"Destination changed during installation: {path}")
            if expected[path] is not None:
                target = backup / path.relative_to(home)
                check_target(target, home)
                atomic_write(target, expected[path])
                if target.read_bytes() != expected[path]:
                    raise ValueError("Backup verification failed")
            atomic_write(path, data)
            written.append(path)
            if path.read_bytes() != data:
                raise ValueError(f"Installed bytes differ: {path}")
    except (OSError, ValueError):
        for path in reversed(written):
            if path.read_bytes() == changes[path]:
                if expected[path] is None:
                    path.unlink()
                else:
                    atomic_write(path, expected[path])
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("codex", "claude"), action="append", required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--operations", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"))
    parser.add_argument("--claude-home", type=Path, default=Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        profile = read_json(args.profile)
        validate_profile(profile)
        operations = args.operations.expanduser().resolve(strict=True)
        if not operations.is_file():
            raise ValueError("Operations must be a maintained reference file")
        git = shutil.which("git")
        if not git:
            raise ValueError("Git is required")
        plans = []
        homes = set()
        for client in dict.fromkeys(args.client):
            home = getattr(args, client + "_home").expanduser().absolute()
            if home in homes or home == Path(home.anchor) or home == Path.home():
                raise ValueError("Use distinct client configuration directories")
            homes.add(home)
            files, expected = plan(client, home, profile, operations, Path(sys.executable), Path(git), sys.platform)
            plans.append((home, files, expected))
        pending = False
        for home, files, expected in plans:
            for path, data in files.items():
                changed = data != expected[path]
                pending |= changed
                print(("UPDATE " if changed else "CURRENT ") + str(path))
            if args.apply:
                apply_plan(files, expected, home)
        return 0 if args.apply or not pending else 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
