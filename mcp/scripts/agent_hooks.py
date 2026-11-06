#!/usr/bin/env python3
"""Bounded, advisory lifecycle hooks for Codex and Claude Code (Python 3.11+)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile

VERSION = "0.5.0"
EVENTS = ("SessionStart", "PreToolUse", "PostToolUse", "SubagentStart", "Stop", "SubagentStop")
MAX_INPUT = 2 * 1024 * 1024
MAX_DIFF = 8 * 1024 * 1024
MAX_TRANSCRIPT = 16 * 1024 * 1024
FILE_KEYS = ("file_path", "notebook_path", "path")
USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens")
MAX_REPLY = 256 * 1024
REPLY_LOCATIONS = 20
REPLY_CONTEXT = 12
# Fullwidth and CJK punctuation plus fullwidth ASCII forms; the enumeration comma and ideographic marks stay allowed.
FULLWIDTH = re.compile("[‘’“”　。-〄〈-〿！-･]")
# Code, inline code and URLs are preserved syntax and are not offered for review.
PRESERVED = re.compile(r"```.*?(?:```|\Z)|~~~.*?(?:~~~|\Z)|`[^`\n]*`|https?://\S+", re.S)
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch")
SHELL_SEPARATOR = re.compile(r"&&|\|\||[;|\n]")
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Move to: (.+)$", re.M)
AI_TRAILER = re.compile(r"co-authored-by:[^\n]*(?:claude|codex|chatgpt|openai|anthropic|copilot|\bgpt)", re.I)
FORCE_PUSH = ("-f", "--force", "--force-with-lease", "--force-if-includes", "--mirror", "--delete", "-d", "--prune")


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


def fullwidth_findings(text):
    """Select fullwidth punctuation outside code and URLs; each finding keeps its line, column and nearby text."""
    masked = PRESERVED.sub(lambda match: re.sub(r"[^\n]", " ", match.group()), text)
    findings = []
    for match in FULLWIDTH.finditer(masked):
        start = match.start()
        line = text.count("\n", 0, start) + 1
        column = start - (text.rfind("\n", 0, start) + 1) + 1
        before = text[max(0, start - REPLY_CONTEXT):start].rpartition("\n")[2]
        after = text[start + 1:start + 1 + REPLY_CONTEXT].partition("\n")[0]
        findings.append((line, column, match.group(), before + "[[" + match.group() + "]]" + after))
    return findings


def reply_review(payload, policy, client, state_dir):
    """Ask the agent once to keep or fix each fullwidth candidate; the receipt keeps only a digest and a count."""
    text = payload.get("last_assistant_message")
    if policy.get("reply_punctuation") is not True or payload.get("stop_hook_active"):
        return {}
    if not isinstance(text, str) or not text.strip():
        return {}
    event = payload.get("hook_event_name")
    agent = payload.get("agent_type") or payload.get("agent_id") or ""
    data = text.encode("utf-8")
    key = digest("\0".join((client, payload["session_id"], event, str(payload.get("agent_id", "")), digest(data))).encode())
    receipt = state_dir / ("reply-" + key + ".json")
    if receipt.exists():
        return {}
    if len(data) > MAX_REPLY:
        atomic_write(receipt, json.dumps({"version": VERSION, "checked": False, "count": 0}).encode())
        label = f"子代理 {agent} " if event == "SubagentStop" else ""
        return {"systemMessage": f"{label}最終回覆超過 {MAX_REPLY // 1024} KiB, 未檢查全形標點"}
    findings = fullwidth_findings(text)
    atomic_write(receipt, json.dumps({"version": VERSION, "checked": True, "count": len(findings)}).encode())
    if not findings:
        return {}
    items = "\n".join(f"- {line}:{column} U+{ord(mark):04X} near: {near}" for line, column, mark, near in findings[:REPLY_LOCATIONS])
    more = f"\n- {len(findings) - REPLY_LOCATIONS} more candidates follow the same rule" if len(findings) > REPLY_LOCATIONS else ""
    owner = f" from subagent {agent}" if event == "SubagentStop" else ""
    reason = (f"Fullwidth punctuation review: {len(findings)} candidate(s) in the final reply{owner}, marked [[ ]]. "
              "Keep a mark only inside preserved originals: quotations, official names, code or other-language syntax. "
              "Otherwise apply the Global punctuation rule. If anything changes, send only the corrected lines; "
              "if every mark stays, reply with one short line saying so. Do not repeat the whole reply.\n" + items + more)
    return {"decision": "block", "reason": reason}


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


def git_value(git, root, *args):
    code, output = git_run(git, root, *args)
    return os.fsdecode(output).strip() if code == 0 else ""


def repository_identity(git, root):
    """Normalize the origin URL; repositories without an origin have no identity."""
    origin = git_value(git, root, "remote", "get-url", "origin")
    return origin.removesuffix(".git").replace("git@github.com:", "https://github.com/").lower() if origin else ""


def personal_repository(git, root, rule):
    identity = repository_identity(git, root)
    return bool(identity) and any(identity.startswith(owner.rstrip("/").lower() + "/") for owner in rule["owners"])


def existing_directory(path):
    for candidate in (path, *path.parents):
        if candidate.is_dir():
            return candidate
    return None


def shell_git(command, cwd):
    """Yield (directory, subcommand, arguments) for Git calls in a shell line; cd and -C select the directory."""
    directory = cwd
    for segment in SHELL_SEPARATOR.split(command):
        try:
            words = shlex.split(segment)
        except ValueError:
            words = segment.split()
        while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
            words = words[1:]
        if len(words) > 1 and words[0] == "cd":
            directory = directory / Path(words[1]).expanduser()
            continue
        if not words or Path(words[0]).name.lower() not in ("git", "git.exe"):
            continue
        target, arguments = directory, words[1:]
        while arguments and arguments[0].startswith("-"):
            option = arguments.pop(0)
            if option == "-C" and arguments:
                target = target / Path(arguments.pop(0)).expanduser()
            elif option in ("-c", "--git-dir", "--work-tree", "--namespace") and arguments:
                arguments.pop(0)
        if arguments:
            yield target, arguments[0], arguments[1:]


def commit_identity_reason(git, directory, rule):
    """Personal repositories commit as the personal identity; other repositories need their own local identity."""
    base = existing_directory(directory)
    root = repo_root(git, base) if base else None
    if root is None:
        return None
    if personal_repository(git, root, rule):
        email = git_value(git, root, "config", "user.email")
        if email != rule["email"]:
            return f"{root.name} is a personal repository but commits as {email or 'no email'}; set the personal identity in this repository"
        return None
    if not git_value(git, root, "config", "--local", "user.email"):
        return (f"{root.name} is not a personal repository and has no repository-local user.email; "
                "set the owner's identity there instead of inheriting the personal global identity")
    return None


def history_reason(subcommand, arguments):
    if subcommand == "push" and any(argument in FORCE_PUSH or argument.startswith("--force") or
                                    (argument[:1] in "+:" and len(argument) > 1) for argument in arguments):
        return "git push would force, mirror or delete remote refs; published history and Tags stay fixed"
    if subcommand == "tag" and any(argument in ("-d", "--delete", "-f", "--force") for argument in arguments):
        return "git tag would delete or move a Tag; published Tags stay fixed"
    if subcommand in ("filter-branch", "filter-repo"):
        return f"git {subcommand} rewrites history and needs separate authorization"
    return None


def edited_paths(payload, cwd):
    tool = payload.get("tool_input")
    if not isinstance(tool, dict):
        return []
    if payload.get("tool_name") == "apply_patch":
        patch = tool.get("command") if isinstance(tool.get("command"), str) else tool.get("input", "")
        names = [first or second for first, second in PATCH_FILE.findall(patch if isinstance(patch, str) else "")]
    else:
        names = [tool[key] for key in FILE_KEYS if isinstance(tool.get(key), str)]
    return [path if path.is_absolute() else cwd / path for path in (Path(name.strip()).expanduser() for name in names)]


def generated_reason(git, path, generated):
    directory = existing_directory(path.parent)
    root = repo_root(git, directory) if directory else None
    if root is None:
        return None
    identity = repository_identity(git, root)
    for rule in generated:
        if identity != rule["repository"].removesuffix(".git").lower():
            continue
        try:
            name = PurePosixPath(path.resolve().relative_to(root).as_posix())
        except ValueError:
            return None
        if any(name.match(pattern) or str(name) == pattern for pattern in rule.get("allow", [])):
            return None
        return f"{root.name}/{name} is generated output; change its canonical source and regenerate"
    return None


def guard(payload, policy, client):
    """Stop selected Git and edit operations before they run; other tool calls pass without output.

    History rewrites ask the user in Claude's native dialog; Codex does not support "ask" and would run the
    call, so it denies and the user runs the command or disables the hook natively for that change.
    """
    rules = policy.get("guards")
    tool = payload.get("tool_input")
    if not isinstance(rules, dict) or not isinstance(tool, dict):
        return {}
    git, cwd = policy["git"], Path(payload["cwd"])
    reasons, history = [], []
    if payload.get("tool_name") == "Bash" and isinstance(tool.get("command"), str):
        command = tool["command"]
        calls = list(shell_git(command, cwd)) if "git" in command else []
        if rules.get("ai_coauthor") and AI_TRAILER.search(command) and any(sub == "commit" for _, sub, _ in calls):
            reasons.append("the commit message carries an AI co-author trailer; keep human authorship only")
        for directory, subcommand, arguments in calls:
            reason = history_reason(subcommand, arguments) if rules.get("history") else None
            if reason and reason not in history:
                history.append(reason)
            reason = commit_identity_reason(git, directory, rules["identity"]) if subcommand == "commit" and rules.get("identity") else None
            if reason and reason not in reasons:
                reasons.append(reason)
    elif payload.get("tool_name") in EDIT_TOOLS and rules.get("generated"):
        for path in edited_paths(payload, cwd):
            reason = generated_reason(git, path, rules["generated"])
            if reason and reason not in reasons:
                reasons.append(reason)
    if not reasons and not history:
        return {}
    if not reasons and client == "claude":
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                       "permissionDecisionReason": "Agent hook: " + "; ".join(history) + "; approve only if you authorized it"}}
    if history and client == "codex":
        history.append("ask the user to run it or to disable this hook in /hooks for that change")
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": "Blocked by agent hook: " + "; ".join(reasons + history)}}


def environment_line(policy, root):
    system = platform.system()
    release = {"Darwin": "macOS " + platform.mac_ver()[0], "Windows": "Windows " + platform.release()}.get(system, system + " " + platform.release())
    python = next((name for name in ("python3", "python", "py") if shutil.which(name)), "unavailable")
    line = f"Environment: {release.strip()} {platform.machine()}; Python {platform.python_version()} via '{python}'"
    rule = (policy.get("guards") or {}).get("identity")
    if rule and root is not None:
        line += "; repository: " + ("personal" if personal_repository(policy["git"], root, rule) else "not personal")
    return line


def require_session(payload):
    if not isinstance(payload.get("session_id"), str) or not payload["session_id"]:
        raise ValueError("Hook session_id is required")


def handle(payload, policy, client, state_dir):
    event = payload.get("hook_event_name")
    if event not in EVENTS:
        raise ValueError("Unsupported lifecycle event")
    if event in ("PreToolUse", "SubagentStart", "SubagentStop"):
        require_session(payload)
    if event == "PreToolUse":
        cwd = payload.get("cwd")
        if not isinstance(cwd, str) or not Path(cwd).is_absolute() or not Path(cwd).is_dir():
            raise ValueError("Hook cwd must be an existing absolute directory")
        return guard(payload, policy, client)
    if event == "SubagentStart":
        note = policy.get("subagent_note")
        return context("SubagentStart", note) if note else {}
    if event == "SubagentStop":
        # A child reply receives only the final-text review; repository evidence stays with the parent's Stop.
        return reply_review(payload, policy, client, state_dir)
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
    if event == "Stop":
        review = reply_review(payload, policy, client, state_dir)
        for message in (review.pop("systemMessage", None), usage_message(payload, policy, client, state_dir)):
            if message:
                result["systemMessage"] = "\n".join(filter(None, (result.get("systemMessage"), message)))
        result.update(review)
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
    if policy.get("session_environment"):
        message += "\n" + environment_line(policy, None if label == "not a Git repository" else root)
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
