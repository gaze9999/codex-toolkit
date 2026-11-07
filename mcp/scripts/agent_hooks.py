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

VERSION = "0.8.0"
EVENTS = ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "SubagentStart", "PreCompact",
          "InstructionsLoaded", "ConfigChange", "Stop")
# Claude uses PreCompact stdout as plain-text summary instructions; every other event prints JSON.
TEXT_OUTPUT = "plainText"
DELIVERY = re.compile(r"^\s*(cpr|cpt|cp)\b", re.I)
CJK = re.compile("[㐀-鿿]")
KANA = re.compile("[぀-ヿ]")
LATIN = re.compile("[A-Za-z]{3}")
DOC_LINT_FILES = 5
DOC_SCAN_FILES = 50
MAX_DOC = 1024 * 1024
MAX_INPUT = 2 * 1024 * 1024
MAX_DIFF = 8 * 1024 * 1024
MAX_TRANSCRIPT = 16 * 1024 * 1024
FILE_KEYS = ("file_path", "notebook_path", "path")
USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens")
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch")
SHELL_DIRECTORY = ("cd", "chdir", "pushd", "set-location", "sl")
MD_TOKEN = re.compile(r"[^\s'\"`<>|;&()=,]+\.md\b", re.I)
SHELL_SEPARATOR = re.compile(r"&&|\|\||[;|\n]")
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Move to: (.+)$", re.M)
AI_TRAILER = re.compile(r"co-authored-by:[^\n]*(?:claude|codex|chatgpt|openai|anthropic|copilot|\bgpt)", re.I)


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


def guard(payload, policy):
    """Deny selected commits and generated-file edits before they run; other tool calls pass without output."""
    rules = policy.get("guards")
    tool = payload.get("tool_input")
    if not isinstance(rules, dict) or not isinstance(tool, dict):
        return {}
    git, cwd = policy["git"], Path(payload["cwd"])
    reasons = []
    if payload.get("tool_name") == "Bash" and isinstance(tool.get("command"), str):
        command = tool["command"]
        calls = list(shell_git(command, cwd)) if "git" in command else []
        if rules.get("ai_coauthor") and AI_TRAILER.search(command) and any(sub == "commit" for _, sub, _ in calls):
            reasons.append("the commit message carries an AI co-author trailer; keep human authorship only")
        for directory, subcommand, _ in calls:
            reason = commit_identity_reason(git, directory, rules["identity"]) if subcommand == "commit" and rules.get("identity") else None
            if reason and reason not in reasons:
                reasons.append(reason)
    elif payload.get("tool_name") in EDIT_TOOLS and rules.get("generated"):
        for path in edited_paths(payload, cwd):
            reason = generated_reason(git, path, rules["generated"])
            if reason and reason not in reasons:
                reasons.append(reason)
    if not reasons:
        return {}
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": "Blocked by agent hook: " + "; ".join(reasons)}}


def environment_line(policy, root):
    system = platform.system()
    release = {"Darwin": "macOS " + platform.mac_ver()[0], "Windows": "Windows " + platform.release()}.get(system, system + " " + platform.release())
    python = next((name for name in ("python3", "python", "py") if shutil.which(name)), "unavailable")
    line = f"Environment: {release.strip()} {platform.machine()}; Python {platform.python_version()} via '{python}'"
    rule = (policy.get("guards") or {}).get("identity")
    if rule and root is not None:
        line += "; repository: " + ("personal" if personal_repository(policy["git"], root, rule) else "not personal")
    return line


def data_root():
    """Mirror Toolkit's maintained tool data root so device paths never enter the profile."""
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        base = local if local.is_absolute() else Path.home() / "AppData/Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        xdg = Path(os.environ.get("XDG_DATA_HOME", ""))
        base = xdg if xdg.is_absolute() else Path.home() / ".local/share"
    return base / "codex-setup"


LINT_CONFIGS = {"zh-TW": "proofreading/zh-tw/.textlintrc.cjs", "ja": "proofreading/ja/.textlintrc.json",
                "en": "proofreading/en/english.textlintrc.cjs"}


def textlint_tools(policy):
    """Find the maintained npm prefix; an installer-recorded prefix covers clients whose app data is virtualized."""
    recorded = policy.get("npm_prefix")
    prefix = Path(recorded) if recorded else data_root() / "tools/npm"
    node = policy.get("node") or shutil.which("node")
    for modules in (prefix / "lib/node_modules", prefix / "node_modules"):
        runner = modules / "textlint/bin/textlint.js"
        if runner.is_file() and node:
            return node, runner, prefix
    return None


