#!/usr/bin/env python3
"""Install portable Local Documents packages or the existing Jev Skill; preview by default."""
from __future__ import annotations

import argparse
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def existing_path(value: Path, *, directory: bool = False) -> Path:
    value = value.expanduser()
    if not value.is_absolute():
        raise ValueError("Use an absolute path: " + str(value))
    path = value.resolve(strict=True)
    if not (path.is_dir() if directory else path.is_file()):
        raise ValueError("Unexpected path type: " + str(path))
    return path


def wheel_info(value: Path, expected: str) -> dict:
    path = existing_path(value)
    if path.suffix != ".whl":
        raise ValueError("Use a built wheel")
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise ValueError("Wheel requires one distribution metadata file")
        metadata = Parser().parsestr(archive.read(names[0]).decode("utf-8"))
    if metadata["Name"] != expected or not metadata["Version"]:
        raise ValueError("Unexpected wheel distribution: " + str(metadata["Name"]))
    return {"path": str(path), "name": expected, "version": metadata["Version"], "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def documents(args: argparse.Namespace) -> int:
    config = existing_path(args.config)
    reads = [existing_path(path, directory=True) for path in args.read_root]
    writes = [existing_path(path, directory=True) for path in args.write_root]
    wheels = []
    for value, name in ((args.core_wheel, "my-py-document-core"), (args.server_wheel, "codex-local-documents-mcp")):
        if value is not None:
            wheels.append(wheel_info(value, name))
    runtime = None
    if args.python:
        python = existing_path(args.python)
    else:
        runtime = args.runtime.expanduser()
        if not runtime.is_absolute():
            raise ValueError("Runtime must be an absolute path")
        runtime = runtime.resolve()
        if runtime.is_relative_to(ROOT) or ROOT.is_relative_to(runtime):
            raise ValueError("Runtime must be outside the source repository")
        python = runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if runtime.exists() and (not (runtime / "pyvenv.cfg").is_file() or not python.is_file()):
            raise ValueError("Existing runtime is not a complete virtual environment; preserve and inspect it")
        if not python.is_file() and not (args.core_wheel and args.server_wheel):
            raise ValueError("A new runtime requires --core-wheel and --server-wheel")
    command = [str(python), "-I", "-B", "-m", "mcp_servers.local_documents.install_document_mcp", "--python", str(python), "--config", str(config)]
    for option, paths in (("--read-root", reads), ("--write-root", writes)):
        for path in paths:
            command.extend((option, str(path)))
    if not args.apply:
        print(json.dumps({"status": "preview", "server": "local_documents", "config": str(config), "python": str(python), "wheels": wheels, "read_roots": [str(path) for path in reads], "write_roots": [str(path) for path in writes], "registration_command": command + ["--apply"], "verify": args.verify}, ensure_ascii=False))
        return 0
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    if runtime is not None and not python.is_file():
        venv.EnvBuilder(with_pip=True).create(runtime)
    for wheel in wheels:
        if hashlib.sha256(Path(wheel["path"]).read_bytes()).hexdigest() != wheel["sha256"]:
            raise ValueError("Wheel changed since inspection")
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", "--force-reinstall", wheel["path"]], env=env, check=True)
    if runtime is not None:
        subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(ROOT / "mcp/mcp_servers/local_documents/requirements.txt")], env=env, check=True)
    subprocess.run([str(python), "-m", "pip", "check"], env=env, check=True)
    subprocess.run(command + ["--apply"], env=env, check=True)
    if args.verify:
        subprocess.run([str(python), "-I", "-B", "-m", "mcp_servers.local_documents.verify_document_mcp"], env=env, check=True, timeout=330)
    return 0


