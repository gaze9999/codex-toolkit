#!/usr/bin/env python3
"""Bounded, advisory lifecycle hooks for Codex and Claude Code (Python 3.11+)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile

VERSION = "0.3.0"
EVENTS = ("SessionStart", "PostToolUse", "Stop")
MAX_INPUT = 2 * 1024 * 1024
MAX_DIFF = 8 * 1024 * 1024
MAX_TRANSCRIPT = 16 * 1024 * 1024
FILE_KEYS = ("file_path", "notebook_path", "path")
USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens")


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


def usage_counts(value):
    if not isinstance(value, dict):
        raise ValueError("Missing native usage counters")
    counts = {key: value.get(key) for key in USAGE_FIELDS}
    if any(type(number) is not int or number < 0 for number in counts.values()):
        raise ValueError("Invalid native usage counters")
    if counts["total_tokens"] != counts["input_tokens"] + counts["output_tokens"]:
        raise ValueError("Unsupported native total accounting")
    if counts["cached_input_tokens"] > counts["input_tokens"]:
        raise ValueError("Invalid cached input accounting")
    return counts


def transcript_usage(payload, transcript_root):
    """Read a bounded native receipt; incomplete or unfamiliar records stay silent."""
    session, turn = payload.get("session_id"), payload.get("turn_id")
    final_text = payload.get("last_assistant_message")
    name = payload.get("transcript_path")
    if not all(isinstance(value, str) and value for value in (session, turn, final_text, name)):
        return None
    path = Path(name)
    root = Path(transcript_root).resolve(strict=True)
    if not path.is_absolute() or path.suffix != ".jsonl":
        return None
    path = path.resolve(strict=True)
    if not path.is_relative_to(root):
        return None
    with path.open("rb") as stream:
        header = stream.readline(MAX_INPUT + 1)
        if len(header) > MAX_INPUT or not header.endswith(b"\n"):
            return None
        metadata = json.loads(header)
        if metadata.get("type") != "session_meta" or metadata.get("payload", {}).get("id") != session:
            return None
        size = os.fstat(stream.fileno()).st_size
        offset = max(0, size - MAX_TRANSCRIPT)
        stream.seek(offset)
        data = stream.read(MAX_TRANSCRIPT)
    if not data.endswith(b"\n"):
        return None
    if offset:
        data = data.partition(b"\n")[2]
    previous = None
    baseline = None
    latest = None
    active = False
    saw_turn = False
    final_seen = False
    final_usage = False
    for line in data.splitlines():
        # Skip prompt/tool records before JSON parsing and never retain message text.
        prefix = line[:256]
        event = (re.search(rb'"type"\s*:\s*"event_msg"', prefix)
                 and re.search(rb'"type"\s*:\s*"(task_started|token_count)"', prefix))
        assistant = re.search(rb'"type"\s*:\s*"response_item"', prefix) and re.search(rb'"role"\s*:\s*"assistant"', prefix)
        if not event and not assistant:
            continue
        if len(line) > MAX_INPUT:
            return None
        record = json.loads(line)
        item = record.get("payload", {})
        kind = item.get("type")
        if record.get("type") == "response_item":
            if active and kind == "message" and item.get("phase") == "final_answer":
                content = item.get("content", [])
                text = "".join(part.get("text", "") for part in content if part.get("type") == "output_text")
                final_seen = text == final_text
                final_usage = False
            continue
        if kind == "task_started":
            if active:
                return None  # A newer turn must not inherit the requested turn's usage.
            if item.get("turn_id") == turn:
                active = True
                baseline = previous
                if baseline is None:
                    if offset or saw_turn or metadata.get("payload", {}).get("forked_from_id"):
                        return None
                    baseline = dict.fromkeys(USAGE_FIELDS, 0)
                latest = baseline
            saw_turn = True
        elif kind == "token_count" and item.get("info") is not None:
            info = item["info"]
            current = usage_counts(info.get("total_token_usage"))
            if active:
                delta = {key: current[key] - latest[key] for key in USAGE_FIELDS}
                if any(number < 0 for number in delta.values()):
                    return None
                if current != latest:
                    # Missing intermediate receipts could otherwise undercount a turn.
                    if delta != usage_counts(info.get("last_token_usage")):
                        return None
                    latest = current
                    final_usage = final_seen
            previous = current
    if not active or not final_usage:
        return None
    return {key: latest[key] - baseline[key] for key in USAGE_FIELDS}


def usage_message(payload, policy, client, state_dir):
    if client != "codex" or policy.get("codex_token_usage") is not True or payload.get("stop_hook_active"):
        return None
    try:
        counts = transcript_usage(payload, policy["transcript_root"])
        if counts is None:
            return None
        key = digest((client + "\0" + payload["session_id"] + "\0" + payload["turn_id"]).encode())
        receipt = state_dir / ("usage-" + key + ".json")
        value = {"version": VERSION, "usage": counts}
        if receipt.exists() and json.loads(receipt.read_text(encoding="utf-8")) == value:
            return None
        atomic_write(receipt, json.dumps(value).encode())
        return (f"Codex 本輪用量: 總計 {counts['total_tokens']:,} tokens "
                f"(輸入 {counts['input_tokens']:,}, 輸出 {counts['output_tokens']:,}, "
                f"快取輸入 {counts['cached_input_tokens']:,})")
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None


def edited_dir(payload):
    """Return the directory of the file a tool changed, when the tool input names one."""
    tool = payload.get("tool_input")
    if not isinstance(tool, dict):
        return None
    for key in FILE_KEYS:
        value = tool.get(key)
        if isinstance(value, str) and Path(value).is_absolute():
            parent = Path(value).parent
            return parent if parent.is_dir() else None
    return None


def repo_root(git, directory):
    code, output = git_run(git, directory, "rev-parse", "--show-toplevel")
    return None if code else Path(os.fsdecode(output).strip()).resolve()


def touched_roots(state_dir, client, session):
    index = state_dir / ("roots-" + digest((client + "\0" + session).encode()) + ".json")
    try:
        known = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    except (ValueError, OSError):
        known = []
    return index, [item for item in known if isinstance(item, str)] if isinstance(known, list) else []


def hook_roots(payload, policy, client, state_dir):
    """Select the repositories an event covers; edits record their repository for the session's Stop."""
    event, cwd = payload.get("hook_event_name"), payload.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute() or not Path(cwd).is_dir():
        raise ValueError("Hook cwd must be an existing absolute directory")
    session = payload.get("session_id")
    if not isinstance(session, str) or not session:
        raise ValueError("Hook session_id is required")
    git = policy["git"]
    if event == "PostToolUse":
        root = repo_root(git, edited_dir(payload) or cwd)
        if root is None:
            return []
        index, known = touched_roots(state_dir, client, session)
        if str(root) not in known:
            atomic_write(index, json.dumps([*known, str(root)]).encode())
        return [root]
    roots = [root] if (root := repo_root(git, cwd)) else []
    if event == "Stop":
        known = touched_roots(state_dir, client, session)[1]
        roots += [Path(item) for item in known if Path(item) not in roots and Path(item).is_dir()]
    return roots


