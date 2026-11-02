import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'mcp/scripts'))
import check_development_tools as checker
import install_development_tool as installer


class SafariSetup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config.toml'
        self.original = 'model = "preserved"\n[mcp_servers.existing]\ncommand = "existing"\n'
        self.config.write_text(self.original, encoding='utf-8')
        self.manifest = json.loads((ROOT / 'mcp/tools/development-tools.requirements.json').read_text(encoding='utf-8'))
        self.spec = self.manifest['tools']['safari-mcp']

    def plan(self, system='macos', **kwargs):
        return installer.plan('safari-mcp', self.manifest, system, self.root / 'npm', self.config, interface='mcp', **kwargs)

    def test_capability_probe_rejects_old_or_failed_driver(self):
        for code, output, expected in [(0, '--mcp', True), (0, 'WebDriver help', False), (1, '--mcp', False)]:
            with self.subTest(code=code, output=output), patch.object(Path, 'is_file', return_value=True), patch.object(checker.subprocess, 'run', return_value=subprocess.CompletedProcess([], code, output, '')) as run:
                self.assertEqual(checker.safari_mcp_ready('/usr/bin/safaridriver'), expected)
                self.assertEqual(run.call_args.args[0], ['/usr/bin/safaridriver', '--help'])
        with patch.object(Path, 'is_file', return_value=True), patch.object(checker.subprocess, 'run', side_effect=subprocess.TimeoutExpired('driver', 10)):
            self.assertFalse(checker.safari_mcp_ready('/usr/bin/safaridriver'))

    def test_preview_registration_repeat_and_other_settings(self):
        with patch.object(checker, 'native_mcp_command', return_value='/usr/bin/safaridriver'), patch.object(checker, 'find_command', return_value='/usr/bin/safaridriver'), patch.object(installer, 'native_mcp_command', return_value='/usr/bin/safaridriver'), patch.object(installer.subprocess, 'run') as run:
            planned = self.plan()
            self.assertEqual(planned['blocked'], [])
            self.assertEqual(planned['steps'][0]['commands'], [])
            self.assertEqual(self.config.read_text(), self.original)
            installer.apply_plan(planned, self.manifest, self.config, self.root / 'npm', yes=True)
            first = self.config.read_bytes()
            settings = tomllib.loads(first.decode())
            self.assertEqual(settings['mcp_servers'].pop('safari-mcp'), {'command': '/usr/bin/safaridriver', 'args': ['--mcp'], 'enabled': True, 'required': False})
            self.assertEqual(settings, tomllib.loads(self.original))
            self.assertEqual(self.plan()['steps'], [])
            self.assertEqual(self.config.read_bytes(), first)
            run.assert_not_called()

    def test_unsupported_platform_has_no_steps(self):
        for system in ['windows', 'linux']:
            with self.subTest(system=system):
                planned = self.plan(system)
                self.assertEqual(planned['check']['status'], 'unsupported_platform')
                self.assertEqual(planned['steps'], [])
                self.assertEqual(self.config.read_text(), self.original)

    def test_missing_driver_blocks_registration(self):
        with patch.object(checker, 'native_mcp_command', return_value=None), patch.object(installer, 'native_mcp_command', return_value=None):
            planned = self.plan()
            self.assertTrue(planned['blocked'])
            with self.assertRaises(ValueError):
                installer.apply_plan(planned, self.manifest, self.config, self.root / 'npm', yes=True)
        self.assertEqual(self.config.read_text(), self.original)

    def test_plain_webdriver_and_disabled_entries_do_not_count_as_mcp(self):
        for args, enabled in [('[]', 'true'), ('["--mcp"]', 'false')]:
            self.config.write_text(self.original + f'\n[mcp_servers.safari-mcp]\ncommand = "/usr/bin/safaridriver"\nargs = {args}\nenabled = {enabled}\n', encoding='utf-8')
            self.assertEqual(checker.mcp_state(self.spec['mcp'], self.config)[0], 'conflict')

    def test_preview_falls_back_to_technology_preview(self):
        with patch.object(checker, 'safari_mcp_ready', side_effect=[False, True]):
            self.assertEqual(checker.native_mcp_command('safari-mcp'), '/Applications/Safari Technology Preview.app/Contents/MacOS/safaridriver')

    def test_explicit_driver_requires_mcp_capability(self):
        driver = self.root / 'safaridriver'
        driver.touch()
        with patch.object(installer, 'safari_mcp_ready', return_value=False):
            with self.assertRaisesRegex(ValueError, 'Safari 27'):
                self.plan(mcp_executable=driver)
        with patch.object(installer, 'safari_mcp_ready', return_value=True):
            planned = self.plan(mcp_executable=driver)
            self.assertEqual(planned['blocked'], [])
            self.assertEqual(planned['mcp_executable'], str(driver))


if __name__ == '__main__':
    unittest.main()