def workspace(args: argparse.Namespace) -> int:
    config = existing_path(args.config)
    reads = [existing_path(path, directory=True) for path in args.read_root]
    wheels = []
    for value, name in (
        (args.core_wheel, "my-py-workspace-core"),
        (args.server_wheel, "codex-workspace-inspection-mcp"),
    ):
        if value is not None:
            wheels.append(wheel_info(value, name))
    runtime = None
    if args.python:
        python = existing_path(args.python)
    else:
        runtime = args.runtime.expanduser()
        if not runtime.is_absolute():
            raise ValueError("Runtime must be an absolute path")
        runtime = runtime.resolve()
        if runtime.is_relative_to(ROOT) or ROOT.is_relative_to(runtime):
            raise ValueError("Runtime must be outside the source repository")
        python = runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if runtime.exists() and (not (runtime / "pyvenv.cfg").is_file() or not python.is_file()):
            raise ValueError("Existing runtime is not a complete virtual environment; preserve and inspect it")
        if not python.is_file() and not (args.core_wheel and args.server_wheel):
            raise ValueError("A new runtime requires --core-wheel and --server-wheel")
    command = [str(python), "-I", "-B", "-m", "workspace_inspection_mcp.install", "--python", str(python), "--config", str(config)]
    for path in reads:
        command.extend(("--read-root", str(path)))
    if not args.apply:
        print(json.dumps({"status": "preview", "server": "workspace_inspection", "config": str(config), "python": str(python), "wheels": wheels, "read_roots": [str(path) for path in reads], "registration_command": command + ["--apply"], "verify": args.verify}, ensure_ascii=False))
        return 0
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    if runtime is not None and not python.is_file():
        venv.EnvBuilder(with_pip=True).create(runtime)
    for wheel in wheels:
        if hashlib.sha256(Path(wheel["path"]).read_bytes()).hexdigest() != wheel["sha256"]:
            raise ValueError("Wheel changed since inspection")
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", "--force-reinstall", wheel["path"]], env=env, check=True)
    if runtime is not None:
        subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(ROOT / "mcp/mcp_servers/workspace_inspection/requirements.txt")], env=env, check=True)
    subprocess.run([str(python), "-m", "pip", "check"], env=env, check=True)
    subprocess.run(command + ["--apply"], env=env, check=True)
    if args.verify:
        subprocess.run([str(python), "-I", "-B", "-m", "workspace_inspection_mcp.verify"], env=env, check=True, timeout=120)
    return 0


def main(argv: list[str] | None = None) -> int:
    selected = sys.argv[1:] if argv is None else argv
    if selected and selected[0] == "bootstrap":
        return subprocess.run([sys.executable, "-B", str(ROOT / "mcp/scripts/bootstrap_mcp.py"), *selected[1:]], check=False).returncode
    parser = argparse.ArgumentParser(description=__doc__, epilog="Jev options are forwarded to its existing installer. Add --apply to install either server.")
    sub = parser.add_subparsers(dest="server", required=True)
    doc = sub.add_parser("local_documents", help="Install or reuse portable wheels in an isolated environment")
    runtime = doc.add_mutually_exclusive_group(required=True)
    runtime.add_argument("--python", type=Path)
    runtime.add_argument("--runtime", type=Path)
    doc.add_argument("--core-wheel", type=Path)
    doc.add_argument("--server-wheel", type=Path)
    doc.add_argument("--config", type=Path, default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "config.toml")
    doc.add_argument("--read-root", type=Path, action="append", required=True)
    doc.add_argument("--write-root", type=Path, action="append", default=[])
    mode = doc.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    doc.add_argument("--verify", action="store_true")
    inspect = sub.add_parser("workspace_inspection", help="Install the read-only workspace inspection MCP")
    runtime = inspect.add_mutually_exclusive_group(required=True)
    runtime.add_argument("--python", type=Path)
    runtime.add_argument("--runtime", type=Path)
    inspect.add_argument("--core-wheel", type=Path)
    inspect.add_argument("--server-wheel", type=Path)
    inspect.add_argument("--config", type=Path, default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "config.toml")
    inspect.add_argument("--read-root", type=Path, action="append", required=True)
    mode = inspect.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    inspect.add_argument("--verify", action="store_true")
    jev = sub.add_parser("jev", add_help=False, help="Use the existing Jev Skill installer")
    mode = jev.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args, extra = parser.parse_known_args(argv)
    if args.server in {"local_documents", "workspace_inspection"} and extra:
        parser.error("unrecognized arguments: " + " ".join(extra))
    try:
        if args.server == "local_documents":
            return documents(args)
        if args.server == "workspace_inspection":
            return workspace(args)
        command = [sys.executable, "-B", str(ROOT / "skills/jev-evaluation/scripts/install_mcp.py"), *extra]
        if not args.apply:
            command.append("--dry-run")
        return subprocess.run(command, check=False).returncode
    except (ValueError, OSError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
