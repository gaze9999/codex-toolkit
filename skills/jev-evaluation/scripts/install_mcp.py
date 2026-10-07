#!/usr/bin/env python3
"""Install the portable Jev Skill and a user-scoped Codex stdio MCP server."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import venv

NAME = "jev-evaluation"
BEGIN = "# BEGIN codex-setup Jev MCP"
END = "# END codex-setup Jev MCP"
SKIP = {"__pycache__", ".venv", "venv", ".git", ".DS_Store"}


def files(root: Path) -> dict[str, bytes]:
    result = {}
    for path in root.rglob("*"):
        if not path.is_file() or SKIP.intersection(path.relative_to(root).parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink() or path.suffix in {".key", ".pem"} or path.name == ".env":
            raise ValueError("skill_contains_private_or_linked_file")
        result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def default_skill_root(codex: Path) -> Path:
    if os.environ.get("CODEX_HOME") or (codex / "skills" / NAME / "SKILL.md").is_file():
        return codex / "skills"
    return Path.home() / ".agents" / "skills"


def default_runtime() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "codex-setup" / ("jev-mcp-py" + str(sys.version_info.major) + str(sys.version_info.minor))


def python_path(runtime: Path) -> Path:
    return runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def update_config(original: str, python: Path, server: Path) -> str:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    parsed = tomllib.loads(original)
    owned = BEGIN in original or END in original
    pattern = re.compile(r"(?m)^" + re.escape(BEGIN) + r"\r?\n.*?^" + re.escape(END) + r"(?:\r?\n|$)", re.DOTALL)
    matches = list(pattern.finditer(original))
    if owned and len(matches) != 1:
        raise ValueError("invalid_managed_config_block")
    if "jev" in parsed.get("mcp_servers", {}) and not owned:
        raise ValueError("existing_jev_server_not_managed")
    block = "\n".join([
        BEGIN, "[mcp_servers.jev]", "command = " + json.dumps(str(python), ensure_ascii=False),
        "args = " + json.dumps(["-B", str(server)], ensure_ascii=False),
        'env_vars = ["TYPESAFE_API_KEY", "TYPESAFE_MODEL", "CODEX_HOME"]',
        'enabled_tools = ["jev_rank", "jev_evaluate", "jev_status"]',
        "enabled = true", "required = false", "startup_timeout_sec = 30", "tool_timeout_sec = 30", END, "",
    ])
    result = original[:matches[0].start()] + block + original[matches[0].end():] if owned else original + ("\n" if original and not original.endswith("\n") else "") + "\n" + block
    tomllib.loads(result)
    return result


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".jev-install-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(source: Path, target: Path, config: Path, runtime: Path, replace: bool) -> dict:
    source, target, config, runtime = (path.expanduser().resolve() for path in (source, target, config, runtime))
    if target.name != NAME or not (source / "SKILL.md").is_file():
        raise ValueError("invalid_skill_location")
    originals = files(source)
    existing = files(target) if target.exists() else {}
    changed = existing != originals
    if target.exists() and changed and not replace:
        raise ValueError("existing_skill_use_replace")
    if target.exists() and set(existing) - set(originals):
        raise ValueError("unexpected_installed_files_preserve_and_review")
    initial = config.read_bytes() if config.exists() else b""
    candidate = update_config(initial.decode("utf-8-sig"), python_path(runtime), target / "scripts/mcp_server.py").encode("utf-8")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = runtime.parent / ("jev-backup-" + timestamp)
    if changed or initial != candidate:
        backup.mkdir(parents=True, exist_ok=False)
        if changed and existing:
            for name, content in existing.items():
                atomic_write(backup / NAME / name, content)
        if initial != candidate and initial:
            atomic_write(backup / "config.toml", initial)
    if (config.read_bytes() if config.exists() else b"") != initial:
        raise ValueError("config_changed_during_install")
    if target.exists() and files(target) != existing:
        raise ValueError("skill_changed_during_install")
    if changed:
        for name, content in originals.items():
            atomic_write(target / name, content)
    if initial != candidate:
        atomic_write(config, candidate)
    return {"status": "ok", "skill": str(target), "config": str(config), "runtime": str(runtime), "backup": str(backup) if backup.exists() else None, "restart_required": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", type=Path, help="Override the client's verified user-scoped Skill directory.")
    parser.add_argument("--config", type=Path, help="Override user Codex config.toml; never supply a project config for global installation.")
    parser.add_argument("--runtime", type=Path, help="Isolated Python runtime directory.")
    parser.add_argument("--replace", action="store_true", help="Back up and replace known Skill files; unknown files are preserved for review.")
    parser.add_argument("--dry-run", action="store_true", help="Show destinations only, without installing packages or editing files.")
    parser.add_argument("--verify-online", action="store_true", help="After installation, verify MCP with a small built-in public sample.")
    parser.add_argument("--runtime-ready", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    codex = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    target = (args.skill_root or default_skill_root(codex)) / NAME
    config = args.config or codex / "config.toml"
    runtime = (args.runtime or default_runtime()).expanduser().resolve()
    try:
        if sys.version_info < (3, 10):
            raise ValueError("python_3_10_required")
        if args.dry_run:
            print(json.dumps({"status": "dry_run", "skill": str(target), "config": str(config), "runtime": str(runtime)}, ensure_ascii=False))
            return 0
        python = python_path(runtime)
        if not args.runtime_ready:
            if not python.is_file():
                venv.EnvBuilder(with_pip=True).create(runtime)
            requirements = source / "requirements.txt"
            expected = hashlib.sha256(requirements.read_bytes()).hexdigest()
            marker = runtime / "jev-requirements.sha256"
            if not marker.is_file() or marker.read_text(encoding="ascii").strip() != expected:
                subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "--quiet", "--timeout", "20", "--retries", "1", "--index-url", "https://pypi.org/simple", "-r", str(requirements)], check=True)
                marker.write_text(expected, encoding="ascii")
            return subprocess.run([str(python), "-B", str(Path(__file__).resolve()), *sys.argv[1:], "--runtime", str(runtime), "--runtime-ready"], check=False).returncode
        result = install(source, target, config, runtime, args.replace)
        verification = subprocess.run([str(python), "-B", str(target / "scripts/verify_mcp.py"), *(["--online"] if args.verify_online else [])], capture_output=True, text=True, encoding="utf-8", timeout=50, check=False)
        try:
            result["verification"] = json.loads(verification.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            result["verification"] = {"status": "fallback", "reason": "mcp_verification_unavailable"}
        result["installed"] = True
        if verification.returncode:
            result["status"] = "fallback"
        print(json.dumps(result, ensure_ascii=False))
        return 0 if verification.returncode == 0 else 1
    except ValueError as exc:
        known = {"python_3_10_required", "skill_contains_private_or_linked_file", "invalid_managed_config_block", "existing_jev_server_not_managed", "invalid_skill_location", "existing_skill_use_replace", "unexpected_installed_files_preserve_and_review", "config_changed_during_install", "skill_changed_during_install"}
        print(json.dumps({"status": "fallback", "reason": str(exc) if str(exc) in known else "invalid_configuration"}))
        return 1
    except (OSError, subprocess.SubprocessError):
        print(json.dumps({"status": "fallback", "reason": "installation_failed_check_local_destinations_and_runtime"}))
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
