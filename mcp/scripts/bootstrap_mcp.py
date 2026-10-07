#!/usr/bin/env python3
"""Preview or apply the baseline preset from a verified local wheel bundle."""
from __future__ import annotations

import argparse
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid
import venv
import zipfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def default_data_root(platform=None, environment=None, home=None):
    platform, environment, home = platform or sys.platform, os.environ if environment is None else environment, home or Path.home()
    if platform == "win32":
        path = Path(environment.get("LOCALAPPDATA", ""))
        base = path if path.is_absolute() else home/"AppData/Local"
    elif platform == "darwin":
        base = home/"Library/Application Support"
    else:
        path = type(home)(environment.get("XDG_DATA_HOME", ""))
        base = path if path.is_absolute() else home/".local/share"
    return base/"codex-setup"


def absolute(path):
    path = path.expanduser()
    if not path.is_absolute():
        raise ValueError("Use an absolute path: " + str(path))
    return path.resolve()


def python_path(runtime):
    return runtime/("Scripts/python.exe" if os.name == "nt" else "bin/python")


def wheel_info(path):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Wheel CRC mismatch")
        metadata = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError("Invalid wheel metadata")
        parsed = Parser().parsestr(archive.read(metadata[0]).decode("utf-8"))
    return {"name": parsed["Name"], "version": parsed["Version"], "sha256": digest(path.read_bytes())}


def load_bundle(bundle, preset):
    path = bundle/"bundle.json"
    if not path.is_file():
        return {}, "Missing bundle.json; run prepare_mcp_bundle.py with built wheels"
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("version") != 1 or value.get("preset_sha256") != digest(json.dumps(preset, sort_keys=True, separators=(",", ":")).encode()):
        raise ValueError("Bundle does not match the preset")
    wheels = {}
    for item in value["wheels"]:
        filename = item["file"]
        if Path(filename).name != filename or not filename.endswith(".whl"):
            raise ValueError("Unsafe wheel filename")
        wheel = bundle/filename
        if wheel.is_symlink() or wheel_info(wheel) != {key: item[key] for key in ("name", "version", "sha256")}:
            raise ValueError("Wheel changed or metadata mismatch: " + filename)
        if item["name"] in wheels:
            raise ValueError("Duplicate package")
        wheels[item["name"]] = item | {"path": str(wheel)}
    return wheels, None


