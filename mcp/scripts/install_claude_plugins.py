#!/usr/bin/env python3
"""Preview or apply a selected Claude Code plugin set from one Git marketplace.

Preview reads Claude files only. --apply runs native `claude plugin` commands, then merges
marketplace auto-update and `<plugin>@inline` disables into settings.json with a backup.

Preview also reports MCP commands missing from PATH. With --apply, a profile `runtimes` recipe
runs only after an interactive yes for that command. Plugins listed in `local_scope` never install
at user scope; `--local <plugin>` installs one into a located project checkout with `--scope local`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCOPE = "user"
TOOLKIT = Path(__file__).resolve().parents[2]
PLATFORM = "windows" if os.name == "nt" else ("macos" if sys.platform == "darwin" else "linux")


def read_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def load_profile(path: Path) -> dict:
    value = read_json(path)
    market = value.get("marketplace")
    if not isinstance(market, dict) or not isinstance(market.get("name"), str) or not isinstance(market.get("url"), str):
        raise ValueError("Profile needs marketplace.name and marketplace.url")
    if not market["url"].startswith(("https://", "git@")):
        raise ValueError("Marketplace url must be an https or git@ Git source")
    for key in ("plugins", "exclude"):
        if key in value and not (isinstance(value[key], list) and all(isinstance(item, str) for item in value[key])):
            raise ValueError(f"Profile {key} must be a list of plugin names")
    for key in ("auto_update", "disable_inline"):
        if not isinstance(value.get(key, False), bool):
            raise ValueError(f"Profile {key} must be true or false")
    for command, recipe in value.get("runtimes", {}).items():
        steps = recipe.get(PLATFORM, []) if isinstance(recipe, dict) else None
        if not isinstance(steps, list) or not all(isinstance(step, list) and step and all(isinstance(part, str) for part in step) for step in steps):
            raise ValueError(f"Runtime recipe for {command} needs per-platform argv lists")
    for name, rule in value.get("local_scope", {}).items():
        if not isinstance(rule, dict) or not str(rule.get("repository", "")).startswith(("https://", "git@")):
            raise ValueError(f"local_scope {name} needs the project repository URL")
    return value


def load_options(path: Path | None, market: str) -> dict:
    """Accept {plugin: {key: value}} or a settings.json backup holding pluginConfigs."""
    if path is None:
        return {}
    value = read_json(path)
    if "pluginConfigs" in value:
        value = {key: entry.get("options", {}) for key, entry in value["pluginConfigs"].items() if isinstance(entry, dict)}
    options = {}
    for key, values in value.items():
        plugin = key if "@" in key else f"{key}@{market}"
        if not plugin.endswith("@" + market):
            continue
        if not isinstance(values, dict) or not all(isinstance(item, str) and "\n" not in item for item in values.values()):
            raise ValueError(f"Options must be single-line strings: {plugin}")
        options[plugin] = values
    return options


def git_address(value: str) -> str:
    """Compare Git addresses without a trailing slash or .git, and with git@host:path as https."""
    value = value.strip().rstrip("/")
    if value.startswith("git@") and ":" in value:
        host, path = value[4:].split(":", 1)
        value = f"https://{host}/{path}"
    return value[:-4] if value.endswith(".git") else value


def source_matches(source: dict, url: str) -> bool:
    kind = source.get("source")
    if kind == "git":
        return git_address(source.get("url", "")) == git_address(url)
    if kind == "github":
        return git_address(f"https://github.com/{source.get('repo', '')}") == git_address(url)
    return False


def describe_source(source: dict) -> str:
    detail = source.get("url") or source.get("repo") or source.get("path") or ""
    return f"{source.get('source', 'unknown')} {detail}".strip()


def marketplace_root(home: Path, profile: dict) -> Path:
    """Locate the profile marketplace; stop when the same name is registered from another source."""
    market, url = profile["marketplace"]["name"], profile["marketplace"]["url"]
    known = read_json(home / "plugins" / "known_marketplaces.json").get(market)
    declared = read_json(home / "settings.json").get("extraKnownMarketplaces", {}).get(market)
    for entry in (known, declared):
        source = entry.get("source") if isinstance(entry, dict) else None
        if isinstance(source, dict) and not source_matches(source, url):
            raise ValueError(f"Marketplace {market} is registered from {describe_source(source)}, not {url}; "
                             f"run `claude plugin marketplace remove {market}` before restoring this profile")
    location = known.get("installLocation") if isinstance(known, dict) else None
    return Path(location) if location else home / "plugins" / "marketplaces" / market


def catalog(home: Path, profile: dict) -> dict | None:
    root = marketplace_root(home, profile)
    manifest = root / ".claude-plugin" / "marketplace.json"
    if not manifest.is_file():
        return None
    plugins = {}
    for entry in read_json(manifest).get("plugins", []):
        source = entry.get("source")
        if not isinstance(source, str):
            continue
        plugin = read_json(root / source / ".claude-plugin" / "plugin.json")
        servers = read_json(root / source / ".mcp.json").get("mcpServers", {})
        # Commands from userConfig placeholders are device options, not PATH lookups.
        commands = sorted({server["command"] for server in servers.values()
                           if isinstance(server, dict) and isinstance(server.get("command"), str) and "${" not in server["command"]})
        plugins[entry["name"]] = {"version": plugin.get("version") or entry.get("version"), "options": plugin.get("userConfig") or {},
                                  "commands": commands}
    return plugins


def select(profile: dict, available: dict) -> list[str]:
    names = profile.get("plugins") or sorted(available)
    unknown = sorted(set(names) - set(available))
    if unknown:
        raise ValueError("Profile selects plugins missing from the marketplace: " + ", ".join(unknown))
    excluded = set(profile.get("exclude", [])) | set(profile.get("local_scope", {}))
    return [name for name in names if name not in excluded]


def search_path() -> str:
    """PATH plus the user tool directories installers commonly add before a new shell starts."""
    extra = [Path.home() / ".cargo/bin", Path.home() / ".local/bin"]
    return os.pathsep.join([os.environ.get("PATH", ""), *map(str, extra)])


def missing_runtimes(available: dict, names: list[str]) -> dict[str, list[str]]:
    missing = {}
    for name in names:
        for command in available[name].get("commands", []):
            if shutil.which(command, path=search_path()) is None:
                missing.setdefault(command, []).append(name)
    return missing


def plan(home: Path, profile: dict, options: dict) -> tuple[list, list[str]]:
    """Return pending actions and report lines; an absent marketplace yields only its add action."""
    market = profile["marketplace"]["name"]
    settings = read_json(home / "settings.json")
    available = catalog(home, profile)
    # A leftover clone without a registration entry is not usable by native install.
    if market not in read_json(home / "plugins" / "known_marketplaces.json"):
        available = None
    if available is None:
        return [("add", market, None)], [f"ADD marketplace {market}"]
    installed = {key: user[0].get("version") for key, rows in read_json(home / "plugins" / "installed_plugins.json").get("plugins", {}).items()
                 if (user := [row for row in rows if row.get("scope", SCOPE) == SCOPE])}
    configs = settings.get("pluginConfigs", {})
    actions, lines = [], []
    names = select(profile, available)
    for name in names:
        plugin, info = f"{name}@{market}", available[name]
        wanted = options.get(plugin, {})
        schema = info["options"]
        for key in wanted:
            if key not in schema:
                raise ValueError(f"Unknown option {key} for {plugin}")
            if schema[key].get("sensitive"):
                raise ValueError(f"Enter sensitive option {key} for {plugin} through the native prompt")
        current = configs.get(plugin, {}).get("options", {})
        pending = len(actions)
        if plugin not in installed:
            actions.append(("install", plugin, wanted))
            lines.append(f"INSTALL {plugin} {info['version']}")
        else:
            if installed[plugin] != info["version"]:
                actions.append(("update", plugin, None))
                lines.append(f"UPDATE {plugin} {installed[plugin]} -> {info['version']}")
            if any(current.get(key) != item for key, item in wanted.items()):
                actions.append(("configure", plugin, wanted))
                lines.append(f"CONFIGURE {plugin} {', '.join(sorted(wanted))}")
        if len(actions) == pending:
            lines.append(f"CURRENT {plugin} {info['version']}")
        unset = [key for key, spec in schema.items()
                 if spec.get("required") and "default" not in spec and key not in wanted and key not in current]
        if unset:
            lines.append(f"UNSET {plugin} {', '.join(unset)}")
    for command, owners in sorted(missing_runtimes(available, names).items()):
        recipe = profile.get("runtimes", {}).get(command, {}).get(PLATFORM)
        owners = ", ".join(f"{name}@{market}" for name in owners)
        if recipe:
            actions.append(("runtime", command, recipe))
            lines.append(f"RUNTIME {command} missing for {owners}; --apply asks before installing")
        else:
            lines.append(f"RUNTIME {command} missing for {owners}; no recipe for {PLATFORM}, see the plugin SETUP.md")
    for name in sorted(set(available) - set(names)):
        lines.append(f"{'LOCAL' if name in profile.get('local_scope', {}) else 'SKIP'} {name}@{market}")
    patch = settings_patch(settings, profile, names)
    if patch:
        actions.append(("settings", market, patch))
        lines += [f"SETTINGS {item}" for item in patch]
    return actions, lines


def settings_patch(settings: dict, profile: dict, names: list[str]) -> list[str]:
    market = profile["marketplace"]["name"]
    patch = []
    if profile.get("auto_update") and settings.get("extraKnownMarketplaces", {}).get(market, {}).get("autoUpdate") is not True:
        patch.append(f"extraKnownMarketplaces.{market}.autoUpdate=true")
    if profile.get("disable_inline"):
        enabled = settings.get("enabledPlugins", {})
        patch += [f"enabledPlugins.{name}@inline=false" for name in names if enabled.get(f"{name}@inline") is not False]
    return patch


def write_settings(home: Path, profile: dict, names: list[str]) -> Path | None:
    path = home / "settings.json"
    settings = read_json(path)
    if not settings_patch(settings, profile, names):
        return None
    market = profile["marketplace"]
    backup = home / "backups" / "claude-plugins" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") / "settings.json"
    if path.exists():
        backup.parent.mkdir(parents=True)
        shutil.copy2(path, backup)
    if profile.get("auto_update"):
        entry = settings.setdefault("extraKnownMarketplaces", {}).setdefault(market["name"], {"source": {"source": "git", "url": market["url"]}})
        entry["autoUpdate"] = True
    if profile.get("disable_inline"):
        enabled = settings.setdefault("enabledPlugins", {})
        for name in names:
            enabled[f"{name}@inline"] = False
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return backup if backup.exists() else None


def run_cli(claude: list[str], args: list[str], stdin: str | None = None, cwd: Path | None = None) -> tuple[int, str]:
    result = subprocess.run([*claude, *args], input=stdin, capture_output=True, text=True, encoding="utf-8", timeout=600, cwd=cwd)
    return result.returncode, (result.stdout + result.stderr).strip()


def ask(question: str) -> bool:
    """Confirm on an interactive terminal only; anything else declines."""
    if not sys.stdin.isatty():
        print(question + " skipped: confirmation needs an interactive terminal")
        return False
    return input(question + " [y/N] ").strip().lower() in {"y", "yes"}


def install_runtime(command: str, recipe: list[list[str]]) -> int:
    env = dict(os.environ, PATH=search_path())
    for step in recipe:
        argv = [part.replace("{toolkit}", str(TOOLKIT)) for part in step]
        # A leading "?command" runs the step only when that command is still missing.
        if argv[0].startswith("?"):
            if shutil.which(argv[0][1:], path=env["PATH"]):
                continue
            argv = argv[1:]
        executable = shutil.which(argv[0], path=env["PATH"])
        if executable is None:
            print(f"RUNTIME {command} step needs {argv[0]}, which is not on PATH")
            return 2
        result = subprocess.run([executable, *argv[1:]], env=env, timeout=1800, check=False)
        print(f"RUNTIME {command} step {argv[0]} exit={result.returncode}")
        if result.returncode:
            return result.returncode
    return 0 if shutil.which(command, path=search_path()) else 2


def checkout_origin(path: Path) -> str | None:
    result = subprocess.run(["git", "-C", str(path), "remote", "get-url", "origin"], capture_output=True, text=True, check=False)
    return git_address(result.stdout) if result.returncode == 0 else None


def locate_project(rule: dict, explicit: Path | None, roots: list[Path]) -> list[Path]:
    """Return checkouts whose origin matches the rule; an explicit directory must match too."""
    wanted = git_address(rule["repository"])
    if explicit is not None:
        path = explicit.expanduser().resolve()
        if checkout_origin(path) != wanted:
            raise ValueError(f"{path} is not a checkout of {rule['repository']}")
        return [path]
    found = []
    for root in roots:
        if not root.is_dir():
            continue
        for git_dir in [root / ".git", *root.glob("*/.git"), *root.glob("*/*/.git"), *root.glob("*/*/*/.git")]:
            parent = git_dir.parent.resolve()
            if git_dir.exists() and parent not in found and checkout_origin(parent) == wanted:
                found.append(parent)
    return found


def install_local(claude: list[str], home: Path, profile: dict, options: dict, name: str, explicit: Path | None, roots: list[Path]) -> int:
    market = profile["marketplace"]["name"]
    rule = profile.get("local_scope", {}).get(name)
    if rule is None:
        raise ValueError(f"{name} is not listed in the profile local_scope")
    candidates = locate_project(rule, explicit, roots)
    if not candidates and sys.stdin.isatty():
        typed = input(f"Project checkout for {name} ({rule['repository']}), empty to skip: ").strip()
        candidates = locate_project(rule, Path(typed), roots) if typed else []
    if len(candidates) != 1:
        listed = ", ".join(map(str, candidates)) or "none found"
        print(f"LOCAL {name}@{market} needs one project checkout ({listed}); pass --project-dir")
        return 2
    project = candidates[0]
    if not ask(f"Install {name}@{market} with --scope local in {project}?"):
        return 1
    configs = [part for key, value in options.get(f"{name}@{market}", {}).items() for part in ("--config", f"{key}={value}")]
    code, output = run_cli(claude, ["plugin", "install", f"{name}@{market}", "--scope", "local", "--json", *configs], cwd=project)
    print(f"LOCAL {name}@{market} {project} exit={code}" + (f" {output[-300:]}" if code else ""))
    return code


def execute(claude: list[str], action: tuple, profile: dict) -> tuple[int, str]:
    kind, target, data = action
    if kind == "add":
        return run_cli(claude, ["plugin", "marketplace", "add", profile["marketplace"]["url"], "--scope", SCOPE, "--json"])
    if kind == "install":
        configs = [part for key, value in data.items() for part in ("--config", f"{key}={value}")]
        return run_cli(claude, ["plugin", "install", target, "--scope", SCOPE, "--json", *configs])
    if kind == "update":
        return run_cli(claude, ["plugin", "update", target, "--scope", SCOPE, "--json"])
    if kind == "configure":
        return run_cli(claude, ["plugin", "configure", target, "--values-stdin"], json.dumps(data))
    raise ValueError(f"Unknown action: {kind}")


def claude_command(value: Path | None) -> list[str]:
    path = value or (Path(found) if (found := shutil.which("claude")) else None)
    if path is None or not path.is_file():
        raise ValueError("Select the device's Claude Code executable with --claude")
    return [str(path)]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", type=Path, required=True, help="Private selection, e.g. <Setup>/profiles/claude-plugins.json.")
    parser.add_argument("--options", type=Path, help="Device-local {plugin: {key: value}} JSON or a settings.json backup with pluginConfigs.")
    parser.add_argument("--claude-home", type=Path, help="Override CLAUDE_CONFIG_DIR or ~/.claude.")
    parser.add_argument("--claude", type=Path, help="Claude Code executable used by --apply; defaults to claude on PATH.")
    parser.add_argument("--refresh", action="store_true", help="With --apply, refresh the marketplace listing before planning updates.")
    parser.add_argument("--local", action="append", default=[], help="With --apply, install this local_scope plugin into its project checkout.")
    parser.add_argument("--project-dir", type=Path, help="Project checkout for a single --local plugin; otherwise search --search-root.")
    parser.add_argument("--search-root", type=Path, action="append", default=[], help="Directories searched up to three levels for --local checkouts.")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    # Native CLI output can contain symbols a legacy Windows console code page cannot encode.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    home = (args.claude_home or Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")).expanduser().resolve()
    try:
        if home == Path(home.anchor) or home == Path.home().resolve():
            raise ValueError("Claude home must be a dedicated configuration directory")
        profile = load_profile(args.profile)
        options = load_options(args.options, profile["marketplace"]["name"])
        actions, lines = plan(home, profile, options)
        if not args.apply:
            print("\n".join(lines))
            return 1 if actions else 0
        claude = claude_command(args.claude)
        failed = False
        if args.refresh and catalog(home, profile) is not None:
            code, output = run_cli(claude, ["plugin", "marketplace", "update", profile["marketplace"]["name"]])
            print(f"REFRESH exit={code} {output[-300:]}")
            failed |= code != 0
        if actions and actions[0][0] == "add":
            code, output = execute(claude, actions[0], profile)
            print(f"ADD exit={code} {output[-300:]}")
            if code:
                return 2
        actions, _ = plan(home, profile, options)
        for action in actions:
            if action[0] == "settings":
                continue
            if action[0] == "runtime":
                if ask(f"Install the missing runtime {action[1]}?"):
                    code = install_runtime(action[1], action[2])
                    failed |= code != 0
                continue
            code, output = execute(claude, action, profile)
            print(f"{action[0].upper()} {action[1]} exit={code}" + (f" {output[-300:]}" if code else ""))
            failed |= code != 0
        backup = write_settings(home, profile, select(profile, catalog(home, profile)))
        if backup:
            print(f"BACKUP {backup}")
        if len(args.local) > 1 and args.project_dir:
            raise ValueError("--project-dir applies to one --local plugin")
        roots = args.search_root or [TOOLKIT.parent.parent]
        for name in args.local:
            failed |= install_local(claude, home, profile, options, name, args.project_dir, roots) == 2
        actions, lines = plan(home, profile, options)
        print("\n".join(lines))
        return 2 if failed else (1 if actions else 0)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