def doc_language(text):
    """Kana marks Japanese, other Han text zh-TW and remaining prose English."""
    if KANA.search(text):
        return "ja"
    if CJK.search(text):
        return "zh-TW"
    return "en" if LATIN.search(text) else None


def spelling(node, runner, prefix, path):
    """Return CSpell issue positions with the maintained English dictionary, or None when unavailable."""
    config = prefix / "proofreading/en/cspell.json"
    binary = runner.parents[2] / "cspell/bin.mjs"
    if not config.is_file() or not binary.is_file():
        return None
    result = subprocess.run([node, str(binary), "lint", "--no-progress", "--no-summary", "--no-color", "--config", str(config), str(path)],
                            cwd=path.parent, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=8, check=False)
    if result.returncode not in (0, 1) or len(result.stdout) > MAX_INPUT:
        raise ValueError("cspell failed")
    return re.findall(r":(\d+:\d+) - Unknown word", result.stdout.decode("utf-8", errors="replace"))


def doc_state(state_dir, client, session):
    path = state_dir / ("docs-" + digest((client + "\0" + session).encode()) + ".json")
    try:
        value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (ValueError, OSError):
        value = {}
    value = value if isinstance(value, dict) else {}
    for key in ("baseline", "files"):
        value[key] = value.get(key) if isinstance(value.get(key), dict) else {}
    value["roots"] = [item for item in value.get("roots", []) if isinstance(item, str)] if isinstance(value.get("roots"), list) else []
    return path, value


def native_path(word, base):
    """Resolve a shell word; Git Bash drive paths such as /d/work become D:/work on Windows."""
    word = word.strip().strip("'\"")
    if os.name == "nt" and (match := re.match(r"^/([A-Za-z])(/.*)?$", word)):
        word = match.group(1) + ":" + (match.group(2) or "/")
    path = Path(word).expanduser()
    return path if path.is_absolute() else base / path


def shell_targets(payload, cwd):
    """Return directories a shell command enters and Markdown paths it names; the command itself is never run."""
    tool = payload.get("tool_input")
    command = tool.get("command") if isinstance(tool, dict) else None
    if payload.get("tool_name") in EDIT_TOOLS or not isinstance(command, str) or len(command) > MAX_INPUT:
        return [], []
    directory, directories, files = cwd, [cwd], []
    for segment in SHELL_SEPARATOR.split(command):
        try:
            words = shlex.split(segment, posix=False)
        except ValueError:
            words = segment.split()
        words = [word.strip("'\"") for word in words]
        if words and words[0].lower() in SHELL_DIRECTORY:
            target = next((word for word in words[1:] if not word.startswith("-") and word.lower() != "/d"), None)
            if target:
                directory = native_path(target, directory)
                directories.append(directory)
            continue
        for index, word in enumerate(words[:-2]):
            if Path(word).name.lower() in ("git", "git.exe") and words[index + 1] == "-C":
                directories.append(native_path(words[index + 2], directory))
        files += [native_path(match, directory) for word in words for match in MD_TOKEN.findall(word)]
    return directories, files


def changed_docs(git, root):
    """List tracked and untracked Markdown changes under a repository; contents are read later."""
    code, _ = git_run(git, root, "rev-parse", "--verify", "HEAD")
    names = []
    for args in ((["diff", "--name-only", "-z", "HEAD", "--"] if code == 0 else ["diff", "--name-only", "-z", "--cached", "--"]),
                 ["diff", "--name-only", "-z", "--"], ["ls-files", "--others", "--exclude-standard", "-z"]):
        result, output = git_run(git, root, "-c", "core.quotepath=off", *args)
        if result:
            raise ValueError("Cannot list changed documents")
        names += [os.fsdecode(name) for name in output.split(b"\0") if name]
    paths = []
    for name in dict.fromkeys(names):
        path = (root / name).resolve()
        if path.suffix.lower() == ".md" and path.is_file() and path not in paths:
            paths.append(path)
    return paths[:DOC_SCAN_FILES]


def content_digest(path):
    data = path.read_bytes()
    return digest(data) if len(data) <= MAX_DOC else None


