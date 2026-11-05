#!/usr/bin/env python3
"""Trusted project policy: staged publication checks and change-bound validation receipts."""
from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import runpy
import subprocess
import sys
import tempfile
import time
import tomllib

VERSION = "0.1.0"
MAX_BYTES = 4 * 1024 * 1024
MAX_FILES = 1000


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True) + "\n").encode()


def git(root, *args):
    result = subprocess.run(["git", "--no-optional-locks", "-c", "core.fsmonitor=false", *args],
                            cwd=root, stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    if result.returncode or len(result.stdout) > 16 * MAX_BYTES:
        raise ValueError("Git inspection failed or exceeded its bound")
    return result.stdout


def identity(value):
    return value.removesuffix(".git").replace("git@github.com:", "https://github.com/").lower()


def safe_path(root, name):
    parts = PurePosixPath(name)
    if not name or "\\" in name or ":" in name or parts.is_absolute() or ".." in parts.parts:
        raise ValueError("Invalid repository-relative path")
    path = root / name
    for parent in (path, *path.parents):
        if parent == root:
            break
        if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
            raise ValueError("Linked input is not accepted")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Input escapes repository")
    return path


def matches(name, patterns):
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def validate_registry(value):
    if set(value) != {"schema_version", "projects"} or value["schema_version"] != 1:
        raise ValueError("Unsupported project check registry")
    seen = set()
    for row in value["projects"]:
        if set(row) != {"repository", "visibility", "deny", "allow", "checks", "delivery"}:
            raise ValueError("Unexpected project fields")
        key = identity(row["repository"])
        if key in seen or not key.startswith("https://github.com/") or row["visibility"] not in ("public", "private"):
            raise ValueError("Invalid or duplicate project identity")
        seen.add(key)
        ids = set()
        for patterns in (row["deny"], row["allow"]):
            if not isinstance(patterns, list) or any(not isinstance(p, str) or not p or p.startswith("/") or ".." in p.split("/") for p in patterns):
                raise ValueError("Invalid path patterns")
        for check in row["checks"]:
            if set(check) != {"id", "kind", "paths", "exclude"} or check["kind"] not in ("json", "toml", "python", "node"):
                raise ValueError("Only supported read-only checks may run automatically")
            if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", check["id"]) or check["id"] in ids:
                raise ValueError("Invalid or duplicate check ID")
            ids.add(check["id"])
            for patterns in (check["paths"], check["exclude"]):
                if not isinstance(patterns, list) or any(not isinstance(p, str) or not p for p in patterns):
                    raise ValueError("Invalid check selector")
        if not isinstance(row["delivery"], list) or any(not isinstance(s, str) for s in row["delivery"]):
            raise ValueError("Delivery references must be text, never executable commands")


def expand_registry(value):
    if "defaults" not in value:
        validate_registry(value)
        return value
    if set(value) != {"schema_version", "defaults", "projects"} or set(value["defaults"]) != {"deny", "allow", "checks"}:
        raise ValueError("Unsupported registry defaults")
    rows = []
    for item in value["projects"]:
        if set(item) - {"repository", "visibility", "delivery", "deny_extra", "allow_extra", "checks"}:
            raise ValueError("Unexpected project override")
        row = dict(value["defaults"], **{k: v for k, v in item.items() if k not in ("deny_extra", "allow_extra")})
        row["deny"] = row["deny"] + item.get("deny_extra", [])
        row["allow"] = row["allow"] + item.get("allow_extra", [])
        rows.append(row)
    result = {"schema_version": value["schema_version"], "projects": rows}
    validate_registry(result)
    return result


def selected(policy, cwd):
    """Return the checkout root and its installed project; a directory outside Git or without origin has none."""
    try:
        root = Path(os.fsdecode(git(cwd, "rev-parse", "--show-toplevel")).strip()).resolve()
    except ValueError:
        return None, None
    try:
        origin = identity(os.fsdecode(git(root, "remote", "get-url", "origin")).strip())
    except ValueError:
        return root, None
    for item in policy.get("project_checks", []):
        if Path(item["root"]).resolve() == root and identity(item["project"]["repository"]) == origin:
            return root, item["project"]
    return root, None


def changed_paths(root):
    try:
        git(root, "rev-parse", "--verify", "HEAD")
        diff = git(root, "diff", "--no-ext-diff", "--no-textconv", "--name-only", "--no-renames", "-z", "HEAD", "--")
    except ValueError:
        diff = git(root, "ls-files", "-z")
    extra = git(root, "ls-files", "--others", "--exclude-standard", "-z")
    names = sorted(set(os.fsdecode(n) for n in (diff + extra).split(b"\0") if n))
    if len(names) > MAX_FILES:
        raise ValueError("Too many changed paths; use scoped project checks")
    return names


def denied(project, name):
    return matches(name.lower(), [p.lower() for p in project["deny"]]) and not matches(name, project["allow"])


def public_index(root, project):
    if project["visibility"] != "public":
        return {"status": "not_applicable", "scope": "index"}
    scanner_path = Path(__file__).with_name("public_content.py")
    if not scanner_path.exists():
        scanner_path = Path(__file__).resolve().parents[2] / "tools/check-public-content.py"
    scanner = runpy.run_path(str(scanner_path))
    issues, count = [], 0
    changed = set(git(root, "diff", "--cached", "--name-only", "--no-renames", "-z", "--diff-filter=ACMRT", "--").split(b"\0"))
    # Inspect object IDs from the index, not the possibly different working copy.
    for entry in git(root, "ls-files", "--stage", "-z").split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        inspect_content = name in changed
        mode, oid, stage = metadata.split()
        name = os.fsdecode(name)
        if stage != b"0":
            raise ValueError("Unmerged index cannot pass publication checks")
        location = oid.decode()[:12]
        if denied(project, name) or scanner["personal_path"](name) or scanner["private_name"](name):
            issues.append({"object": location, "reason": "private path"})
            continue
        if mode == b"160000" or not inspect_content:
            continue
        size = int(git(root, "cat-file", "-s", oid.decode()))
        if size > MAX_BYTES:
            # Large binary assets are not silently declared scanned.
            issues.append({"object": location, "reason": "size limit; explicit review required"})
            continue
        raw = git(root, "cat-file", "blob", oid.decode())
        count += 1
        if "private key material" in scanner["content_problems"](raw):
            issues.append({"object": location, "reason": "private key material"})
    return {"status": "failed" if issues else "passed", "scope": "all index paths and changed staged blobs", "objects": count, "issues": issues}


def check_inputs(root, check, names):
    selected_names = [n for n in names if matches(n, check["paths"]) and not matches(n, check["exclude"])]
    values = []
    total = 0
    for name in selected_names:
        path = safe_path(root, name)
        if not path.exists():
            values.append((name, None))
            continue
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise ValueError("Check input is not a bounded regular file")
        raw = path.read_bytes()
        total += len(raw)
        if total > 16 * MAX_BYTES:
            raise ValueError("Selected inputs exceed the check byte budget")
        values.append((name, raw))
    return values


def signature(check, values, policy):
    runtime = policy.get("node") if check["kind"] == "node" else sys.version
    return digest(encoded([VERSION, check, runtime, [(name, digest(raw) if raw is not None else None) for name, raw in values]]))


def perform(root, check, values, policy, deadline):
    count = 0
    for name, raw in values:
        if time.monotonic() >= deadline:
            return {"status": "deferred", "reason": "time budget", "checked": count}
        if raw is None:
            continue
        try:
            kind = check["kind"]
            if kind == "json":
                json.loads(raw.decode("utf-8-sig"))
            elif kind == "toml":
                tomllib.loads(raw.decode("utf-8-sig"))
            elif kind == "python":
                # Compile without importing, running code or writing pycache.
                compile(raw, name, "exec", flags=ast.PyCF_ONLY_AST, dont_inherit=True)
            else:
                runtime = policy.get("node")
                if not runtime:
                    return {"status": "unavailable", "reason": "Node runtime missing", "checked": count}
                env = dict(os.environ)
                env.pop("NODE_OPTIONS", None)
                env.pop("NODE_PATH", None)
                result = subprocess.run([runtime, "--check", str(safe_path(root, name))], cwd=root,
                                        env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL, timeout=max(.1, min(2, deadline-time.monotonic())))
                if result.returncode:
                    return {"status": "failed", "exit_code": result.returncode, "path": name, "checked": count}
            count += 1
        except (SyntaxError, ValueError, UnicodeError) as error:
            return {"status": "failed", "reason": "parse error", "path": name,
                    "line": getattr(error, "lineno", None), "checked": count}
        except subprocess.TimeoutExpired:
            return {"status": "deferred", "reason": "time budget", "checked": count}
    return {"status": "passed", "checked": count, "scope": "syntax only"}


def state_path(state, root, client, session):
    return state / ("checks-" + digest(encoded([str(root), client, session])) + ".json")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".checks-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded(value))
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def evaluate(root, project, policy, state, client, session, run=False):
    names = changed_paths(root)
    path = state_path(state, root, client, session)
    prior = json.loads(path.read_text()) if path.exists() else {}
    receipts = prior.get("receipts", {})
    rows = []
    deadline = time.monotonic() + (60 if client == "cli" else 6)
    for check in project["checks"]:
        values = check_inputs(root, check, names)
        if not values:
            continue
        token = signature(check, values, policy)
        receipt = receipts.get(check["id"], {})
        if run and (receipt.get("signature") != token or client == "cli" and receipt.get("status") in ("deferred", "unavailable")):
            result = perform(root, check, values, policy, deadline)
            # Do not promote a result for inputs changed while the process ran.
            if signature(check, check_inputs(root, check, changed_paths(root)), policy) != token:
                result = {"status": "stale", "reason": "inputs changed during check"}
            receipt = dict(result, signature=token)
            receipts[check["id"]] = receipt
        status = receipt.get("status", "missing") if receipt.get("signature") == token else "stale" if receipt else "missing"
        rows.append({"id": check["id"], "status": status, "signature": token,
                     "detail": {k: receipt[k] for k in ("reason", "path", "line", "exit_code", "checked") if k in receipt}
                     if receipt.get("signature") == token else {}})
    private = [digest(n.encode())[:12] for n in names if project["visibility"] == "public" and denied(project, n)]
    report = {"checks": rows, "private_paths": private, "project_acceptance": "not_verified",
              "delivery": project["delivery"] if names else []}
    if run:
        write_json(path, {"receipts": receipts, "reported": prior.get("reported")})
    return report, path


def lifecycle(payload, policy, client, state, roots=None):
    """Report each installed project among roots; roots defaults to the hook cwd."""
    if not policy.get("project_checks") or payload.get("stop_hook_active"):
        return ""
    event = payload.get("hook_event_name")
    if event not in ("PostToolUse", "Stop"):
        return ""
    messages, seen = [], set()
    for directory in roots if roots is not None else [payload["cwd"]]:
        root, project = selected(policy, directory)
        if not project or root in seen:
            continue
        seen.add(root)
        message = project_message(root, project, policy, state, client, payload["session_id"], event)
        if message:
            messages.append(message if Path(payload["cwd"]).resolve().is_relative_to(root) else root.name + ": " + message)
    return ("Project checks: " + " | ".join(messages))[:1100] if messages else ""


def project_message(root, project, policy, state, client, session, event):
    report, path = evaluate(root, project, policy, state, client, session, event == "PostToolUse")
    failures = [row["id"] + ":" + row["status"] for row in report["checks"] if row["status"] != "passed"]
    if report["private_paths"]:
        failures.append("private paths require publication review")
    if event == "Stop" and report["delivery"]:
        failures.append("Project delivery evidence: " + "; ".join(report["delivery"]))
    if not failures:
        return ""
    value = json.loads(path.read_text()) if path.exists() else {}
    token = digest(encoded(report))
    if value.get("reported") == token:
        return ""
    value["reported"] = token
    write_json(path, value)
    return "; ".join(failures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("public-index", "run", "audit"))
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--session", default="delivery")
    args = parser.parse_args()
    try:
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        root, project = selected(policy, args.cwd)
        if not project:
            raise ValueError("Checkout identity is not installed in this policy")
        if args.action == "public-index":
            report = public_index(root, project)
            failed = report["status"] == "failed"
        else:
            report, _ = evaluate(root, project, policy, args.state_dir, "cli", args.session, args.action == "run")
            failed = bool(report["private_paths"]) or any(r["status"] != "passed" for r in report["checks"])
        print(json.dumps(report))
        return int(failed)
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "error", "reason": type(error).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
