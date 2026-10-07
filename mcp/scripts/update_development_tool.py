#!/usr/bin/env python3
"""Preview or update exactly one installed tool through its reviewed official channel."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import importlib.metadata
import platform
import re
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.parse
import urllib.request
import zipfile

if __package__:
    from .bootstrap_mcp import absolute, atomic, default_data_root, toml_value
    from .check_development_tools import ROOT, find_command, npm_prefix, system_name, tool_spec, version
    from .install_development_tool import install_command
    from .plan_guard import require_same_plan
else:
    from bootstrap_mcp import absolute, atomic, default_data_root, toml_value
    from check_development_tools import ROOT, find_command, npm_prefix, system_name, tool_spec, version
    from install_development_tool import install_command
    from plan_guard import require_same_plan


def fetch(url, limit=4_000_000):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"registry.npmjs.org", "pypi.org", "api.github.com", "github.com"} or parsed.username or parsed.password:
        raise ValueError("Unsupported update source")
    request = urllib.request.Request(url, headers={"User-Agent": "codex-tool-setup", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Update download exceeds the selected limit")
    return data


def fetch_json(url):
    return json.loads(fetch(url))


def stable(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise ValueError("Only a verified stable version is supported: " + str(value))
    return tuple(map(int, value.split(".")))


def installed_python(python, package):
    result = subprocess.run([str(python), "-I", "-c", "import importlib.metadata; print(importlib.metadata.version(" + repr(package) + "))"], capture_output=True, text=True, timeout=15, check=False)
    if result.returncode:
        raise ValueError("Selected Python package is not installed")
    return result.stdout.strip()


def installed_npm_prefix(spec, config, fallback):
    packages = spec.get("packages", {})
    if not packages or any((fallback/"node_modules"/name/"package.json").is_file() for name in packages):
        return fallback
    # Desktop and a standalone CLI can expose different user data prefixes
    candidates = set()
    if config.is_file():
        settings = tomllib.loads(config.read_text(encoding="utf-8-sig"))
        server = settings.get("mcp_servers", {}).get(spec.get("mcp", {}).get("name"), {})
        for value in [server.get("command", ""), *server.get("args", [])]:
            path = Path(value)
            if path.is_absolute() and "node_modules" in path.parts:
                candidate = Path(*path.parts[:path.parts.index("node_modules")]).resolve()
                if candidate.is_relative_to(Path.home().resolve()) and candidate.parts[-3:] == ("codex-setup", "tools", "npm"):
                    if any((candidate/"node_modules"/name/"package.json").is_file() for name in packages):
                        candidates.add(candidate)
    if len(candidates) > 1:
        raise ValueError("Multiple managed npm prefixes found; select one with --npm-prefix")
    return next(iter(candidates), fallback)


def release_binary(system):
    release = fetch_json("https://api.github.com/repos/rtk-ai/rtk/releases/latest")
    target = release["tag_name"].removeprefix("v")
    stable(target)
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "x86_64": "x86_64", "arm64": "aarch64", "aarch64": "aarch64"}.get(machine)
    suffix = {"windows": "pc-windows-msvc.zip", "macos": "apple-darwin.tar.gz", "linux": "unknown-linux-gnu.tar.gz"}.get(system)
    name = f"rtk-{arch}-{suffix}"
    assets = [a for a in release.get("assets", []) if a["name"] == name]
    if len(assets) != 1 or not re.fullmatch(r"sha256:[a-f0-9]{64}", assets[0].get("digest") or ""):
        raise ValueError("No matching RTK release binary with a verified SHA-256 digest")
    asset = assets[0]
    expected_url = f"https://github.com/rtk-ai/rtk/releases/download/v{target}/{name}"
    if asset["browser_download_url"] != expected_url or release.get("prerelease") or release.get("draft"):
        raise ValueError("Unexpected RTK release source")
    return {"version": target, "url": expected_url, "sha256": asset["digest"][7:], "filename": name}


def python_environment(name):
    root = default_data_root()/"mcp_optional"/name
    marker = root/".codex-setup-managed"
    if root.is_symlink() or not marker.is_file() or marker.read_text(encoding="utf-8").strip() != name:
        raise ValueError("Only the selected setup-managed Python environment can be updated")
    python = root/("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        raise ValueError("Selected Python environment is unavailable")
    return python


def setup_release():
    release = fetch_json("https://api.github.com/repos/gaze9999/codex-toolkit/releases/latest")
    if release.get("draft") or release.get("prerelease") or not re.fullmatch(r"v\d+\.\d+\.\d+", release["tag_name"]):
        raise ValueError("No verified stable setup release")
    urls = {a["name"]: a["browser_download_url"] for a in release["assets"]}
    base = "https://github.com/gaze9999/codex-toolkit/releases/download/" + release["tag_name"] + "/"
    if urls.get("mcp-release-manifest.json") != base + "mcp-release-manifest.json":
        raise ValueError("Setup release manifest is unavailable")
    manifest = fetch_json(urls["mcp-release-manifest.json"])
    if manifest.get("producer") != "codex-setup.prepare_mcp_release.v1" or manifest.get("tag") != release["tag_name"]:
        raise ValueError("Unexpected setup release manifest")
    matches = [a for a in manifest["assets"] if re.fullmatch(r"codex_tool_setup-\d+\.\d+\.\d+-py3-none-any.whl", a["name"])]
    if len(matches) != 1:
        raise ValueError("Setup release wheel is missing or ambiguous")
    item = matches[0]
    if urls.get(item["name"]) != base + item["name"] or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"]):
        raise ValueError("Unexpected setup wheel asset")
    return item | {"url": urls[item["name"]], "version": item["name"].split("-")[1]}


def update_plan(name, manifest, system, prefix, config, interface="native"):
    result = {"tool": name, "steps": [], "blocked": [], "shared_tools": [], "checks": []}
    if name == "setup":
        python = Path(sys.executable)
        if sys.prefix == sys.base_prefix:
            raise ValueError("Run setup self-update from the independent venv containing the setup wheel")
        distribution = importlib.metadata.distribution("codex-tool-setup")
        if not Path(distribution.locate_file("")).resolve().is_relative_to(Path(sys.prefix).resolve()):
            raise ValueError("Setup wheel must belong to the running independent environment")
        current = installed_python(python, "codex-tool-setup")
        item = setup_release()
        result["current"] = current
        result["latest"] = item["version"]
        if stable(item["version"]) > stable(current):
            result["steps"].append({"kind": "setup_wheel", "python": str(python), "previous": current, **item})
        result["checks"].append("New processes use the updated packaged catalog; local account configuration is preserved")
        return result
    spec = tool_spec(name, manifest, interface)
    if system not in spec["platforms"]:
        result["blocked"].append("Unsupported platform: " + system)
        return result
    if spec.get("manual_setup"):
        result["blocked"].append(spec["manual_setup"])
        return result
    if spec.get("prefer_plugins") and config.is_file():
        settings = tomllib.loads(config.read_text(encoding="utf-8-sig"))
        if any(isinstance(value, dict) and value.get("enabled") and name.split("@")[0] in spec["prefer_plugins"] for name, value in settings.get("plugins", {}).items()):
            result["blocked"].append("Use the selected client's plugin update and authorization flow")
            return result
    if name == "rtk":
        command = find_command("rtk")
        if not command:
            result["blocked"].append("Install the selected RTK tool first")
            return result
        probe = subprocess.run([command, "--version"], capture_output=True, text=True, timeout=15, check=False)
        current = version(probe.stdout) if probe.returncode == 0 else None
        if current is None:
            raise ValueError("Installed RTK version is unreadable")
        item = release_binary(system)
        result.update(current=".".join(map(str, current)), latest=item["version"])
        if stable(item["version"]) > current:
            result["steps"].append({"kind": "rtk_binary", "previous_executable": command, **item})
        result["checks"].append("Only a matching setup RTK adapter executable may change; roots and permissions remain intact")
        return result
    if spec.get("packages"):
        command_packages = {package for package in spec["packages"] if any(part.startswith(package + "@") for recipe in spec.get("automatic_install", {}).values() for cmd in recipe.get("commands", []) for part in cmd)}
        selected = command_packages or set(spec["packages"])
        missing = []
        for package in sorted(selected):
            path = prefix/"node_modules"/package/"package.json"
            if not path.is_file():
                missing.append(package)
                continue
            current = json.loads(path.read_text(encoding="utf-8"))["version"]
            latest = fetch_json("https://registry.npmjs.org/" + urllib.parse.quote(package, safe="@/") + "/latest")
            if latest.get("name") != package:
                raise ValueError("Unexpected npm package metadata")
            result.setdefault("packages", []).append({"package": package, "current": current, "latest": latest["version"]})
            if stable(latest["version"]) > stable(current):
                result["steps"].append({"kind": "npm", "package": package, "previous": current, "version": latest["version"], "engines": latest.get("engines", {}), "source": "https://registry.npmjs.org/" + package})
        if missing:
            result["blocked"].append("Selected package is not installed in this setup prefix: " + ", ".join(missing))
        changed = {s["package"] for s in result["steps"]}
        result["shared_tools"] = [n for n, other in manifest["tools"].items() if n != name and changed.intersection(other.get("packages", {}))]
        result["checks"].append("npm engine-strict checks the target runtime; existing entrypoints and language rules must remain usable")
        return result
    if spec.get("python_package"):
        if spec.get("python_source"):
            result["blocked"].append("Install the reviewed wheel from a refreshed setup bundle; this local adapter has no PyPI update channel")
            return result
        package, _ = spec["python_package"].split("==", 1)
        python = python_environment(name)
        current = installed_python(python, package)
        latest = fetch_json("https://pypi.org/pypi/" + urllib.parse.quote(package, safe="") + "/json")
        if latest["info"].get("name", package).lower().replace("_", "-") != package.lower().replace("_", "-"):
            raise ValueError("Unexpected PyPI package metadata")
        target = latest["info"]["version"]
        result.update(current=current, latest=target)
        if stable(target) > stable(current):
            result["steps"].append({"kind": "pip", "package": package, "previous": current, "version": target, "python": str(python), "requires_python": latest["info"].get("requires_python"), "source": "https://pypi.org/project/" + package})
        result["checks"].append("pip checks Python compatibility in this tool's isolated environment; client tool discovery needs a reload")
        return result
    if spec.get("mcp", {}).get("url"):
        result["checks"].append("Hosted server updates are provider-managed; recheck authentication, quota and actual tools after client reload")
    else:
        result["blocked"].append("Use the selected app/package manager or a refreshed setup release; no automatic update channel has been verified")
    return result


def rtk_payload(data, filename, executable):
    if filename.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = [n for n in archive.namelist() if Path(n).name == executable]
            if len(names) != 1 or archive.getinfo(names[0]).file_size > 100_000_000:
                raise ValueError("Unexpected RTK archive contents")
            return archive.read(names[0])
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = [m for m in archive.getmembers() if m.isfile() and Path(m.name).name == executable]
        if len(members) != 1 or members[0].size > 100_000_000:
            raise ValueError("Unexpected RTK archive contents")
        return archive.extractfile(members[0]).read()


def retarget_rtk(config, previous, target):
    if not config.is_file():
        return None
    before = config.read_bytes()
    text = before.decode("utf-8-sig")
    parsed = tomllib.loads(text)
    changed = []
    for name, server in parsed.get("mcp_servers", {}).items():
        args = server.get("args", [])
        if "-m" not in args or args[args.index("-m") + 1:args.index("-m") + 2] != ["development_tool_mcp.server"] or "--tool" not in args or args[args.index("--tool") + 1:args.index("--tool") + 2] != ["rtk"] or "--executable" not in args:
            continue
        index = args.index("--executable") + 1
        if index >= len(args) or os.path.normcase(os.path.abspath(args[index])) != os.path.normcase(os.path.abspath(previous)):
            continue  # Independently customized adapters retain their executable
        new_args = [*args[:index], str(target), *args[index + 1:]]
        section = re.search(r"(?m)^\[mcp_servers\." + re.escape(name) + r"\][ \t]*\r?$", text)
        if not section:
            raise ValueError("RTK entry uses an unsupported TOML form; preserve it for manual migration")
        end_match = re.search(r"(?m)^\[", text[section.end():])
        end = section.end() + end_match.start() if end_match else len(text)
        body = text[section.start():end]
        matches = list(re.finditer(r"(?m)^args[ \t]*=[ \t]*\[.*\][ \t]*\r?$", body))
        if len(matches) != 1:
            raise ValueError("RTK args use an unsupported TOML form; preserve them for manual migration")
        match = matches[0]
        body = body[:match.start()] + "args = " + toml_value(new_args) + body[match.end():]
        text = text[:section.start()] + body + text[end:]
        parsed["mcp_servers"][name]["args"] = new_args
        changed.append(name)
    if not changed:
        return None
    if tomllib.loads(text) != parsed:
        raise ValueError("Unrelated Codex settings changed; RTK migration cancelled")
    return atomic(config, text.encode("utf-8"), before)


def apply_update(planned, prefix, config, *, yes=False):
    if planned["blocked"]:
        raise ValueError("Resolve the selected update prerequisites first")
    if not planned["steps"]:
        return []
    if not yes and (not sys.stdin.isatty() or input("Update only this tool and the displayed shared packages? [y/N] ").strip().lower() not in {"y", "yes"}):
        return [{"status": "declined"}]
    env = dict(os.environ, PYTHONUTF8="1", RTK_TELEMETRY_DISABLED="1")
    receipt_dir = default_data_root()/"tools/update-history"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = receipt_dir/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + "-" + planned["tool"] + ".json")
    receipt.write_text(json.dumps(planned, indent=2) + "\n", encoding="utf-8")
    completed = []
    npm_steps = [s for s in planned["steps"] if s["kind"] == "npm"]
    if npm_steps:
        command = install_command(["npm", "install", "-g", "--engine-strict", "--prefix", str(prefix), *[s["package"] + "@" + s["version"] for s in npm_steps]], env)
        subprocess.run(command, env=env, check=True)
        for s in npm_steps:
            current = json.loads((prefix/"node_modules"/s["package"]/"package.json").read_text(encoding="utf-8"))["version"]
            if current != s["version"]:
                raise ValueError("Installed npm version differs from the preview; consult " + str(receipt))
        completed += [{"package": s["package"], "version": s["version"]} for s in npm_steps]
    for step in planned["steps"]:
        if step["kind"] == "pip":
            subprocess.run([step["python"], "-I", "-m", "pip", "install", "--upgrade", step["package"] + "==" + step["version"]], env=env, check=True)
            if installed_python(step["python"], step["package"]) != step["version"]:
                raise ValueError("Installed Python version differs from preview")
            completed.append({"package": step["package"], "version": step["version"]})
        elif step["kind"] in {"rtk_binary", "setup_wheel"}:
            data = fetch(step["url"], 100_000_000)
            if hashlib.sha256(data).hexdigest() != step["sha256"] or (step.get("size") and len(data) != step["size"]):
                raise ValueError("Downloaded asset checksum or size mismatch; it was not installed")
            if step["kind"] == "setup_wheel":
                with tempfile.TemporaryDirectory(prefix="codex-setup-update-") as temp:
                    wheel = Path(temp)/step["name"]
                    wheel.write_bytes(data)
                    subprocess.run([step["python"], "-I", "-m", "pip", "install", "--upgrade", str(wheel)], env=env, check=True)
                completed.append({"package": "codex-tool-setup", "version": installed_python(step["python"], "codex-tool-setup")})
            else:
                filename = "rtk.exe" if os.name == "nt" else "rtk"
                target = default_data_root()/"tools/native/rtk"/filename
                payload = rtk_payload(data, step["filename"], filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                before = target.read_bytes() if target.exists() else None
                backup = atomic(target, payload, before)
                if os.name != "nt":
                    target.chmod(0o755)
                probe = subprocess.run([str(target), "--version"], capture_output=True, text=True, timeout=15, check=False, env=env)
                if probe.returncode or version(probe.stdout) != stable(step["version"]):
                    if before is not None:
                        atomic(target, before, payload)
                    elif target.read_bytes() == payload:
                        target.unlink()
                    raise ValueError("RTK version verification failed; previous managed binary restored when present")
                config_backup = retarget_rtk(config, step["previous_executable"], target)
                completed.append({"package": "rtk", "version": step["version"], "binary": str(target), "backup": backup, "config_backup": config_backup})
    return [{"receipt": str(receipt)}, *completed]


def main(argv=None):
    manifest = json.loads((ROOT/"mcp/tools/development-tools.requirements.json").read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", required=True, choices=[*manifest["tools"], "setup"], action="append")
    parser.add_argument("--interface", choices=["native", "mcp"], default="native")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--npm-prefix", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-plan-sha256", help=argparse.SUPPRESS)
    parser.add_argument("--yes", action="store_true", help="For already authorized noninteractive updates of this one tool")
    args = parser.parse_args(argv)
    if len(args.tool) != 1:
        parser.error("Select exactly one --tool per invocation")
    selected = args.tool[0]
    prefix = absolute(args.npm_prefix or npm_prefix())
    config = absolute(args.config or Path(os.environ.get("CODEX_HOME") or Path.home()/".codex")/"config.toml")
    try:
        if selected != "setup" and args.npm_prefix is None:
            prefix = installed_npm_prefix(tool_spec(selected, manifest, args.interface), config, prefix)
        planned = update_plan(selected, manifest, system_name(), prefix, config, args.interface)
        print(json.dumps(planned, ensure_ascii=False, indent=2))
        if args.apply:
            require_same_plan(planned, args.expected_plan_sha256)
            print(json.dumps({"completed": apply_update(planned, prefix, config, yes=args.yes)}, ensure_ascii=False, indent=2))
        return 1 if planned["blocked"] else 0
    except (OSError, ValueError, KeyError, importlib.metadata.PackageNotFoundError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "update_unavailable", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
