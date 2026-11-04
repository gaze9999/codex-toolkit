#!/usr/bin/env python3
"""Bounded, advisory lifecycle hooks for Codex and Claude Code (Python 3.11+)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

VERSION = "0.1.0"
EVENTS = ("SessionStart", "PostToolUse", "Stop")
MAX_INPUT = 2 * 1024 * 1024
MAX_DIFF = 8 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".hook-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def git_run(git, cwd, *args):
    # Disable repository-defined diff drivers and optional index writes.
    with tempfile.TemporaryFile() as output:
        result = subprocess.run(
            [git, "--no-optional-locks", "-c", "core.fsmonitor=false", *args],
            cwd=cwd, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.DEVNULL,
            timeout=2, check=False,
        )
        output.seek(0)
        data = output.read(MAX_DIFF + 1)
    if len(data) > MAX_DIFF:
        raise ValueError("Git output exceeds the hook limit; use the project verification command")
    return result.returncode, data


def snapshot(git, root):
    code, head = git_run(git, root, "rev-parse", "--verify", "HEAD")
    base = ["HEAD"] if code == 0 else ["--cached"]
    code, diff = git_run(git, root, "diff", "--no-ext-diff", "--no-textconv", "--binary", *base, "--")
    if code:
        raise ValueError("Cannot inspect the current Git diff")
    if base == ["--cached"]:
        code, unstaged = git_run(git, root, "diff", "--no-ext-diff", "--no-textconv", "--binary", "--")
        if code:
            raise ValueError("Cannot inspect the unstaged Git diff")
        diff += unstaged
    code, untracked = git_run(git, root, "ls-files", "--others", "--exclude-standard", "-z")
    if code:
        raise ValueError("Cannot inspect untracked file names")
    # Untracked contents are not inspected and cannot receive a passing receipt.
    return digest(head + diff + untracked), bool(diff), bool(untracked), base


def context(event, message):
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": message[:1600]}}


def handle(payload, policy, client, state_dir):
    event = payload.get("hook_event_name")
    if event not in EVENTS:
        raise ValueError("Unsupported lifecycle event")
    if event == "Stop" and payload.get("stop_hook_active"):
        return {}
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute() or not Path(cwd).is_dir():
        raise ValueError("Hook cwd must be an existing absolute directory")
    git = policy["git"]
    code, output = git_run(git, cwd, "rev-parse", "--show-toplevel")
    if code and event != "SessionStart":
        return {}
    root = Path(cwd).resolve() if code else Path(os.fsdecode(output).strip()).resolve()
    session = payload.get("session_id")
    if not isinstance(session, str) or not session:
        raise ValueError("Hook session_id is required")
    key = digest((client + "\0" + str(root) + "\0" + session).encode())
    state = state_dir / (key + ".json")
    try:
        previous = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {}
    except (ValueError, OSError):
        previous = {}
    if event == "SessionStart":
        entries = [name for name in policy["entries"] if (root / name).is_file()]
        code, branch = git_run(git, root, "symbolic-ref", "--quiet", "--short", "HEAD")
        label = branch.decode("utf-8", errors="replace").strip() if code == 0 else "detached/unborn"
        message = f"Workspace: {root}\nBranch: {label}\nExisting entrypoints: {', '.join(entries) or 'none found'}"
        message += "\n" + policy["start_note"]
        message += "\nOperations: " + policy["operations"]
        token = digest(message.encode())
        if previous.get("route") == token and payload.get("source") != "compact":
            return {}
        previous["route"] = token
        atomic_write(state, json.dumps(previous).encode())
        return context(event, message)
    revision, changed, untracked, base = snapshot(git, root)
    if event == "PostToolUse":
        if not changed or previous.get("checked") == revision:
            return {}
        code, _ = git_run(git, root, "diff", "--no-ext-diff", "--no-textconv", "--check", *base, "--")
        if base == ["--cached"]:
            unstaged_code, _ = git_run(git, root, "diff", "--no-ext-diff", "--no-textconv", "--check", "--")
            code = code or unstaged_code
        if snapshot(git, root)[0] != revision:
            return context(event, "Files changed during the whitespace check; receipt deferred until the next event")
        previous.update(checked=revision, check_exit=code, check="git diff --check (tracked files only)")
        atomic_write(state, json.dumps(previous).encode())
        if code:
            return context(event, "git diff --check found a tracked-file issue; run that command for locations")
        return {}
    if not changed and not untracked:
        return {}
    if previous.get("reported") == revision:
        return {}
    reasons = []
    if changed and previous.get("checked") != revision:
        reasons.append("tracked changes have no current whitespace-check receipt")
    elif changed and previous.get("check_exit"):
        reasons.append("tracked whitespace check failed")
    if untracked:
        reasons.append("untracked files require the project's selected checks")
    previous["reported"] = revision
    atomic_write(state, json.dumps(previous).encode())
    if reasons:
        return {"systemMessage": "Hook evidence: " + "; ".join(reasons) + ". " + policy["stop_note"]}
    return {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("codex", "claude"), required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ValueError("Hook input exceeds 2 MiB")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Hook input must be an object")
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        result = handle(payload, policy, args.client, args.state_dir)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        # The client retains this as a hook failure, without requesting continuation.
        print("Agent hook failed: " + type(error).__name__ + "; check the installed runtime and policy", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