def handle(payload, policy, client, state_dir):
    if payload.get("hook_event_name") not in EVENTS:
        raise ValueError("Unsupported lifecycle event")
    roots = hook_roots(payload, policy, client, state_dir)
    result = workspace_event(payload, policy, client, state_dir, roots)
    if policy.get("project_checks") and roots:
        module = runpy.run_path(str(Path(__file__).with_name("project_checks.py")))
        try:
            message = module["lifecycle"](payload, policy, client, state_dir, roots)
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            message = "Project checks unavailable; use the maintained project check CLI"
        if message:
            result["systemMessage"] = "\n".join(filter(None, (result.get("systemMessage"), message)))
    if payload.get("hook_event_name") == "Stop":
        message = usage_message(payload, policy, client, state_dir)
        if message:
            result["systemMessage"] = "\n".join(filter(None, (result.get("systemMessage"), message)))
    return result


def workspace_event(payload, policy, client, state_dir, roots):
    event = payload.get("hook_event_name")
    if event == "Stop" and payload.get("stop_hook_active"):
        return {}
    git, session = policy["git"], payload["session_id"]
    if event == "SessionStart":
        return session_start(payload, policy, client, state_dir, roots[0] if roots else None)
    if event == "PostToolUse":
        return post_tool(git, root_state(state_dir, client, roots[0], session)) if roots else {}
    cwd_root = roots[0] if roots and repo_root(git, payload["cwd"]) == roots[0] else None
    notes = []
    for root in roots:
        reasons = stop_reasons(git, root_state(state_dir, client, root, session))
        if reasons:
            label = "" if root == cwd_root else root.name + ": "
            notes.append(label + "; ".join(reasons))
    if notes:
        return {"systemMessage": "Hook evidence: " + " | ".join(notes) + ". " + policy["stop_note"]}
    return {}


