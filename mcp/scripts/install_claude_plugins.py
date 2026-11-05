#!/usr/bin/env python3
"""Preview or apply a selected Claude Code plugin set from one Git marketplace.

Preview reads Claude files only. --apply runs native `claude plugin` commands, then merges
marketplace auto-update and `<plugin>@inline` disables into settings.json with a backup.
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


def catalog(home: Path, market: str) -> dict | None:
    root = home / "plugins" / "marketplaces" / market
    manifest = root / ".claude-plugin" / "marketplace.json"
    if not manifest.is_file():
        return None
    plugins = {}
    for entry in read_json(manifest).get("plugins", []):
        source = entry.get("source")
        if not isinstance(source, str):
            continue
        plugin = read_json(root / source / ".claude-plugin" / "plugin.json")
        plugins[entry["name"]] = {"version": plugin.get("version") or entry.get("version"), "options": plugin.get("userConfig") or {}}
    return plugins


def select(profile: dict, available: dict) -> list[str]:
    names = profile.get("plugins") or sorted(available)
    unknown = sorted(set(names) - set(available))
    if unknown:
        raise ValueError("Profile selects plugins missing from the marketplace: " + ", ".join(unknown))
    excluded = set(profile.get("exclude", []))
    return [name for name in names if name not in excluded]


def plan(home: Path, profile: dict, options: dict) -> tuple[list, list[str]]:
    """Return pending actions and report lines; an absent marketplace yields only its add action."""
    market = profile["marketplace"]["name"]
    settings = read_json(home / "settings.json")
    available = catalog(home, market)
    if available is None:
        return [("add", market, None)], [f"ADD marketplace {market}"]
    installed = {key: rows[0].get("version") for key, rows in read_json(home / "plugins" / "installed_plugins.json").get("plugins", {}).items() if rows}
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
    for name in sorted(set(available) - set(names)):
        lines.append(f"SKIP {name}@{market}")
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


def run_cli(claude: list[str], args: list[str], stdin: str | None = None) -> tuple[int, str]:
    result = subprocess.run([*claude, *args], input=stdin, capture_output=True, text=True, encoding="utf-8", timeout=600)
    return result.returncode, (result.stdout + result.stderr).strip()


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
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
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
        if args.refresh and catalog(home, profile["marketplace"]["name"]) is not None:
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
            code, output = execute(claude, action, profile)
            print(f"{action[0].upper()} {action[1]} exit={code}" + (f" {output[-300:]}" if code else ""))
            failed |= code != 0
        backup = write_settings(home, profile, select(profile, catalog(home, profile["marketplace"]["name"])))
        if backup:
            print(f"BACKUP {backup}")
        actions, lines = plan(home, profile, options)
        print("\n".join(lines))
        return 2 if failed else (1 if actions else 0)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