def run(command, *, timeout=180):
    value = subprocess.run(command, env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", JEV_TELEMETRY="0"), capture_output=True, text=True, encoding="utf-8", timeout=timeout, check=False)
    if value.returncode:
        raise ValueError("Command failed; inspect the isolated runtime: " + Path(command[0]).name)
    return value.stdout.strip()


def runtime_info(python, packages):
    if not python.is_file():
        return None
    script = "import importlib.metadata as m,json,sys; names="+repr(list(packages))+"; print(json.dumps({'python':list(sys.version_info[:3]),'packages':{n:next((d.version for d in m.distributions() if d.metadata['Name'].lower().replace('_','-')==n.lower().replace('_','-')),None) for n in names}}))"
    try:
        return json.loads(run([str(python), "-I", "-B", "-c", script], timeout=20))
    except (ValueError, subprocess.SubprocessError):
        return None


def atomic(path, after, before=None, backup_path=None):
    current = path.read_bytes() if path.exists() else None
    if current != before:
        raise ValueError("File changed during setup: " + path.name)
    if before == after:
        return None
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = None
    if before is not None:
        backup = backup_path or path.with_name(path.name+".before-mcp-"+uuid.uuid4().hex[:8]+".bak")
        backup.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with backup.open("xb") as handle:
            handle.write(before)
        if os.name != "nt":
            backup.chmod(0o600)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".mcp-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(after); stream.flush(); os.fsync(stream.fileno())
        if (path.read_bytes() if path.exists() else None) != before:
            raise ValueError("File changed during setup: " + path.name)
        os.replace(temporary, path)
        if path.read_bytes() != after:
            raise ValueError("Readback mismatch")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return str(backup) if backup else None


def owned(server, spec, text):
    if spec["kind"] == "http":
        return server.get("url", "").rstrip("/") == spec["url"]
    arguments = server.get("args", [])
    if not isinstance(arguments, list):
        return False
    if "-m" in arguments and arguments.index("-m")+1 < len(arguments) and arguments[arguments.index("-m")+1] == spec["module"]:
        return True
    return spec["name"] == "jev" and "# BEGIN codex-setup Jev MCP" in text and any(isinstance(a, str) and a.replace("\\", "/").endswith("/jev-evaluation/scripts/mcp_server.py") for a in arguments)


def plugin_endpoint(home, parsed, url):
    # Inspect manifests only for plugins explicitly enabled in this client config
    for plugin, setting in parsed.get("plugins", {}).items():
        if not isinstance(setting, dict) or setting.get("enabled") is not True or "@" not in plugin:
            continue
        name, registry = plugin.split("@", 1)
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", name) or not re.fullmatch(r"[a-zA-Z0-9_-]+", registry):
            continue
        folder = home/"plugins/cache"/registry/name
        for path in folder.glob("*/.mcp.json"):
            try:
                if path.stat().st_size <= 65536 and any(isinstance(item, dict) and item.get("url", "").rstrip("/") == url for item in json.loads(path.read_text()).get("mcpServers", {}).values()):
                    return plugin
            except (OSError, ValueError, AttributeError):
                continue
    return None


def toml_value(value):
    if isinstance(value, dict):
        return "{ " + ", ".join(json.dumps(key) + " = " + toml_value(item) for key, item in value.items()) + " }"
    return json.dumps(value, ensure_ascii=True)


def registration(text, name, server, *, existing=False):
    if existing:
        # Only the managed Jev script registration needs migration; preserve nested env settings
        pattern = re.compile(r"(?m)^(command|args|env_vars)[ \t]*=.*$")
        section = re.search(r"(?m)^\[mcp_servers\."+re.escape(name)+r"\][ \t]*\r?$", text)
        if not section:
            raise ValueError("Managed registration not found")
        following = re.search(r"(?m)^\[", text[section.end():])
        end = section.end()+following.start() if following else len(text)
        body = text[section.start():end]
        for key in ("command", "args", "env_vars"):
            replacement = key+" = "+toml_value(server[key])
            matches = list(re.finditer(r"(?m)^"+key+r"[ \t]*=.*$", body))
            if len(matches) > 1:
                raise ValueError("Ambiguous registration")
            body = body[:matches[0].start()]+replacement+body[matches[0].end():] if matches else body.rstrip()+"\n"+replacement+"\n"
        return text[:section.start()]+body+text[end:]
    lines = [f"# BEGIN codex-setup baseline {name}", f"[mcp_servers.{name}]"]
    for key, value in server.items():
        lines.append(key+" = "+toml_value(value))
    lines += [f"# END codex-setup baseline {name}", ""]
    return text.rstrip()+"\n\n"+"\n".join(lines)


def sync_skill(source, target):
    expected = {}
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if any(part in {"__pycache__", "build", "dist", ".git"} or part.endswith(".egg-info") for part in relative.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink() or path.suffix in {".key", ".pem"} or path.name.startswith(".env"):
            raise ValueError("Skill contains private or linked files")
        if path.is_file():
            expected[relative] = path.read_bytes()
    if Path("SKILL.md") not in expected:
        raise ValueError("Missing Skill source")
    present = {path.relative_to(target) for path in target.rglob("*") if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}}
    if present-set(expected):
        raise ValueError("Unknown installed Skill files; preserve and inspect")
    backups, changed = [], 0
    backup_root = target.parent.parent/"backups"/("jev-"+uuid.uuid4().hex[:12])
    for relative, content in expected.items():
        destination = target/relative
        before = destination.read_bytes() if destination.exists() else None
        if before != content:
            backup = atomic(destination, content, before, backup_root/relative)
            if backup: backups.append(backup)
            changed += 1
    if any((target/relative).read_bytes() != content for relative, content in expected.items()):
        raise ValueError("Skill mirror mismatch")
    return {"changed_files": changed, "matched_files": len(expected), "backups": backups}


def plan(args):
    if sys.version_info < (3, 11):
        raise ValueError("Bootstrap needs Python 3.11+; per-server requirements remain in the wheels")
    preset = json.loads((ROOT/"mcp/mcp_servers/presets/baseline.json").read_text(encoding="utf-8"))
    home = absolute(Path(os.environ.get("CODEX_HOME") or Path.home()/".codex"))
    config = absolute(args.config or home/"config.toml")
    state_path = home/"mcp-bootstrap.json"
    state = json.loads(state_path.read_text()) if state_path.is_file() else {"version": 1, "servers": {}}
    if state.get("version") != 1 or not isinstance(state.get("servers"), dict):
        raise ValueError("Invalid saved bootstrap settings")
    if args.cert:
        cert = absolute(args.cert)
        if not cert.is_file():
            raise ValueError("Certificate bundle must be an existing file")
        state["cert"] = str(cert)
    original = config.read_bytes() if config.exists() else None
    text = (original or b"").decode("utf-8-sig")
    parsed = tomllib.loads(text)
    bundle = absolute(args.bundle or (ROOT.parent if (ROOT.parent/"bundle.json").is_file() else ROOT/"dist/mcp/bootstrap"))
    wheels, bundle_problem = load_bundle(bundle, preset)
    entries = []
    for spec in preset["servers"]:
        if spec.get("optional") and not args.context7:
            continue
        name = spec["name"]
        existing = parsed.get("mcp_servers", {}).get(name)
        item = {"name": name, "spec": spec, "status": "new", "existing": existing is not None}
        if spec["kind"] == "http":
            provider = next((key for key, value in parsed.get("mcp_servers", {}).items() if value.get("url", "").rstrip("/") == spec["url"] and value.get("enabled", True)), None) or plugin_endpoint(home, parsed, spec["url"])
            if provider:
                item.update(status="reuse_provider", provider=provider)
            elif existing:
                item.update(status="preserve_existing", problem="Existing named registration is retained")
            else:
                item["registration"] = {"url": spec["url"], "enabled": True, "required": False}
            entries.append(item); continue
        if existing and not owned(existing, spec, text):
            item.update(status="conflict", problem="Unowned registration is preserved")
            entries.append(item); continue
        if existing:
            python = absolute(Path(existing["command"]))
            item["status"] = "reuse"
            item["registration"] = existing.copy()
            for option, field in (("--read-root", "read_roots"), ("--write-root", "write_roots")):
                item[field] = [value for i,value in enumerate(existing.get("args", [])) if i and existing["args"][i-1] == option and isinstance(value, str)]
        else:
            python = python_path(absolute(args.runtime_root or default_data_root()/"mcp")/name)
            roots = (args.read_root or state["servers"].get(name, {}).get("read_roots", [])) if spec["roots_required"] else []
            roots = [absolute(Path(root)) for root in roots]
            if any(not root.is_dir() for root in roots):
                raise ValueError("Read root must be an existing directory")
            item["read_roots"] = [str(root) for root in roots]
            if spec["roots_required"] and not roots:
                item.update(status="pending_roots", problem="Explicit --read-root is required")
            arguments = ["-I", "-B", "-m", spec["module"]]
            for root in roots:
                arguments += ["--read-root", str(root)]
            item["registration"] = {"command": str(python), "args": arguments, "enabled": True, "required": False, "enabled_tools": spec["tools"], "startup_timeout_sec": spec["startup_timeout_sec"], "tool_timeout_sec": spec["tool_timeout_sec"]}
            if spec.get("env_vars"):
                item["registration"]["env_vars"] = spec["env_vars"]
        item["python"] = str(python)
        item["runtime"] = str(python.parent.parent)
        if existing and name == "jev":
            item["registration"]["args"] = ["-I", "-B", "-m", spec["module"]]
            item["registration"]["env_vars"] = list(dict.fromkeys(existing.get("env_vars", [])+spec["env_vars"]))
        item["runtime_info"] = runtime_info(python, spec["packages"])
        item["wheels"] = [wheels[package] for package, version in spec["packages"].items() if package in wheels and wheels[package]["version"] == version]
        if len(item["wheels"]) != len(spec["packages"]) and item["status"] not in {"conflict", "pending_roots"}:
            item.update(status="pending_wheels", problem=bundle_problem or "Matching local wheels are missing")
        if python.exists() and item["runtime_info"] is None:
            item.update(status="pending_runtime", problem="Existing interpreter is unreadable or unhealthy; preserved")
        entries.append(item)
    return {"status": "preview", "preset": preset["name"], "config": str(config), "bundle": str(bundle), "state_file": str(state_path), "sync_jev_skill": not getattr(args, "no_skill_sync", False), "python_prerequisite": "3.11+ for bootstrap; native dependencies resolved per machine", "servers": entries}, (config, original, text, state_path, state, home)


def apply(report, context):
    config, original, text, state_path, state, home = context
    initial = tomllib.loads(text)
    updated = text
    applied = []
    for item in report["servers"]:
        if item["status"] not in {"new", "reuse"}:
            continue
        spec, name = item["spec"], item["name"]
        try:
            if spec["kind"] == "python":
                python, runtime = Path(item["python"]), Path(item["runtime"])
                if not python.exists():
                    if runtime.exists():
                        raise ValueError("Incomplete runtime preserved; select another --runtime-root")
                    venv.EnvBuilder(with_pip=True).create(runtime)
                info = item["runtime_info"]
                marker = runtime/"codex-mcp-wheels.json"
                expected = {wheel["name"]:wheel["sha256"] for wheel in item["wheels"]}
                previous = json.loads(marker.read_text()) if marker.is_file() else {}
                reinstall = any(previous.get(wheel["name"]) != wheel["sha256"] or not info or info["packages"].get(wheel["name"]) != wheel["version"] for wheel in item["wheels"])
                if reinstall:
                    for wheel in item["wheels"]:
                        if wheel_info(Path(wheel["path"])) != {key: wheel[key] for key in ("name", "version", "sha256")}:
                            raise ValueError("Wheel changed after preview")
                    paths = [wheel["path"] for wheel in item["wheels"]]
                    pip = [str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "--timeout", "20", "--retries", "1", "--find-links", report["bundle"]]
                    if state.get("cert"):
                        pip += ["--cert", state["cert"]]
                    run(pip+["--no-deps", "--force-reinstall", *paths], timeout=180)
                    run(pip+paths, timeout=600)
                    run([str(python), "-m", "pip", "check"])
                    info = runtime_info(python, spec["packages"])
                    if not info or info["packages"] != spec["packages"]:
                        raise ValueError("Installed package readback mismatch")
                    atomic(marker, (json.dumps(expected, sort_keys=True)+"\n").encode(), marker.read_bytes() if marker.exists() else None)
                else:
                    run([str(python), "-m", "pip", "check"])
                item["verification"] = json.loads(run([str(python), "-I", "-B", "-m", spec["verify_module"]], timeout=330))
                item["packages_reinstalled"] = reinstall
                if name == "jev":
                    output = run([str(python), "-I", "-B", "-c", "from codex_jev_mcp import jev; from types import SimpleNamespace; import json; result,_=jev.run(SimpleNamespace(command='doctor',key_file=None,online=False,timeout=8,retries=1)); print(json.dumps({key:result[key] for key in ('credential_available','credential_source','reason') if key in result}))"])
                    item["credential_available"] = json.loads(output)["credential_available"]
                    item["credential_reason"] = json.loads(output).get("reason")
                    item["credential_setup"] = "ready" if item["credential_available"] else "pending_access" if item["credential_reason"] == "credential_file_unreadable" else "pending_setup"
                    if report["sync_jev_skill"]:
                        source = ROOT/"skills/jev-evaluation"
                        target = (home/"skills" if (home/"skills/jev-evaluation/SKILL.md").exists() or os.environ.get("CODEX_HOME") else Path.home()/".agents/skills")/"jev-evaluation"
                        item["skill_sync"] = sync_skill(source, target)
                    else:
                        item["skill_sync"] = {"status":"skipped_by_option"}
                if item.get("read_roots") and not item["existing"]:
                    state["servers"][name] = {"read_roots": item["read_roots"]}
            registration_value = item["registration"]
            if item["existing"]:
                if registration_value != initial.get("mcp_servers", {}).get(name):
                    updated = registration(updated, name, registration_value, existing=True)
            else:
                updated = registration(updated, name, registration_value)
            item["status"] = "ready"
            applied.append(name)
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            item.update(status="failed", problem=str(exc) if isinstance(exc, ValueError) else "Local runtime operation unavailable")
    parsed = tomllib.loads(updated)
    changed_servers = {name for name in applied if parsed.get("mcp_servers", {}).get(name) != initial.get("mcp_servers", {}).get(name)}
    old_others = {key:value for key,value in initial.get("mcp_servers",{}).items() if key not in changed_servers}
    new_others = {key:value for key,value in parsed.get("mcp_servers",{}).items() if key not in changed_servers}
    if old_others != new_others or {key:value for key,value in initial.items() if key != "mcp_servers"} != {key:value for key,value in parsed.items() if key != "mcp_servers"}:
        raise ValueError("Unrelated config changed")
    after = (b"\xef\xbb\xbf" if original and original.startswith(b"\xef\xbb\xbf") else b"")+updated.encode("utf-8")
    report["backup"] = atomic(config, after, original) if updated != text else None
    state_before = state_path.read_bytes() if state_path.exists() else None
    if state["servers"] or state.get("cert"):
        atomic(state_path, (json.dumps(state, indent=2)+"\n").encode(), state_before)
    report.update(status="applied", restart_required=bool(changed_servers), changed_servers=sorted(changed_servers))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--read-root", action="append", type=Path, default=[])
    parser.add_argument("--context7", action="store_true", help="Opt in to hosted Context7; OAuth is separate via codex mcp login context7")
    parser.add_argument("--cert", type=Path, help="Explicit PEM certificate bundle for pip; never disable TLS verification")
    parser.add_argument("--no-skill-sync", action="store_true", help="Install/verify runtimes only when another owner manages the Skill mirror")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        report, context = plan(args)
        if args.apply:
            report = apply(report, context)
        public = report.copy()
        public["servers"] = [{key:value for key,value in item.items() if key != "registration"} for item in report["servers"]]
        print(json.dumps(public, ensure_ascii=True, indent=2))
        return 1 if any(item["status"] == "failed" for item in report["servers"]) else 0
    except (ValueError, OSError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status":"failed", "reason":str(exc)}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