def root_state(state_dir, client, root, session):
    state = state_dir / (digest((client + "\0" + str(root) + "\0" + session).encode()) + ".json")
    try:
        previous = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {}
    except (ValueError, OSError):
        previous = {}
    return root, state, previous


def session_start(payload, policy, client, state_dir, root):
    git = policy["git"]
    if root is None:
        root, label = Path(payload["cwd"]).resolve(), "not a Git repository"
    else:
        code, branch = git_run(git, root, "symbolic-ref", "--quiet", "--short", "HEAD")
        label = branch.decode("utf-8", errors="replace").strip() if code == 0 else "detached/unborn"
    _, state, previous = root_state(state_dir, client, root, payload["session_id"])
    entries = [name for name in policy["entries"] if (root / name).is_file()]
    message = f"Workspace: {root}\nBranch: {label}\nExisting entrypoints: {', '.join(entries) or 'none found'}"
    message += "\n" + policy["start_note"]
    message += "\nOperations: " + policy["operations"]
    token = digest(message.encode())
    if previous.get("route") == token and payload.get("source") != "compact":
        return {}
    previous["route"] = token
    atomic_write(state, json.dumps(previous).encode())
    return context("SessionStart", message)


def post_tool(git, target):
    root, state, previous = target
    revision, changed, _, base = snapshot(git, root)
    if not changed or previous.get("checked") == revision:
        return {}
    code, _ = git_run(git, root, "diff", "--no-ext-diff", "--no-textconv", "--check", *base, "--")
    if base == ["--cached"]:
        unstaged_code, _ = git_run(git, root, "diff", "--no-ext-diff", "--no-textconv", "--check", "--")
        code = code or unstaged_code
    if snapshot(git, root)[0] != revision:
        return context("PostToolUse", "Files changed during the whitespace check; receipt deferred until the next event")
    previous.update(checked=revision, check_exit=code, check="git diff --check (tracked files only)")
    atomic_write(state, json.dumps(previous).encode())
    if code:
        return context("PostToolUse", f"git diff --check found a tracked-file issue in {root.name}; run that command for locations")
    return {}


def stop_reasons(git, target):
    root, state, previous = target
    revision, changed, untracked, _ = snapshot(git, root)
    if not changed and not untracked or previous.get("reported") == revision:
        return []
    reasons = []
    if changed and previous.get("checked") != revision:
        reasons.append("tracked changes have no current whitespace-check receipt")
    elif changed and previous.get("check_exit"):
        reasons.append("tracked whitespace check failed")
    if untracked:
        reasons.append("untracked files require the project's selected checks")
    previous["reported"] = revision
    atomic_write(state, json.dumps(previous).encode())
    return reasons


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