def lint_docs(paths, policy, client, session, state_dir, state):
    """Lint each Markdown content once; results stay in the per-turn document state for Stop."""
    tools = textlint_tools(policy)
    if tools is None:
        missing = state_dir / ("doc-missing-" + digest((client + "\0" + session).encode()) + ".json")
        if missing.exists():
            return []
        atomic_write(missing, json.dumps({"version": VERSION}).encode())
        return ["Doc lint skipped: install textlint with the maintained development tool installer"]
    node, runner, prefix = tools
    notes, linted = [], 0
    for path in paths:
        data = path.read_bytes()
        language = doc_language(data.decode("utf-8", errors="replace")) if len(data) <= MAX_DOC else None
        config = prefix / LINT_CONFIGS[language] if language else None
        if not config or not config.is_file():
            continue
        sha = digest(data)
        receipt = state_dir / ("doc-" + digest("\0".join((client, session, str(path), sha)).encode()) + ".json")
        if receipt.exists():
            try:
                count = json.loads(receipt.read_text(encoding="utf-8")).get("count", 0)
            except (ValueError, OSError, AttributeError):
                count = 0
            state["files"][str(path)] = [sha, count if type(count) is int else 0]
            continue
        if linted >= DOC_LINT_FILES:
            break
        linted += 1
        # Profile rule files are copied into this bundle and add to the shared language profile.
        extra = [part for name in policy.get("doc_lint_rules", {}).get(language, [])
                 if (rule := Path(__file__).parent / name).is_file() for part in ("--rule", str(rule))]
        try:
            result = subprocess.run([node, str(runner), "--config", str(config), *extra, "--format", "json", str(path)], cwd=path.parent,
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=8, check=False)
            if result.returncode not in (0, 1) or len(result.stdout) > MAX_INPUT:
                raise ValueError("textlint failed")
            places = [f"{item.get('line', 0)}:{item.get('column', 0)}" for document in json.loads(result.stdout)
                      for item in document.get("messages", [])]
            words = spelling(node, runner, prefix, path) if language == "en" else None
        except (OSError, ValueError, subprocess.TimeoutExpired):
            notes.append(f"{path.name} ({language}): textlint did not complete")
            continue
        count = len(places) + len(words or [])
        atomic_write(receipt, json.dumps({"version": VERSION, "count": count}).encode())
        state["files"][str(path)] = [sha, count]
        if places:
            notes.append(f"{path.name} ({language}): {len(places)} issue(s) at {', '.join(places[:6])}" + (" ..." if len(places) > 6 else ""))
        if words:
            notes.append(f"{path.name} (spelling): {len(words)} unknown word(s) at {', '.join(words[:6])}" + (" ..." if len(words) > 6 else ""))
    return notes


def doc_roots(git, items):
    roots = []
    for item in items:
        if Path(item).is_dir() and (root := repo_root(git, item)) and root not in roots:
            roots.append(root)
    return roots


def turn_docs(git, roots, state):
    """Markdown changed since this turn's baseline in the selected repositories."""
    found = []
    for root in roots:
        for path in changed_docs(git, root):
            if state["baseline"].get(str(path)) != content_digest(path) and path not in found:
                found.append(path)
    return found


def doc_baseline(payload, policy, client, state_dir):
    """At each prompt, remember existing Markdown changes so later checks cover only this turn's documents."""
    if policy.get("doc_lint") is not True:
        return
    git, session = policy["git"], payload["session_id"]
    path, state = doc_state(state_dir, client, session)
    baseline = {}
    for root in doc_roots(git, [payload["cwd"], *state["roots"]]):
        for doc in changed_docs(git, root):
            baseline[str(doc)] = content_digest(doc)
    atomic_write(path, json.dumps({"baseline": baseline, "files": {}, "roots": state["roots"]}).encode())


