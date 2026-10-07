#!/usr/bin/env python3
"""Check optional development-tool prerequisites without installing or changing settings."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tomllib

if __package__:
    from .bootstrap_mcp import default_data_root, plugin_endpoint
else:
    from bootstrap_mcp import default_data_root, plugin_endpoint

ROOT = Path(__file__).resolve().parents[2]


def system_name():
    return {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux" if sys.platform.startswith("linux") else sys.platform)


def npm_prefix():
    return default_data_root()/"tools/npm"


def find_command(name):
    if name == "rtk":
        managed_native = default_data_root()/("tools/native/rtk/rtk.exe" if os.name == "nt" else "tools/native/rtk/rtk")
        if managed_native.is_file():
            return str(managed_native)
    path = shutil.which(name + ".cmd") if os.name == "nt" and name in {"npm", "npx", "playwright-cli", "playwright-mcp", "codex", "t3"} else None
    path = path or shutil.which(name)
    if path:
        return path
    filename = name + ".cmd" if os.name == "nt" else name
    managed = npm_prefix()/(filename if os.name == "nt" else "bin/" + filename)
    if managed.is_file():
        return str(managed)
    if os.name == "nt" and name == "rtk":
        local = default_data_root().parent
        matches = list((local/"Microsoft/WinGet/Packages").glob("rtk-ai.rtk_*/rtk.exe"))
        if len(matches) == 1:
            return str(matches[0])
    return None


def tool_spec(name, manifest, interface="native"):
    spec = manifest["tools"][name]
    if interface == "native":
        return spec
    mode = spec.get("interfaces", {}).get(interface)
    if mode is None:
        if interface == "mcp" and spec.get("kind") in {"library", "reference"}:
            raise ValueError("This catalog entry is a " + spec["kind"] + ", not an MCP server: " + name)
        if interface == "mcp" and (spec.get("mcp") or spec.get("manual_setup")):
            return spec
        raise ValueError("Unsupported interface for " + name + ": " + interface)
    return spec | mode


def profile_tools(manifest, profile="all"):
    profiles = manifest.get("profiles", {"all": {"groups": []}})
    if profile not in profiles:
        raise ValueError("Unknown tool profile: " + profile)
    groups = profiles[profile]["groups"]
    selected = profiles[profile].get("tools", [])
    return {name: spec for name, spec in manifest["tools"].items()
            if (not groups and not selected) or set(spec.get("categories", [spec.get("group")])).intersection(groups) or name in selected}


def dependency_missing(requirement, system):
    if "native_mcp" in requirement:
        return not native_mcp_command(requirement["native_mcp"])
    if "app" in requirement:
        if system == "macos":
            return not any((root/requirement["app"]).is_dir() for root in (Path.home()/"Applications", Path("/Applications")))
        if system == "linux":
            return not find_command(requirement["linux_command"])
        winget = find_command("winget")
        if not winget:
            return True
        try:
            result = subprocess.run([winget, "list", "--id", requirement["windows_package"], "--exact", "--source", "winget", "--disable-interactivity"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, check=False)
            return result.returncode != 0 or requirement["windows_package"] not in result.stdout
        except (OSError, subprocess.SubprocessError):
            return True
    command = find_command(requirement["command"])
    if not command:
        return True
    minimum = requirement.get("minimum_version")
    ranges = requirement.get("version_ranges")
    if not minimum and not ranges and not requirement.get("version_args"):
        return False
    try:
        result = subprocess.run([command, *requirement.get("version_args", ["--version"])], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, check=False)
        current = version(result.stdout + result.stderr) if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        current = None
    return current is None or bool(minimum and current < tuple(minimum)) or bool(ranges and not any(
        current >= tuple(item["minimum"]) and (not item.get("maximum_exclusive") or current < tuple(item["maximum_exclusive"]))
        for item in ranges
    ))


def mcp_state(spec, config=None):
    home = Path(os.environ.get("CODEX_HOME") or Path.home()/".codex")
    config = config or home/"config.toml"
    parsed = tomllib.loads(config.read_text(encoding="utf-8-sig")) if config.exists() else {}
    for name, server in parsed.get("mcp_servers", {}).items():
        if not server.get("enabled", True):
            continue
        arguments = server.get("args", [])
        matches = (server.get("url", "").rstrip("/") in {spec["url"].rstrip("/"), spec["url"].rstrip("/") + "/oauth"}) if "url" in spec else False
        if spec.get("module"):
            matches = "-m" in arguments and arguments[arguments.index("-m")+1:arguments.index("-m")+2] == [spec["module"]]
            if spec.get("tool"):
                matches = matches and "--tool" in arguments and arguments[arguments.index("--tool")+1:arguments.index("--tool")+2] == [spec["tool"]]
        elif spec.get("entry_suffix"):
            matches = any(isinstance(arg, str) and arg.replace("\\", "/").endswith(spec["entry_suffix"])
                          and (not spec.get("entry_directory") or "/"+spec["entry_directory"]+"/" in arg.replace("\\", "/")) for arg in arguments)
            if matches and spec.get("config_suffix"):
                matches = "--config" in arguments and any(
                    isinstance(arg, str) and arg.replace("\\", "/").endswith(spec["config_suffix"])
                    for arg in arguments[arguments.index("--config") + 1:arguments.index("--config") + 2]
                )
        elif spec.get("native_command"):
            matches = Path(server.get("command", "")).name in spec["native_command"]
        if matches:
            return "registered", name
    provider = plugin_endpoint(home, parsed, spec["url"]) if "url" in spec else None
    if provider:
        return "registered", provider
    return ("conflict" if spec["name"] in parsed.get("mcp_servers", {}) else "missing"), None


def native_mcp_command(name):
    if name != "repoprompt":
        return None
    for command in ("repoprompt-mcp", "rpce-cli"):
        path = find_command(command)
        if path:
            return path
    for root in (Path.home()/"Applications", Path("/Applications")):
        path = root/"RepoPrompt CE.app/Contents/MacOS/repoprompt-mcp"
        if path.is_file():
            return str(path)
    return None


def version(text):
    match = re.search(r"\b(?:v)?(\d+)\.(\d+)(?:\.(\d+))?", text)
    return tuple(int(part or 0) for part in match.groups()) if match else None


def check(name, spec, system, config=None):
    report = {"tool": name, "kind": spec.get("kind", "development-tool"), "origin": spec.get("origin"), "source": spec.get("source"), "platform": system, "missing": [], "manual_checks": spec.get("manual_checks", []), "install": spec["install"].get(system, spec["install"].get("all"))}
    if system not in spec["platforms"]:
        return report | {"status": "unsupported_platform"}
    home = Path(os.environ.get("CODEX_HOME") or Path.home()/".codex")
    settings = config or home/"config.toml"
    parsed = tomllib.loads(settings.read_text(encoding="utf-8-sig")) if settings.exists() else {}
    providers = [key for key, value in parsed.get("plugins", {}).items() if isinstance(value, dict) and value.get("enabled") and key.split("@")[0] in spec.get("prefer_plugins", [])]
    if providers:
        return report | {"status": "manual_verification_required", "provider": providers[0], "manual_checks": ["Existing plugin selected; verify account authorization and a safe tool call"]}
    report["credential_env"] = {key: "available" if os.environ.get(key) else "missing" for key in spec.get("credential_env", [])}
    report["service_requirements"] = spec.get("service_requirements", [])
    if spec.get("python_wheel"):
        report["python_wheel"] = spec["python_wheel"]
    if spec.get("minimum_python") and sys.version_info < tuple(spec["minimum_python"]):
        report["missing"].append("Python " + ".".join(map(str, spec["minimum_python"])) + "+ for the selected MCP")
    if spec.get("minimum_macos"):
        current = version(platform.mac_ver()[0])
        if current is None or current < tuple(spec["minimum_macos"]):
            report["missing"].append("macOS " + ".".join(map(str, spec["minimum_macos"][:2])) + "+")
    for requirement in spec["dependencies"]:
        if dependency_missing(requirement, system):
            minimum = requirement.get("minimum_version")
            label = requirement.get("command") or requirement.get("native_mcp") or (requirement.get("windows_package") if system == "windows" else requirement.get("linux_command") if system == "linux" else requirement["app"])
            report["missing"].append(label + (" " + ".".join(map(str, minimum)) + "+ (missing, old or unreadable version)" if minimum else ""))
    if spec.get("mcp"):
        state, provider = mcp_state(spec["mcp"], config)
        report["mcp_status"] = state
        report["provider"] = provider
        if state != "registered":
            report["missing"].append("MCP registration: " + state)
        elif spec["mcp"].get("module"):
            home = Path(os.environ.get("CODEX_HOME") or Path.home()/".codex")
            parsed = tomllib.loads((config or home/"config.toml").read_text(encoding="utf-8-sig"))
            command = parsed["mcp_servers"][provider].get("command", "")
            try:
                probe = subprocess.run([command, "-I", "-B", "-c", "import development_tool_mcp.server; import mcp"], capture_output=True, timeout=10, check=False)
                ready = probe.returncode == 0
            except (OSError, subprocess.SubprocessError):
                ready = False
            if not ready:
                report["missing"].append("MCP Python runtime or package")
        elif spec["mcp"].get("entry_suffix") and provider in parsed.get("mcp_servers", {}):
            server = parsed["mcp_servers"][provider]
            if not Path(server.get("command", "")).is_file() or not any(Path(arg).is_file() for arg in server.get("args", []) if isinstance(arg, str) and arg.replace("\\", "/").endswith(spec["mcp"]["entry_suffix"])):
                report["missing"].append("MCP Node runtime or package")
            if spec["mcp"].get("config_suffix"):
                arguments = server.get("args", [])
                selected = arguments[arguments.index("--config") + 1] if "--config" in arguments and arguments.index("--config") + 1 < len(arguments) else None
                if not selected or not Path(selected).is_file():
                    report["missing"].append("Selected proofreading configuration")
        elif spec["mcp"].get("native_command") and provider in parsed.get("mcp_servers", {}):
            command = parsed["mcp_servers"][provider].get("command", "")
            if not Path(command).is_file() and not find_command(command):
                report["missing"].append("MCP native executable")
            elif spec["mcp"].get("health_args"):
                try:
                    probe = subprocess.run([command, *parsed["mcp_servers"][provider].get("args", []), *spec["mcp"]["health_args"]], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15, check=False)
                    if probe.returncode:
                        report["missing"].append((probe.stderr or probe.stdout).strip() or "MCP prerequisite check failed")
                except (OSError, subprocess.SubprocessError) as error:
                    report["missing"].append("MCP prerequisite check failed: " + str(error))
    if spec.get("manual_setup"):
        report["manual_setup"] = spec["manual_setup"]
        return report | {"status": "manual_setup_required"}
    return report | {"status": "missing_dependencies" if report["missing"] else "manual_verification_required"}


def main(argv=None):
    manifest = json.loads((ROOT / "mcp/tools/development-tools.requirements.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported requirements schema")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", action="append", required=True, choices=manifest["tools"], help="Tool to check; repeat to check several tools")
    parser.add_argument("--interface", choices=["native", "mcp"], default="native", help="Check the existing CLI/app mode or the selected MCP integration")
    args = parser.parse_args(argv)
    system = system_name()
    reports = [check(name, tool_spec(name, manifest, args.interface), system) | {"interface": args.interface} for name in dict.fromkeys(args.tool)]
    print(json.dumps({"status": "checked", "install_performed": False, "tools": reports}, ensure_ascii=True, indent=2))
    return 1 if any(item["status"] in {"missing_dependencies", "unsupported_platform", "manual_setup_required"} for item in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
