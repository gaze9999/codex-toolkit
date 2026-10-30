import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'mcp/scripts'))

import install_development_tool as installer


class DevelopmentToolInstallation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config.toml'
        self.prefix = self.root / 'npm'
        self.original = 'model = "preserved"\n[mcp_servers.existing]\ncommand = "existing-server"\n'
        self.config.write_text(self.original, encoding='utf-8')
        self.manifest = json.loads((ROOT / 'mcp/tools/development-tools.requirements.json').read_text())
        self.env = patch.dict(os.environ)
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_http(self, apply=True):
        args = ['--tool', 'openai-docs', '--interface', 'mcp', '--config', str(self.config),
                '--npm-prefix', str(self.prefix), '--no-guide']
        if apply:
            args += ['--apply', '--yes']
        with contextlib.redirect_stdout(io.StringIO()), patch.object(installer.subprocess, 'run') as run:
            result = installer.main(args)
        run.assert_not_called()
        return result

    def test_http_preview_apply_and_repeat_preserve_other_settings(self):
        self.assertEqual(self.run_http(apply=False), 0)
        self.assertEqual(self.config.read_text(), self.original)
        self.assertEqual(self.run_http(), 0)
        first = self.config.read_bytes()
        settings = tomllib.loads(first.decode())
        self.assertEqual(settings['mcp_servers'].pop('openaiDeveloperDocs'), {
            'url': 'https://developers.openai.com/mcp', 'enabled': True, 'required': False,
        })
        self.assertEqual(settings, tomllib.loads(self.original))
        backups = set(self.root.iterdir())
        self.assertEqual(self.run_http(), 0)
        self.assertEqual(self.config.read_bytes(), first)
        self.assertEqual(set(self.root.iterdir()), backups)

    def test_http_conflict_and_disabled_entry_are_preserved(self):
        for url, enabled in [('https://example.test/mcp', True), ('https://developers.openai.com/mcp', False)]:
            with self.subTest(url=url, enabled=enabled):
                original = self.original + f'\n[mcp_servers.openaiDeveloperDocs]\nurl = "{url}"\nenabled = {str(enabled).lower()}\n'
                self.config.write_text(original)
                self.assertEqual(self.run_http(), 2)
                self.assertEqual(self.config.read_text(), original)

    def test_http_equivalent_provider_is_reused(self):
        original = self.original + '\n[mcp_servers.alternate_docs]\nurl = "https://developers.openai.com/mcp"\n'
        self.config.write_text(original)
        self.assertEqual(self.run_http(), 0)
        self.assertEqual(self.config.read_text(), original)

    def apply_node(self, platform, entry_exists=True):
        spec = installer.tool_spec('playwright', self.manifest, 'mcp')
        package_root = self.prefix / ('node_modules' if platform == 'windows' else 'lib/node_modules')
        entry = package_root / spec['mcp']['entry_suffix'].lstrip('/')
        if entry_exists:
            entry.parent.mkdir(parents=True, exist_ok=True)
            entry.write_text('// installed package fixture\n')
        recipe = spec['automatic_install'].get(platform, spec['automatic_install'].get('all'))
        planned = {'tool': 'playwright', 'platform': platform, 'spec': spec, 'blocked': [],
                   'steps': [installer.recipe_step('playwright', recipe, self.prefix)]}
        with patch.object(installer, 'install_command', side_effect=lambda command, env: command), patch.object(
            installer.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)
        ) as run, patch.object(installer.shutil, 'which', return_value='/fixture/node'):
            installer.apply_plan(planned, self.manifest, self.config, self.prefix, yes=True)
        self.assertEqual(run.call_count, 1)
        return entry

    def test_node_registration_uses_platform_global_package_layout(self):
        for platform in ['macos', 'linux', 'windows']:
            with self.subTest(platform=platform):
                self.config.write_text(self.original)
                entry = self.apply_node(platform)
                settings = tomllib.loads(self.config.read_text())
                server = settings['mcp_servers'].pop('playwright')
                self.assertEqual(server['command'], '/fixture/node')
                self.assertEqual(server['args'][0], str(entry))
                self.assertEqual(settings, tomllib.loads(self.original))

    def test_missing_node_entrypoint_does_not_register(self):
        with self.assertRaisesRegex(ValueError, 'Installed MCP entrypoint is missing'):
            self.apply_node('macos', entry_exists=False)
        self.assertEqual(self.config.read_text(), self.original)


if __name__ == '__main__':
    unittest.main()
