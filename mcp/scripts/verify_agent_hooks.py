#!/usr/bin/env python3
"""Verify installed hook commands and optionally query Codex native discovery."""

import argparse
import json
import os
from pathlib import Path
import queue
import shlex
import subprocess
import sys
import threading
import time
import uuid

from install_agent_hooks import read_json


def selected_hooks(result, groups, config):
    commands = {group["hooks"][0]["command"] for group in groups.values()}
    selected = []
    for row in result.get("data", []):
        if row.get("errors"):
            raise ValueError("Native hook discovery errors: " + str(row["errors"]))
        for hook in row.get("hooks", []):
            if hook.get("sourcePath") and Path(hook["sourcePath"]).resolve() == config.resolve() and hook.get("command") in commands:
                selected.append({key: hook.get(key) for key in ("eventName", "enabled", "trustStatus")})
    return selected


def discover(cli, cwd):
    process = subprocess.Popen([str(cli), "app-server"], cwd=cwd, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, encoding="utf-8", bufsize=1)
    messages = queue.Queue()

    def receive():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except ValueError:
                pass

    reader = threading.Thread(target=receive, daemon=True)
    reader.start()

    def request(identifier, method, params):
        process.stdin.write(json.dumps({"id": identifier, "method": method, "params": params}) + "\n")
        process.stdin.flush()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            message = messages.get(timeout=max(.1, deadline - time.monotonic()))
            if message.get("id") == identifier:
                if "error" in message:
                    raise ValueError(method + " failed: " + str(message["error"]))
                return message["result"]
        raise TimeoutError(method)

    try:
        request(1, "initialize", {"clientInfo": {"name": "agent_hook_verifier", "version": "0.1.0"},
                                   "capabilities": {"experimentalApi": True}})
        process.stdin.write('{"method":"initialized"}\n')
        process.stdin.flush()
        return request(2, "hooks/list", {"cwds": [str(cwd)]})
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)
        reader.join(timeout=2)
        process.stdout.close()


def command_evidence(client, event, output):
    if not isinstance(output, dict) or output.get("decision") == "block" or output.get("continue") is False:
        raise ValueError("Unexpected hook output: " + event)
    return {"client": client, "event": event, "command": "passed", "json_output": "valid",
            "output_kind": "message" if output else "silent",
            "hook_output": output, "project_checks": "not_verified", "native_event": "not_verified"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("codex", "claude"), required=True)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--codex-cli", type=Path)
    args = parser.parse_args()
    try:
        home, cwd = args.home.expanduser().resolve(), args.cwd.resolve(strict=True)
        manifest = read_json(home / "managed-agent-hooks/manifest.json")
        config = read_json(home / ("hooks.json" if args.client == "codex" else "settings.json"))
        session = "installed-command-verification-" + uuid.uuid4().hex
        for event, group in manifest["groups"].items():
            if config.get("hooks", {}).get(event, []).count(group) != 1:
                raise ValueError("Missing or changed installed event: " + event)
            handler = group["hooks"][0]
            if args.client == "claude":
                argv = [handler["command"], *handler["args"]]
            else:
                command = handler.get("commandWindows", handler["command"]) if os.name == "nt" else handler["command"]
                argv = shlex.split(command)
            payload = {"hook_event_name": event, "cwd": str(cwd), "session_id": session, "source": "compact"}
            result = subprocess.run(argv, input=json.dumps(payload).encode(), capture_output=True, timeout=20)
            if result.returncode:
                raise ValueError(f"{event}: command exit {result.returncode}")
            output = json.loads(result.stdout)
            print(json.dumps(command_evidence(args.client, event, output), ensure_ascii=False))
        if args.codex_cli:
            result = discover(args.codex_cli, cwd)
            selected = selected_hooks(result, manifest["groups"], home / "hooks.json")
            print(json.dumps({"native_hooks": selected}))
            if len(selected) != len(manifest["groups"]):
                raise ValueError("Native discovery did not return every selected hook")
        return 0
    except (OSError, ValueError, KeyError, queue.Empty, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
