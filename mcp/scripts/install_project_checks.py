#!/usr/bin/env python3
"""Install local Git check dispatchers while chaining existing hooks unchanged."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from install_agent_hooks import apply_plan, encoded, read_json
from project_checks import git, identity, digest

HOOKS = ("applypatch-msg", "pre-applypatch", "post-applypatch", "pre-commit", "pre-merge-commit",
         "prepare-commit-msg", "commit-msg", "post-commit", "pre-rebase", "post-checkout", "post-merge",
         "pre-push", "post-rewrite", "sendemail-validate", "post-index-change", "reference-transaction")


def plan(root, policy_path, state):
    policy = read_json(policy_path)
    origin = identity(os.fsdecode(git(root, "remote", "get-url", "origin")).strip())
    row = next((r for r in policy.get("project_checks", []) if Path(r["root"]).resolve() == root.resolve()
                and identity(r["project"]["repository"]) == origin), None)
    if row is None:
        raise ValueError("No installed policy for checkout")
    common = Path(os.fsdecode(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).strip())
    managed = common / "managed-project-checks"
    manifest = managed / "manifest.json"
    prior = read_json(manifest)
    result = subprocess.run(["git", "config", "--local", "--get", "core.hooksPath"], cwd=root, capture_output=True)
    if result.returncode not in (0, 1):
        raise ValueError("Cannot read local hook selection")
    current = os.fsdecode(result.stdout).strip() if result.returncode == 0 else None
    if prior:
        if current != str(managed):
            raise ValueError("Hook selection changed locally")
        original = prior["original"]
        old_dir = Path(prior["original_directory"])
        for name, expected in prior["files"].items():
            file = managed / name
            if not file.is_file() or digest(file.read_bytes()) != expected:
                raise ValueError("Managed Git hook changed locally")
    else:
        original = current
        old_dir = Path(os.fsdecode(git(root, "rev-parse", "--path-format=absolute", "--git-path", "hooks")).strip())
    if old_dir.resolve() == managed.resolve():
        raise ValueError("Cannot chain a managed hook to itself")
    files = {}
    runner = policy_path.parent / "project_checks.py"
    quote = lambda p: shlex.quote(Path(p).as_posix())
    command = " ".join([quote(sys.executable), "-I -B", quote(runner), "public-index --policy", quote(policy_path),
                        "--state-dir", quote(state)])
    for name in HOOKS:
        old = old_dir / name
        public_guard = name == "pre-commit" and row["project"]["visibility"] == "public"
        if not old.is_file() and not public_guard:
            continue
        # Original hook retains arguments and stdin, including pre-push input.
        script = "#!/bin/sh\n# Managed project checks; edit the private registry, not this file\n"
        if old.is_file():
            if os.name != "nt" and not os.access(old, os.X_OK):
                if not public_guard:
                    continue
            else:
                script += quote(old) + ' "$@" || exit $?\n'
        if public_guard:
            script += "exec " + command + "\n"
        else:
            script += "exit 0\n"
        files[managed / name] = script.encode()
    record = {"original": original, "original_directory": str(old_dir),
              "files": {p.name: digest(data) for p, data in files.items()}}
    files[manifest] = encoded(record)
    expected = {p: p.read_bytes() if p.exists() else None for p in files}
    config = common / "config"
    backup = managed / "original-config"
    if not prior and not backup.exists():
        files[backup] = config.read_bytes()
        expected[backup] = None
    return managed, current, files, expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--checkout", type=Path, action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        pending = False
        plans = [(p.resolve(), *plan(p.resolve(), args.policy.resolve(), args.state_dir.resolve())) for p in args.checkout]
        for root, managed, current, files, expected in plans:
            changed = current != str(managed) or any(expected[p] != data for p, data in files.items())
            pending |= changed
            print(json.dumps({"checkout": str(root), "status": "UPDATE" if changed else "CURRENT",
                              "chained_hooks": [p.name for p in files if p.name in HOOKS]}))
            if args.apply:
                apply_plan(files, expected, managed.parent)
                for p in files:
                    if p.name in HOOKS:
                        p.chmod(p.stat().st_mode | 0o111)
                if current != str(managed):
                    observed = subprocess.run(["git", "config", "--local", "--get", "core.hooksPath"], cwd=root, capture_output=True)
                    actual = os.fsdecode(observed.stdout).strip() if observed.returncode == 0 else None
                    if actual != current:
                        raise ValueError("Git config changed after preview")
                    subprocess.run(["git", "config", "--local", "core.hooksPath", str(managed)], cwd=root, check=True)
                if git(root, "config", "--local", "--get", "core.hooksPath").decode().strip() != str(managed):
                    raise ValueError("Git hook readback mismatch")
        return 0 if args.apply or not pending else 1
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(type(error).__name__ + ": " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
