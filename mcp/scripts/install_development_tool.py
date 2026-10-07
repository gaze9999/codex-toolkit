#!/usr/bin/env python3
"""Preview or install one optional development tool and only its missing prerequisites."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
from urllib.parse import urlparse

if __package__:
    from .installer_language import InstallerUi, open_chinese_guide
    from .plan_guard import require_same_plan
    from .bootstrap_mcp import absolute, atomic, registration, default_data_root, digest, wheel_info
    from .check_development_tools import ROOT, check, dependency_missing, find_command, mcp_state, native_mcp_command, npm_prefix, system_name, tool_spec, profile_tools
else:
    from installer_language import InstallerUi, open_chinese_guide
    from plan_guard import require_same_plan
    from bootstrap_mcp import absolute, atomic, registration, default_data_root, digest, wheel_info
    from check_development_tools import ROOT, check, dependency_missing, find_command, mcp_state, native_mcp_command, npm_prefix, system_name, tool_spec, profile_tools


def recipe_step(name, recipe, prefix):
    values = {"npm_prefix": str(prefix), "app_dir": str(Path.home()/"Applications")}
    return {"component": name, "source": recipe.get("source"), "version": recipe.get("version"), "scope": recipe.get("scope"),
            "commands": [[part.format(**values) for part in cmd] for cmd in recipe.get("commands", [])], "action": recipe.get("action")}


def verified_wheel(folder, requirement):
    package, version = requirement.split("==", 1)
    folder = absolute(folder)
    manifest = json.loads((folder / "mcp-release-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("producer") != "codex-setup.prepare_mcp_release.v1":
        raise ValueError("Use a wheel directory with the setup's release manifest")
    prefix = package.replace("-", "_") + "-" + version + "-"
    matches = [item for item in manifest["assets"] if item["name"].startswith(prefix) and item["name"].endswith(".whl")]
    if len(matches) != 1:
        raise ValueError("Missing or ambiguous selected wheel: " + requirement)
    item = matches[0]
    if Path(item["name"]).name != item["name"]:
        raise ValueError("Unsafe wheel filename")
    path = folder / item["name"]
    if path.is_symlink() or not path.is_file():
        raise ValueError("Selected wheel is missing or unsafe")
    data = path.read_bytes()
    if len(data) != item["size"] or digest(data) != item["sha256"]:
        raise ValueError("Selected wheel checksum mismatch")
    info = wheel_info(path)
    if info["name"].lower().replace("_", "-") != package.lower().replace("_", "-") or info["version"] != version:
        raise ValueError("Selected wheel metadata mismatch")
    return path


def plan(name, manifest, system, prefix, config, browser=None, interface="native", *, server_url=None, token_env_var=None, mcp_executable=None, read_roots=(), feeds_path=None, wheel_dir=None):
    spec = dict(tool_spec(name, manifest, interface))
    if spec.get("custom_endpoint"):
        if server_url:
            url = urlparse(server_url)
            if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError("Use a credential-free HTTP(S) server URL without query or fragment")
            spec["mcp"] = spec["mcp"] | {"url": server_url.rstrip("/")}
        else:
            spec["manual_setup"] = "Provide your existing Home Assistant MCP endpoint using --server-url; enable the integration and approve exposed entities first"
    if token_env_var:
        if not token_env_var.isidentifier() or not spec.get("mcp", {}).get("url"):
            raise ValueError("--token-env-var requires a valid environment-variable name and an HTTP MCP")
        spec["mcp"] = spec["mcp"] | {"registration": spec["mcp"].get("registration", {}) | {"bearer_token_env_var": token_env_var}}
    if mcp_executable and name != "repoprompt":
        raise ValueError("--mcp-executable is only available for RepoPrompt")
    if mcp_executable:
        mcp_executable = absolute(mcp_executable)
        if not mcp_executable.is_file() or mcp_executable.name not in spec["mcp"]["native_command"]:
            raise ValueError("Select an existing native RepoPrompt MCP executable")
        spec["dependencies"] = [req for req in spec["dependencies"] if "native_mcp" not in req]
    report = check(name, spec, system, config)
    result = {"tool": name, "interface": interface, "platform": system, "check": report, "steps": [], "blocked": [], "manual_checks": spec.get("manual_checks", []), "spec": spec, "read_roots": [str(absolute(root)) for root in read_roots], "mcp_executable": str(mcp_executable) if mcp_executable else None}
    if report["status"] == "unsupported_platform":
        result["blocked"].append("Tool does not support " + system)
        return result
    if report.get("provider") and report.get("mcp_status") is None:
        return result
    if spec.get("manual_setup"):
        result["blocked"].append(spec["manual_setup"])
        return result
    for root in result["read_roots"]:
        if name != "rtk" or interface != "mcp" or not Path(root).is_dir():
            raise ValueError("--read-root requires RTK MCP and an existing absolute directory")
    if name == "rss":
        if not feeds_path or not absolute(feeds_path).is_file():
            result["blocked"].append("Select an existing OPML/JSON file using --feeds-path")
            return result
        result["feeds_path"] = str(absolute(feeds_path))
    if spec.get("minimum_macos") and any(item.startswith("macOS ") for item in report["missing"]):
        result["blocked"].extend(report["missing"])
        return result
    pending = set()
    tool_commands = {"playwright-cli", "playwright-mcp", "rtk", "cmux", *spec.get("tool_commands", [])}

    def add_dependency(requirement):
        requirement = {"command": requirement} if isinstance(requirement, str) else requirement
        if requirement["command"] == "node" and "minimum_version" not in requirement:
            requirement = requirement | {"minimum_version": [18, 0, 0], "version_args": ["--version"]}
        command = requirement["command"]
        if command in pending or not dependency_missing(requirement, system):
            return
        pending.add(command)
        installers = manifest["dependency_installers"].get(command, {})
        recipe = installers.get(system, installers.get("all", {}))
        if recipe.get("manual") or not recipe.get("commands"):
            result["blocked"].append(recipe.get("manual", "Install " + command + " using an approved source"))
            return
        for dependency in installers.get("requires", []):
            add_dependency(dependency)
        # npm arrives with a missing Node.js installation
        result["steps"].append(recipe_step(command, installers | recipe, prefix))

    for requirement in spec["dependencies"]:
        if "command" in requirement and requirement["command"] not in tool_commands:
            add_dependency(requirement)
    tool_missing = any(dependency_missing(req, system) for req in spec["dependencies"] if req.get("command") in tool_commands or "app" in req or "native_mcp" in req)
    if interface == "mcp" and name in {"rtk", "cmux"} and tool_missing:
        base = manifest["tools"][name]["automatic_install"]
        native_recipe = base.get(system, base.get("all", {}))
        for requirement in native_recipe.get("requires", []):
            add_dependency(requirement)
        result["steps"].append(recipe_step(name + ":native", native_recipe, prefix))
    if spec.get("mcp"):
        state, _ = mcp_state(spec["mcp"], config)
        tool_missing = state != "registered" or bool(report["missing"])
        if state == "conflict":
            result["blocked"].append("Existing MCP name conflicts; inspect and merge the selected entry first")
    if tool_missing:
        recipe = spec["automatic_install"].get(system, spec["automatic_install"].get("all", {}))
        for requirement in recipe.get("requires", []):
            add_dependency(requirement)
        result["steps"].append(recipe_step(name, recipe, prefix))
        if recipe.get("action") == "native_mcp" and not (mcp_executable or native_mcp_command(name)):
            result["blocked"].append("Install the selected native RepoPrompt app first, then select its MCP executable")
    if spec.get("setup_assets"):
        result["assets"] = asset_files(spec, prefix)
        if not tool_missing and any(not path.is_file() or digest(path.read_bytes()) != digest(source.read_bytes()) for source, path in result["assets"]):
            result["steps"].append({"component": name, "source": spec["source"], "version": "selected language configuration", "scope": str(prefix/spec["setup_assets"]["destination"]), "commands": [], "action": "setup_assets"})
    if browser:
        if name != "playwright":
            raise ValueError("--browser is only available for Playwright")
        if interface == "mcp":
            raise ValueError("MCP mode uses installed Chrome in an isolated profile; browser installation is a separate explicit operation")
        result["steps"].append({"component": "browser:" + browser, "source": "https://github.com/microsoft/playwright-cli", "version": "Playwright managed browser channel", "scope": "Playwright cache; Chrome / Edge may use system installation", "commands": [["playwright-cli", "install-browser", browser]], "action": None})
    # A missing Node.js package provides npm too; an npm-only failure requires repair
    if "node" in pending:
        result["blocked"] = [item for item in result["blocked"] if not item.startswith("npm is bundled")]
    for step in result["steps"]:
        step["purpose"] = "Install " + name if step["component"] == name else "Missing prerequisite for " + name
        for command in step["commands"]:
            manager = command[0]
            if manager not in pending and manager not in {"npm", "playwright-cli"} and not find_command(manager):
                result["blocked"].append("Missing package manager: " + manager + "; install from its approved official source")
    result["blocked"] = list(dict.fromkeys(result["blocked"]))
    if wheel_dir and any(step["action"] == "python_mcp" for step in result["steps"]):
        requirement = spec.get("python_package", "codex-development-tools-mcp==0.1.0")
        result["wheel_file"] = str(verified_wheel(wheel_dir, requirement))
    return result


def asset_files(spec, prefix):
    assets = spec["setup_assets"]
    relative = [Path(assets["source"]), Path(assets["destination"]), *map(Path, assets["files"])]
    if any(path.is_absolute() or ".." in path.parts for path in relative):
        raise ValueError("Setup assets must stay in the selected source and user prefix")
    pairs = [(ROOT/relative[0]/name, prefix/relative[1]/name) for name in relative[2:]]
    for item in assets.get("shared_files", []):
        source, target = Path(item["source"]), Path(item["destination"])
        if any(path.is_absolute() or ".." in path.parts for path in (source, target)):
            raise ValueError("Shared setup assets must stay in the selected source and user prefix")
        pairs.append((ROOT/source, prefix/target))
    return pairs


def install_assets(spec, prefix):
    pairs = asset_files(spec, prefix)
    folder = prefix/spec["setup_assets"]["destination"]
    marker = folder/".codex-setup-assets.json"
    if folder.is_symlink() or any(path.is_symlink() for _, path in pairs) or marker.is_symlink():
        raise ValueError("Selected proofreading assets contain a symlink; files were preserved")
    previous = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else {}
    for source, path in pairs:
        if not source.is_file():
            raise ValueError("Setup resource is missing: " + str(source))
        if path.exists() and path.read_bytes() != source.read_bytes() and digest(path.read_bytes()) != previous.get(path.name):
            raise ValueError("Modified proofreading config was preserved: " + str(path))
    folder.mkdir(parents=True, exist_ok=True)
    changed = []
    for source, path in pairs:
        before = path.read_bytes() if path.exists() else None
        after = source.read_bytes()
        if before != after:
            path.parent.mkdir(parents=True, exist_ok=True)
            changed.append({"file": str(path), "backup": atomic(path, after, before)})
    after = json.dumps({path.name: digest(path.read_bytes()) for _, path in pairs}, indent=2).encode("utf-8")
    before = marker.read_bytes() if marker.exists() else None
    if before != after:
        atomic(marker, after, before)
    return changed


def refresh_windows_path(env):
    if os.name != "nt":
        return
    import winreg
    paths = []
    for hive, key in ((winreg.HKEY_CURRENT_USER, "Environment"), (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")):
        try:
            with winreg.OpenKey(hive, key) as handle:
                paths.append(os.path.expandvars(winreg.QueryValueEx(handle, "Path")[0]))
        except OSError:
            continue
    env["PATH"] = os.pathsep.join([*paths, env.get("PATH", "")])


def install_command(command, env):
    filename = command[0] + ".cmd" if os.name == "nt" and command[0] in {"npm", "playwright-cli"} else command[0]
    executable = shutil.which(filename, path=env["PATH"]) or find_command(command[0])
    if not executable:
        raise ValueError("Installed executable is not visible yet: " + command[0] + "; reopen the terminal and rerun this selected tool")
    # Invoke the official Node entrypoint directly so literal paths cannot become batch syntax
    if os.name == "nt" and Path(executable).suffix.lower() == ".cmd":
        entries = {"npm": "node_modules/npm/bin/npm-cli.js", "playwright-cli": "node_modules/@playwright/cli/playwright-cli.js", "codex": "node_modules/@openai/codex/bin/codex.js", "cspell": "node_modules/cspell/bin.mjs", "textlint": "node_modules/textlint/bin/textlint.js"}
        if command[0] not in entries:
            raise ValueError("No reviewed Node entrypoint for " + command[0])
        entry = Path(executable).parent/entries[command[0]]
        node = shutil.which("node", path=env["PATH"])
        if not entry.is_file() or not node:
            raise ValueError("Cannot resolve official Node entrypoint for " + command[0] + "; inspect the selected npm installation")
        return [node, str(entry), *command[1:]]
    return [executable, *command[1:]]


def register_mcp(spec, config, server=None):
    state, provider = mcp_state(spec, config)
    if state == "registered":
        return {"status": "already_registered", "provider": provider}
    if state == "conflict":
        raise ValueError("Existing MCP name conflicts; settings were preserved")
    before = config.read_bytes() if config.exists() else None
    text = (before or b"").decode("utf-8-sig")
    selected = server or {"url": spec["url"], **spec.get("registration", {})}
    after = registration(text, spec["name"], selected | {"enabled": True, "required": False}).encode("utf-8")
    parsed = tomllib.loads(after.decode("utf-8"))
    previous = tomllib.loads(text)
    parsed["mcp_servers"].pop(spec["name"])
    if not parsed["mcp_servers"] and "mcp_servers" not in previous:
        parsed.pop("mcp_servers")
    if parsed != previous:
        raise ValueError("Unrelated settings changed; registration cancelled")
    backup = atomic(config, after, before)
    return {"status": "registered", "backup": backup}


def install_python_mcp(planned, env):
    name, spec = planned["tool"], planned["spec"]
    if planned.get("wheel_file"):
        selected = absolute(Path(planned["wheel_file"]))
        verified = verified_wheel(selected.parent, spec.get("python_package", "codex-development-tools-mcp==0.1.0"))
        if selected != verified:
            raise ValueError("Selected wheel changed after preview")
    root = default_data_root()/"mcp_optional"/name
    marker = root/".codex-setup-managed"
    if root.exists() and not marker.is_file():
        raise ValueError("Unmanaged Python environment exists; it was preserved: " + str(root))
    if not root.exists():
        subprocess.run([sys.executable, "-I", "-B", "-m", "venv", str(root)], env=env, check=True)
        marker.write_text(name + "\n", encoding="utf-8")
    python = root/("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if spec.get("python_package"):
        if not planned.get("wheel_file") and spec.get("python_source"):
            source_path = (ROOT / spec["python_source"]).resolve()
            if not source_path.is_relative_to(ROOT.resolve()) or not (source_path / "pyproject.toml").is_file():
                raise ValueError("Selected Python MCP source is missing or outside the setup")
            with tempfile.TemporaryDirectory(prefix="codex-optional-mcp-") as temp:
                source = Path(temp) / "adapter"
                shutil.copytree(source_path, source, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info", "build", "dist"))
                subprocess.run([str(python), "-I", "-m", "pip", "install", str(source)], env=env, check=True)
        else:
            subprocess.run([str(python), "-I", "-m", "pip", "install", planned.get("wheel_file", spec["python_package"])], env=env, check=True)
        entry = spec.get("python_entry", "arxiv-mcp-server")
        arguments = [part.replace("{node_executable}", find_command("node") or "") for part in spec.get("mcp", {}).get("args", [])]
        return {"command": str(root/("Scripts/" + entry + ".exe" if os.name == "nt" else "bin/" + entry)), "args": arguments, **spec.get("mcp", {}).get("registration", {})}
    # Build only this adapter from a temporary copy; leave source build artifacts untouched
    if planned.get("wheel_file"):
        subprocess.run([str(python), "-I", "-m", "pip", "install", planned["wheel_file"]], env=env, check=True)
    else:
        with tempfile.TemporaryDirectory(prefix="codex-optional-mcp-") as temp:
            source = Path(temp)/"adapter"
            shutil.copytree(ROOT/"mcp/mcp_servers/development_tools", source, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info", "build", "dist"))
            subprocess.run([str(python), "-I", "-m", "pip", "install", str(source)], env=env, check=True)
    executable = find_command(name)
    if not executable:
        raise ValueError("Native executable is unavailable after installation: " + name)
    args = ["-I", "-B", "-m", "development_tool_mcp.server", "--tool", name, "--executable", executable]
    for root in planned["read_roots"]:
        if not Path(root).is_dir():
            raise ValueError("Read root must be an existing directory: " + root)
        args += ["--read-root", root]
    return {"command": str(python), "args": args}


def install_rss(planned, env):
    spec = planned["spec"]
    root = default_data_root()/"tools"/"mcp-rss-aggregator"
    marker = root/".codex-setup-managed"
    if root.exists() and not marker.is_file():
        raise ValueError("Unmanaged RSS checkout exists; it was preserved")
    if not root.exists():
        root.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([find_command("git"), "clone", "--no-checkout", spec["repository"], str(root)], env=env, check=True)
        marker.write_text(spec["source_commit"] + "\n", encoding="utf-8")
        subprocess.run([find_command("git"), "-C", str(root), "checkout", "--detach", spec["source_commit"]], env=env, check=True)
    else:
        current = subprocess.run([find_command("git"), "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run([find_command("git"), "-C", str(root), "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True, check=True).stdout
        if current != spec["source_commit"] or dirty:
            raise ValueError("RSS checkout changed; inspect it before installing")
    for command in (["npm", "ci"], ["npm", "run", "build"]):
        subprocess.run(install_command(command, env), cwd=root, env=env, check=True)
    return {"command": shutil.which("node", path=env["PATH"]), "args": [str(root/"build/index.js")], "env": {"RSS_FEEDS_PATH": planned["feeds_path"]}}


def apply_plan(planned, manifest, config, prefix, *, yes=False, ui=None):
    if planned["blocked"]:
        raise ValueError("Resolve the listed prerequisites before applying; nothing was installed")
    if not planned["steps"]:
        return []
    if not yes:
        if not sys.stdin.isatty():
            raise ValueError("Installation needs an interactive confirmation or explicitly authorized --yes")
        if input((ui or InstallerUi()).text("Install the listed components for {0} only? [y/N] ", planned["tool"])).strip().lower() not in {"y", "yes"}:
            return [{"status": "declined"}]
    env = dict(os.environ, PYTHONUTF8="1", RTK_TELEMETRY_DISABLED="1")
    bins = [prefix if os.name == "nt" else prefix/"bin", Path.home()/".cargo/bin", Path("/opt/homebrew/bin"), Path("/usr/local/bin")]
    env["PATH"] = os.pathsep.join(map(str, bins)) + os.pathsep + env.get("PATH", "")
    os.environ["PATH"] = env["PATH"]
    completed = []
    for step in planned["steps"]:
        if step["action"] == "setup_assets":
            completed += install_assets(planned["spec"], prefix)
            continue
        if step["action"] == "register_mcp":
            completed.append(register_mcp(planned["spec"]["mcp"], config))
            continue
        if step["action"] == "python_mcp":
            server = install_python_mcp(planned, env)
            completed.append(register_mcp(planned["spec"]["mcp"], config, server))
            continue
        if step["action"] == "native_mcp":
            server = {"command": planned["mcp_executable"] or native_mcp_command(planned["tool"])}
            completed.append(register_mcp(planned["spec"]["mcp"], config, server))
            continue
        if step["action"] == "repo_node_mcp":
            completed.append(register_mcp(planned["spec"]["mcp"], config, install_rss(planned, env)))
            continue
        for command in step["commands"]:
            args = install_command(command, env)
            if command[0] == "winget":
                args += ["--accept-source-agreements", "--accept-package-agreements", "--disable-interactivity"]
            process = subprocess.run(args, env=env, check=False)
            if process.returncode:
                raise ValueError("Installation failed: " + step["component"] + "; exit code " + str(process.returncode) + "; subsequent steps were not run")
            if command[0] == "winget":
                refresh_windows_path(env)
                os.environ["PATH"] = env["PATH"]
        completed.append({"component": step["component"], "status": "command_succeeded"})
        if step["component"] == planned["tool"] and planned["spec"].get("setup_assets"):
            completed += install_assets(planned["spec"], prefix)
        if step["action"] == "node_mcp":
            spec = planned["spec"]["mcp"]
            entry = prefix/"node_modules"/spec["entry_suffix"].lstrip("/")
            if not entry.is_file():
                raise ValueError("Installed MCP entrypoint is missing: " + str(entry))
            arguments = [part.format(npm_prefix=str(prefix)) for part in spec.get("args", [])]
            launcher = [str(prefix/spec["launcher_asset"])] if spec.get("launcher_asset") else []
            server = {"command": shutil.which("node", path=env["PATH"]) or find_command("node"), "args": [*launcher, str(entry), *arguments], **spec.get("registration", {})}
            completed.append(register_mcp(spec, config, server))
    # This process only; users receive a PATH hint instead of a persistent edit
    os.environ["PATH"] = env["PATH"]
    return completed


def guided_select(manifest, profile="all", *, ui=None):
    ui = ui or InstallerUi()
    if not sys.stdin.isatty():
        raise ValueError("Run launch-cli.cmd mcp / sh launch-cli.sh mcp in an interactive terminal, or select --tool explicitly")
    selected_tools = profile_tools(manifest, profile)
    groups = list(dict.fromkeys(spec.get("group", "Other") for spec in selected_tools.values()))
    while True:
        print("\n" + ui.text("Select a tool category (profile: {0}):", ui.label("profile", profile)))
        print("  0. " + ui.text("Show all tools in this profile"))
        for index, group in enumerate(groups, 1):
            print(f"  {index}. {ui.label('group', group)}")
        print("  L. " + ui.text("Language"))
        print("  Q. " + ui.text("Exit"))
        group = choose_index(range(1, len(groups) + 1), ui.text("Category number (0 = All, L = Language, Q / Enter = Exit): "), ui=ui, language_option=True, exit_option=True, zero_value=0)
        if group == "language":
            print("\n" + ui.text("Language"))
            for index, language in enumerate(("zh-TW", "en"), 1):
                print(f"  {index}. {ui.label('language', language)}")
            print("  0. " + ui.text("Back"))
            language = choose_index(["zh-TW", "en"], ui.text("Language number (0 / Enter = Back): "), ui=ui)
            if language:
                ui.select(language)
            continue
        if group is None:
            return None
        group = groups[group-1] if group else None
        names = [name for name, spec in selected_tools.items() if group is None or spec.get("group", "Other") == group]
        print("\n" + (ui.label("group", group) if group else ui.text("All tools in this profile")))
        for index, name in enumerate(names, 1):
            spec = tool_spec(name, manifest, setup_interface(manifest["tools"][name]))
            mode = ui.text("manual setup required" if spec.get("manual_setup") or spec.get("custom_endpoint") else "check / install")
            print(f"  {index}. {ui.label('title', spec.get('title', name), name)} [{name}] - {mode}")
        print("  0. " + ui.text("Back to categories"))
        selected = choose_index(names, ui.text("Tool number (0 / Enter = Back): "), ui=ui)
        if selected is not None:
            return selected


def setup_interface(spec):
    if spec.get("kind") in {"library", "reference"}:
        return "native"
    return "mcp" if spec.get("mcp") or spec.get("interfaces", {}).get("mcp") or spec.get("manual_setup") else "native"


def choose_index(values, prompt, *, ui=None, language_option=False, exit_option=False, zero_value=None):
    ui = ui or InstallerUi()
    while True:
        selected = input(prompt).strip()
        if language_option and selected.lower() == "l":
            return "language"
        if not selected or exit_option and selected.lower() == "q":
            return None
        if selected == "0":
            return zero_value
        if selected.isdecimal() and 1 <= int(selected) <= len(values):
            return values[int(selected)-1]
        print(ui.text("Enter a number from the list"))


def show_guided_plan(planned, *, ui=None):
    ui = ui or InstallerUi()
    spec = planned["spec"]
    print(f"\n{ui.label('title', spec.get('title', planned['tool']), planned['tool'])} / {planned['platform']} / {planned['interface']}")
    print(ui.text("Source: {0}", spec.get("source", ui.text("See requirements"))))
    for step in planned["steps"]:
        print("  " + ui.text("{0}: {1}\n  Scope: {2}\n  Purpose: {3}\n  Package source: {4}", step["component"], step["version"], step["scope"], step["purpose"], step["source"]))
    for item in planned["blocked"]:
        print(ui.text("Required setup: {0}", item))
    for item in spec.get("service_requirements", []):
        print(ui.text("Service requirement: {0}", item))
    for name, state in planned["check"].get("credential_env", {}).items():
        print(ui.text("Credential variable: {0} ({1}); configure locally, keep values out of chat and source", name, state))
    if not planned["steps"] and not planned["blocked"]:
        print(ui.text("Reusing the existing installation / provider; no installation steps needed"))


def oauth_entry(spec, config):
    if not spec.get("mcp"):
        return None
    state, provider = mcp_state(spec["mcp"], config)
    parsed = tomllib.loads(config.read_text(encoding="utf-8-sig")) if config.exists() else {}
    return provider if state == "registered" and provider in parsed.get("mcp_servers", {}) else None


def login_selected(spec, config):
    if config.name != "config.toml":
        raise ValueError("OAuth login requires a Codex home config.toml path")
    provider = oauth_entry(spec, config)
    if not provider:
        raise ValueError("Use the existing plugin / connector account setup; no standalone MCP entry is available for CLI login")
    executable = find_command("codex")
    if not executable:
        raise ValueError("Codex CLI unavailable; use the app's MCP account connection instead")
    env = dict(os.environ, CODEX_HOME=str(config.parent))
    args = install_command(["codex", "mcp", "login", provider], env)
    result = subprocess.run(args, env=env, check=False)
    if result.returncode:
        raise ValueError("Account login did not complete; registration was kept for the next attempt")


def guided_next_steps(planned, config, *, completed=(), login=False, ready=True, interactive=True, ui=None):
    ui = ui or InstallerUi()
    spec = planned["spec"]
    print("\n" + ui.text("Next steps: verify account access and real use" if ready else "Remaining setup and verification:"))
    for item in completed:
        if item.get("backup"):
            print(ui.text("Config backup: {0}", item["backup"]))
    oauth = spec.get("authentication", spec.get("auth")) == "oauth"
    if ready and oauth and not oauth_entry(spec, config):
        print(ui.text("Account login: use the existing plugin / connector account connection"))
    elif ready and oauth:
        selected = login
        if not selected and interactive and sys.stdin.isatty():
            selected = input(ui.text("Open the official OAuth login now? [y/N] ")).strip().lower() in {"y", "yes"}
        if selected:
            login_selected(spec, config)
            print(ui.text("OAuth login completed; verify service permissions with a safe call"))
        else:
            print(ui.text("Account login: connect in Codex MCP settings, or rerun this entry and choose login"))
    if spec.get("mcp"):
        print(ui.text("After setup, reload MCP / open a new Codex chat, check tool discovery, then perform a safe call"))
    else:
        print(ui.text("After setup, run a safe CLI check and verify its output and configuration"))
    for item in spec.get("manual_checks", []):
        print(ui.text("Verify: {0}", item))
    print(ui.text("Setup guide: {0}", str(ROOT/"docs/tools/catalog.md")))


def main(argv=None):
    manifest = json.loads((ROOT/"mcp/tools/development-tools.requirements.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported requirements schema")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", choices=manifest["tools"], action="append", help="Exactly one tool; no all-tools installation")
    parser.add_argument("--apply", action="store_true", help="Install after confirmation")
    parser.add_argument("--yes", action="store_true", help="Use only after explicit authorization for the displayed scope")
    parser.add_argument("--expected-plan-sha256", help=argparse.SUPPRESS)
    parser.add_argument("--config", type=Path, help="Absolute Codex config path")
    parser.add_argument("--npm-prefix", type=Path, help="Absolute user npm prefix")
    parser.add_argument("--browser", choices=["chromium", "chrome", "msedge", "firefox", "webkit"], help="Explicitly install a Playwright browser")
    parser.add_argument("--interface", choices=["native", "mcp"], default="native")
    parser.add_argument("--server-url", help="Credential-free Home Assistant MCP endpoint")
    parser.add_argument("--token-env-var", help="Bearer token environment-variable name, never the token")
    parser.add_argument("--mcp-executable", type=Path, help="Existing native RepoPrompt MCP executable")
    parser.add_argument("--read-root", type=Path, action="append", default=[], help="Explicit RTK log read root; default is no file access")
    parser.add_argument("--feeds-path", type=Path, help="Explicit existing RSS OPML/JSON feed file")
    parser.add_argument("--lang", choices=["auto", "zh-TW", "en"], default="auto", help="Prefer Traditional Chinese; fall back to English when the output encoding cannot represent it")
    parser.add_argument("--guided", action="store_true", help="Interactive tool selection and readable install/login/verification steps")
    parser.add_argument("--list", action="store_true", help="List independent tools without installation")
    parser.add_argument("--no-guide", "--no-pause", dest="no_guide", action="store_true", help="Skip opening the Chinese guide for automation or a parent launcher")
    parser.add_argument("--profile", choices=manifest.get("profiles", {"all": {}}), default="all", help="Filter the catalog by computer purpose; never installs an entire profile")
    parser.add_argument("--update", action="store_true", help="Check or update the selected installed tool through its supported official channel")
    parser.add_argument("--login", action="store_true", help="Explicitly start OAuth for the selected supported hosted service after registration")
    parser.add_argument("--wheel-dir", type=Path, help="Absolute directory of built wheels and mcp-release-manifest.json")
    args = parser.parse_args(argv)
    ui = InstallerUi(args.lang)
    open_guide = args.guided and not args.yes and not args.no_guide and not args.list and sys.stdin.isatty()
    try:
        return run_selected(args, manifest, parser, ui)
    except (EOFError, KeyboardInterrupt):
        open_guide = False
        print("\n" + ui.text("Setup cancelled"))
        return 130
    finally:
        if open_guide and not args.no_guide and args.tool:
            open_chinese_guide(ROOT, args.tool[0], ui=ui)


def run_selected(args, manifest, parser, ui):
    if args.list:
        for name, spec in profile_tools(manifest, args.profile).items():
            print(ui.label("group", spec.get("group", "Other")) + " / " + name + " - " + ui.label("title", spec.get("title", name), name) + " (" + spec.get("kind", "tool") + ")")
        return 0
    if not args.tool and args.guided:
        try:
            selected = guided_select(manifest, args.profile, ui=ui)
        except ValueError as exc:
            print(str(exc))
            return 2
        if selected is None:
            args.no_guide = True
            return 0
        args.tool = [selected]
        args.interface = setup_interface(manifest["tools"][selected])
    if not args.tool:
        parser.error("Select --tool, --guided or --list")
    if len(args.tool) != 1:
        parser.error("Select exactly one --tool per invocation")
    if args.guided and setup_interface(manifest["tools"][args.tool[0]]) == "native":
        args.interface = "native"
    if args.update:
        if __package__:
            from .update_development_tool import main as update
        else:
            from update_development_tool import main as update
        options = ["--tool", args.tool[0], "--interface", args.interface]
        for flag, value in (("--config", args.config), ("--npm-prefix", args.npm_prefix)):
            if value:
                options += [flag, str(value)]
        if args.apply:
            options.append("--apply")
        if args.yes:
            options.append("--yes")
        if args.expected_plan_sha256:
            options += ["--expected-plan-sha256", args.expected_plan_sha256]
        return update(options)
    if args.guided and not args.yes and sys.stdin.isatty():
        selected_spec = tool_spec(args.tool[0], manifest, args.interface)
        if selected_spec.get("custom_endpoint") and not args.server_url:
            args.server_url = input(ui.text("Your Home Assistant MCP URL (no credentials): ")).strip() or None
        if args.tool[0] == "rss" and not args.feeds_path:
            value = input(ui.text("Absolute RSS OPML / JSON file path: ")).strip()
            args.feeds_path = Path(value) if value else None
    config = absolute(args.config or Path(os.environ.get("CODEX_HOME") or Path.home()/".codex")/"config.toml")
    prefix = absolute(args.npm_prefix or npm_prefix())
    planned = None
    confirmed = False
    try:
        wheel_dir = args.wheel_dir or (ROOT / "wheels" if (ROOT / "wheels").is_dir() else None)
        planned = plan(args.tool[0], manifest, system_name(), prefix, config, args.browser, args.interface, server_url=args.server_url, token_env_var=args.token_env_var, mcp_executable=args.mcp_executable, read_roots=args.read_root, feeds_path=args.feeds_path, wheel_dir=wheel_dir)
        if args.login and planned["spec"].get("authentication", planned["spec"].get("auth")) != "oauth":
            raise ValueError("This selected tool does not use the automatic OAuth route")
        if args.guided:
            show_guided_plan(planned, ui=ui)
            if planned["blocked"]:
                print(ui.text("Complete the required setup, then rerun this entry; no installation performed"))
                guided_next_steps(planned, config, ready=False, interactive=False, ui=ui)
                return 1
            if planned["steps"] and not args.apply:
                if args.yes:
                    args.no_guide = True
                    print(ui.text("Preview only; add --apply to install the listed components"))
                    return 0
                if not sys.stdin.isatty() or input(ui.text("Install this tool and only the listed prerequisites? [y/N] ")).strip().lower() not in {"y", "yes"}:
                    args.no_guide = True
                    return 0
                args.apply = True
                confirmed = True
            elif not planned["steps"]:
                args.apply = True
        else:
            public = {key: value for key, value in planned.items() if key not in {"spec", "assets"}}
            print(json.dumps({"status": "preview", "install_performed": False, **public}, ensure_ascii=True, indent=2), flush=True)
        if not args.apply:
            return 1 if planned["blocked"] else 0
        require_same_plan(planned, args.expected_plan_sha256)
        completed = apply_plan(planned, manifest, config, prefix, yes=args.yes or confirmed, ui=ui)
        if completed == [{"status": "declined"}]:
            args.no_guide = True
            if args.guided:
                print(ui.text("Cancelled; no installation performed"))
            else:
                print(json.dumps({"status": "declined", "completed": completed}))
            return 0
        report = check(args.tool[0], planned["spec"], system_name(), config)
        if args.guided:
            print(ui.text("Check status: {0}", report["status"]))
        incomplete = report["status"] in {"missing_dependencies", "unsupported_platform", "manual_setup_required"}
        if args.guided and incomplete:
            print(ui.text("Post-install checks are incomplete; resolve these items and rerun this entry"))
            for item in report.get("missing", []):
                print("  " + item)
            if report.get("manual_setup"):
                print("  " + report["manual_setup"])
            guided_next_steps(planned, config, completed=completed, ready=False, interactive=False, ui=ui)
            return 1
        if args.guided:
            guided_next_steps(planned, config, completed=completed, login=args.login, interactive=not args.yes, ui=ui)
            return 0
        elif args.login:
            if incomplete:
                raise ValueError("Post-install checks are incomplete; resolve prerequisites before account login")
            if planned["spec"].get("authentication", planned["spec"].get("auth")) != "oauth":
                raise ValueError("This selected tool does not use the automatic OAuth route")
            login_selected(planned["spec"], config)
        print(json.dumps({"status": "declined" if completed == [{"status": "declined"}] else "applied", "completed": completed, "check": report, "path_to_add": str(prefix if os.name == "nt" else prefix/"bin")}, indent=2))
        return 1 if incomplete else 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        if args.guided and planned is not None:
            guided_next_steps(planned, config, ready=False, interactive=False, ui=ui)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