def doc_lint(payload, policy, client, state_dir):
    """Lint Markdown changed by file edits or shell commands once per content; receipts keep only a digest and a count."""
    if policy.get("doc_lint") is not True:
        return None
    cwd, git, session = Path(payload["cwd"]), policy["git"], payload["session_id"]
    explicit = edited_paths(payload, cwd) if payload.get("tool_name") in EDIT_TOOLS else []
    directories, named = shell_targets(payload, cwd)
    if not explicit and not directories:
        return None
    path, state = doc_state(state_dir, client, session)
    roots = doc_roots(git, directories)
    state["roots"] = list(dict.fromkeys([*state["roots"], *map(str, roots)]))
    candidates = [doc.resolve() for doc in [*explicit, *named] if doc.suffix.lower() == ".md" and doc.is_file()]
    candidates = list(dict.fromkeys([*candidates, *turn_docs(git, roots, state)]))
    notes = lint_docs(candidates, policy, client, session, state_dir, state) if candidates else []
    atomic_write(path, json.dumps(state).encode())
    if not notes:
        return None
    return "textlint on edited docs: " + "; ".join(notes) + ". Fix authored prose; keep quotations, code and preserved originals."


def doc_stop(payload, policy, client, state_dir):
    """Ask once per pending set to fix this turn's Markdown issues before finishing; no loop after the client's retry."""
    if policy.get("doc_lint") is not True or policy.get("doc_lint_stop") is not True or payload.get("stop_hook_active"):
        return None
    git, session = policy["git"], payload["session_id"]
    path, state = doc_state(state_dir, client, session)
    tracked = [Path(name) for name in state["files"] if Path(name).is_file()]
    candidates = list(dict.fromkeys([*tracked, *turn_docs(git, doc_roots(git, [payload["cwd"], *state["roots"]]), state)]))
    lint_docs(candidates, policy, client, session, state_dir, state)
    pending = sorted((name, sha, count) for name, (sha, count) in state["files"].items()
                     if count and Path(name).is_file() and content_digest(Path(name)) == sha)
    token = digest(json.dumps(pending).encode()) if pending else None
    blocked = bool(token) and state.get("blocked") != token
    if blocked:
        state["blocked"] = token
    atomic_write(path, json.dumps(state).encode())
    if not blocked:
        return None
    listing = ", ".join(f"{Path(name).name} ({count})" for name, _, count in pending[:6]) + (" ..." if len(pending) > 6 else "")
    return {"decision": "block", "reason": "textlint still reports issues in Markdown changed this turn: " + listing +
            ". Fix authored prose, or keep flagged text that is a quotation, code, specification literal or another owner's content"
            " and say so in the reply."}


def delivery_context(payload, policy):
    note, prompt = policy.get("delivery_note"), payload.get("prompt")
    if not note or not isinstance(prompt, str) or len(prompt) > 200 or not (match := DELIVERY.match(prompt)):
        return {}
    root = repo_root(policy["git"], payload["cwd"])
    entries = [name for name in policy.get("delivery_entries", []) if root and (root / name).is_file()]
    message = f"Delivery request '{match.group(1).lower()}': {note}"
    if entries:
        message += "\nPolicy files in this repository: " + ", ".join(entries)
    return context("UserPromptSubmit", message)


def compact_instructions(payload, policy):
    note = policy.get("compact_note")
    if not note:
        return {}
    root = repo_root(policy["git"], payload["cwd"])
    entries = [name for name in policy["entries"] if root and (root / name).is_file()]
    text = note + ("\nCurrent entrypoints: " + ", ".join(entries) if entries else "")
    return {TEXT_OUTPUT: text[:4000]}


def session_log(state_dir, prefix, client, session):
    path = state_dir / (prefix + digest((client + "\0" + session).encode()) + ".json")
    try:
        value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except (ValueError, OSError):
        value = []
    return path, value if isinstance(value, list) else []


def record_instructions(payload, policy, client, state_dir):
    """Keep which instruction files Claude loaded, with digests, for later load verification."""
    name = payload.get("file_path")
    if policy.get("instruction_log") is not True or not isinstance(name, str) or not Path(name).is_absolute():
        return {}
    path = Path(name)
    entry = {"file": name, "memory_type": payload.get("memory_type"), "load_reason": payload.get("load_reason"),
             "sha256": digest(path.read_bytes()) if path.is_file() else None}
    log, entries = session_log(state_dir, "instructions-", client, payload["session_id"])
    if entry not in entries:
        atomic_write(log, json.dumps([*entries, entry][-200:]).encode())
    return {}


