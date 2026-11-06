"""Synthetic Claude homes only; the native CLI is replaced by a fake that edits the same files."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import install_claude_plugins as installer

MARKET = "toolbox"
URL = "https://example.invalid/toolbox.git"


class FakeClaude:
    """Mimic marketplace add, install, update and configure on a synthetic home."""

    def __init__(self, home: Path, versions: dict, schema: dict):
        self.home, self.versions, self.schema, self.calls = home, versions, schema, []

    def publish(self):
        root = self.home / "plugins/marketplaces" / MARKET
        entries = []
        for name, version in self.versions.items():
            manifest = root / name / ".claude-plugin/plugin.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps({"name": name, "version": version, "userConfig": self.schema.get(name, {})}))
            entries.append({"name": name, "source": f"./{name}"})
        (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
        (root / ".claude-plugin/marketplace.json").write_text(json.dumps({"plugins": entries}))

    def edit(self, name, change):
        path = self.home / name
        value = json.loads(path.read_text()) if path.exists() else {}
        change(value)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def __call__(self, claude, args, stdin=None):
        self.calls.append(args)
        if args[:3] == ["plugin", "marketplace", "add"]:
            self.publish()
            self.edit("settings.json", lambda s: s.setdefault("extraKnownMarketplaces", {}).update({MARKET: {"source": {"source": "git", "url": URL}}}))
            location = str(self.home / "plugins/marketplaces" / MARKET)
            self.edit("plugins/known_marketplaces.json", lambda k: k.update({MARKET: {"source": {"source": "git", "url": URL}, "installLocation": location}}))
            return 0, "ok"
        plugin = args[2]
        name = plugin.split("@")[0]
        if args[1] in ("install", "update"):
            self.edit("plugins/installed_plugins.json", lambda d: d.setdefault("plugins", {}).update({plugin: [{"version": self.versions[name]}]}))
        values = dict(item.split("=", 1) for item in args[args.index("--config") + 1::2]) if "--config" in args else {}
        if args[1] == "configure":
            values = json.loads(stdin)
        if values:
            self.edit("settings.json", lambda s: s.setdefault("pluginConfigs", {}).setdefault(plugin, {"options": {}})["options"].update(values))
        return 0, "ok"


class ClaudePluginRestore(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.home = self.base / "claude"
        self.home.mkdir()
        (self.home / "settings.json").write_text(json.dumps({"hooks": {"Stop": ["keep"]}}))
        self.profile = self.base / "profile.json"
        self.profile.write_text(json.dumps({"marketplace": {"name": MARKET, "url": URL}, "exclude": ["company"],
                                            "auto_update": True, "disable_inline": True}))
        self.options = self.base / "options.json"
        self.options.write_text(json.dumps({"pluginConfigs": {f"runner@{MARKET}": {"options": {"python_executable": "C:/env/python.exe"}}}}))
        self.fake = FakeClaude(self.home, {"runner": "0.2.0", "skills": "1.0.0", "company": "0.1.0"},
                               {"runner": {"python_executable": {"type": "string", "default": "python"}},
                                "skills": {"server": {"type": "string", "required": True}, "token": {"type": "string", "sensitive": True}}})
        self.claude = self.base / "claude.exe"
        self.claude.write_bytes(b"")

    def run_tool(self, *extra):
        output = io.StringIO()
        args = ["--profile", str(self.profile), "--options", str(self.options), "--claude-home", str(self.home), "--claude", str(self.claude), *extra]
        with patch.object(installer, "run_cli", self.fake), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            return installer.main(args), output.getvalue()

    def settings(self):
        return json.loads((self.home / "settings.json").read_text())

    def test_fresh_home_installs_selection_and_merges_settings(self):
        before = (self.home / "settings.json").read_bytes()
        code, output = self.run_tool()
        self.assertEqual((code, output.strip()), (1, f"ADD marketplace {MARKET}"))
        self.assertEqual((self.home / "settings.json").read_bytes(), before)
        code, output = self.run_tool("--apply")
        self.assertEqual(code, 0, output)
        installed = json.loads((self.home / "plugins/installed_plugins.json").read_text())["plugins"]
        self.assertEqual(set(installed), {f"runner@{MARKET}", f"skills@{MARKET}"})
        install = next(call for call in self.fake.calls if call[:3] == ["plugin", "install", f"runner@{MARKET}"])
        self.assertIn("python_executable=C:/env/python.exe", install)
        settings = self.settings()
        self.assertEqual(settings["hooks"], {"Stop": ["keep"]})
        self.assertTrue(settings["extraKnownMarketplaces"][MARKET]["autoUpdate"])
        self.assertEqual(settings["enabledPlugins"], {"runner@inline": False, "skills@inline": False})
        self.assertIn(f"UNSET skills@{MARKET} server", output)
        self.assertIn(f"SKIP company@{MARKET}", output)
        self.assertEqual(len(list((self.home / "backups/claude-plugins").glob("*/settings.json"))), 1)
        self.assertEqual(self.run_tool()[0], 0)

    def test_new_version_and_changed_option_are_pending(self):
        self.run_tool("--apply")
        self.fake.versions["runner"] = "0.3.0"
        self.fake.publish()
        self.options.write_text(json.dumps({"runner": {"python_executable": "D:/other/python.exe"}}))
        code, output = self.run_tool()
        self.assertEqual(code, 1)
        self.assertIn(f"UPDATE runner@{MARKET} 0.2.0 -> 0.3.0", output)
        self.assertIn(f"CONFIGURE runner@{MARKET} python_executable", output)
        self.assertEqual(self.run_tool("--apply")[0], 0)
        self.assertEqual(self.settings()["pluginConfigs"][f"runner@{MARKET}"]["options"]["python_executable"], "D:/other/python.exe")

    def test_invalid_options_stop_before_changes(self):
        self.run_tool("--apply")
        before = (self.home / "settings.json").read_bytes()
        for options in ({"skills": {"token": "secret"}}, {"skills": {"missing": "x"}}, {"skills": {"server": "a\nb"}}):
            self.options.write_text(json.dumps(options))
            code, _ = self.run_tool("--apply")
            self.assertEqual(code, 2)
        self.assertEqual((self.home / "settings.json").read_bytes(), before)

    def test_same_name_from_another_source_stops_before_changes(self):
        local = {"source": "directory", "path": str(self.base / "checkout")}
        for target in ("plugins/known_marketplaces.json", "settings.json"):
            with self.subTest(target=target):
                self.fake.calls.clear()
                (self.home / "plugins").mkdir(exist_ok=True)
                (self.home / "plugins/known_marketplaces.json").write_text("{}")
                (self.home / "settings.json").write_text(json.dumps({"hooks": {"Stop": ["keep"]}}))
                if target == "settings.json":
                    self.fake.edit(target, lambda s: s.setdefault("extraKnownMarketplaces", {}).update({MARKET: {"source": local}}))
                else:
                    self.fake.edit(target, lambda k: k.update({MARKET: {"source": local, "installLocation": local["path"]}}))
                before = (self.home / "settings.json").read_bytes()
                code, output = self.run_tool("--apply")
                self.assertEqual(code, 2)
                self.assertIn(f"registered from directory {local['path']}", output)
                self.assertIn(f"claude plugin marketplace remove {MARKET}", output)
                self.assertEqual(self.fake.calls, [])
                self.assertEqual((self.home / "settings.json").read_bytes(), before)

    def test_matching_source_reads_recorded_install_location(self):
        self.fake.publish()
        moved = self.base / "cache-copy"
        (self.home / "plugins/marketplaces" / MARKET).rename(moved)
        recorded = {"source": "github", "repo": "example/toolbox"}
        self.profile.write_text(json.dumps({"marketplace": {"name": MARKET, "url": "git@github.com:example/toolbox.git"}}))
        self.fake.edit("plugins/known_marketplaces.json", lambda k: k.update({MARKET: {"source": recorded, "installLocation": str(moved)}}))
        code, output = self.run_tool()
        self.assertEqual(code, 1)
        self.assertIn(f"INSTALL runner@{MARKET} 0.2.0", output)
        self.assertNotIn("ADD marketplace", output)

    def test_preview_needs_no_cli_and_rejects_home_root(self):
        self.claude.unlink()
        self.assertEqual(self.run_tool()[0], 1)
        self.assertEqual(installer.main(["--profile", str(self.profile), "--claude-home", str(Path.home())]), 2)


if __name__ == "__main__":
    unittest.main()