def record_config_change(payload, policy, client, state_dir):
    """Claude discards ConfigChange messages, so changes are queued for the session's next Stop."""
    if policy.get("config_change_note") is not True:
        return {}
    source = payload.get("source") if isinstance(payload.get("source"), str) else "unknown"
    name = Path(payload["file_path"]).name if isinstance(payload.get("file_path"), str) else ""
    item = source + (f" ({name})" if name else "")
    log, entries = session_log(state_dir, "config-", client, payload["session_id"])
    if item not in entries:
        atomic_write(log, json.dumps([*entries, item]).encode())
    return {}


def config_change_message(payload, policy, client, state_dir):
    if policy.get("config_change_note") is not True:
        return None
    log, entries = session_log(state_dir, "config-", client, payload["session_id"])
    if not entries:
        return None
    log.unlink(missing_ok=True)
    return "Claude 設定在本工作階段變更: " + "、".join(entries) + ", 依賴新設定前先讀回確認"


def require_session(payload):
    if not isinstance(payload.get("session_id"), str) or not payload["session_id"]:
        raise ValueError("Hook session_id is required")


def handle(payload, policy, client, state_dir):
    event = payload.get("hook_event_name")
    if event not in EVENTS:
        raise ValueError("Unsupported lifecycle event")
    if event in ("UserPromptSubmit", "PreToolUse", "SubagentStart", "PreCompact", "InstructionsLoaded", "ConfigChange"):
        require_session(payload)
    if event in ("UserPromptSubmit", "PreToolUse", "PreCompact"):
        cwd = payload.get("cwd")
        if not isinstance(cwd, str) or not Path(cwd).is_absolute() or not Path(cwd).is_dir():
            raise ValueError("Hook cwd must be an existing absolute directory")
    if event == "UserPromptSubmit":
        doc_baseline(payload, policy, client, state_dir)
        return delivery_context(payload, policy)
    if event == "PreToolUse":
        return guard(payload, policy)
    if event == "PreCompact":
        return compact_instructions(payload, policy)
    if event == "InstructionsLoaded":
        return record_instructions(payload, policy, client, state_dir)
    if event == "ConfigChange":
        return record_config_change(payload, policy, client, state_dir)
    if event == "SubagentStart":
        note = policy.get("subagent_note")
        return context("SubagentStart", note) if note else {}
    roots = hook_roots(payload, policy, client, state_dir)
    result = workspace_event(payload, policy, client, state_dir, roots)
    if policy.get("project_checks") and roots:
        module = runpy.run_path(str(Path(__file__).with_name("project_checks.py")))
        try:
            message = module["lifecycle"](payload, policy, client, state_dir, roots)
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            message = "Project checks unavailable; use the maintained project check CLI"
        if message and not policy.get("silent"):
            result["systemMessage"] = "\n".join(filter(None, (result.get("systemMessage"), message)))
        elif message and event == "PostToolUse":
            # Silent mode keeps check results with the model instead of showing them to the user.
            previous = result.get("hookSpecificOutput", {}).get("additionalContext")
            result.update(context("PostToolUse", "\n".join(filter(None, (previous, message)))))
    if event == "Stop" and policy.get("silent"):
        # Receipts are still recorded; only the user-facing reminders are dropped.
        result.pop("systemMessage", None)
    if event == "PostToolUse" and (note := doc_lint(payload, policy, client, state_dir)):
        previous = result.get("hookSpecificOutput", {}).get("additionalContext")
        result.update(context("PostToolUse", "\n".join(filter(None, (previous, note)))))
    if event == "Stop" and (block := doc_stop(payload, policy, client, state_dir)):
        result.update(block)
    if event == "Stop":
        notes = (usage_message(payload, policy, client, state_dir),
                 None if policy.get("silent") else config_change_message(payload, policy, client, state_dir))
        for message in notes:
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
    if policy.get("session_environment"):
        message += "\n" + environment_line(policy, None if label == "not a Git repository" else root)
    message += "\n" + policy["start_note"]
    if payload.get("source") == "compact" and policy.get("compact_note"):
        # Codex has no compaction-prompt hook; it runs SessionStart(compact) before the next model request instead.
        message += "\nAfter compaction, restore from the summary and sources: " + policy["compact_note"]
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
        if TEXT_OUTPUT in result:
            sys.stdout.buffer.write(result[TEXT_OUTPUT].encode("utf-8") + b"\n")
        else:
            print(json.dumps(result, ensure_ascii=True))
        return 0
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        # The client retains this as a hook failure, without requesting continuation.
        print("Agent hook failed: " + type(error).__name__ + "; check the installed runtime and policy", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
