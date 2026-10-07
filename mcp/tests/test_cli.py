"""Check terminal entrypoint behavior without installing or packaging anything."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'mcp/mcp_servers/tool_setup/src'))
from codex_tool_setup import cli


class TerminalEntrypoints(unittest.TestCase):
    def invoke(self, args):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(sys, 'argv', ['codex-setup', *args]), redirect_stdout(output), redirect_stderr(errors):
            result = cli.setup_main()
        return result, output.getvalue(), errors.getvalue()

    def handler(self, name):
        module = ModuleType('codex_tool_setup._setup.mcp.scripts.'+name)
        module.main = Mock(return_value=0)
        return module

    def test_help_lists_terminal_categories(self):
        for args in ([], ['--help'], ['--list']):
            with self.subTest(args=args):
                result, output, errors = self.invoke(args)
                self.assertEqual(result, 0)
                self.assertIn('agents, skills, plugins, mcp', output)
                self.assertNotIn('--web', output)
                self.assertEqual(errors, '')

    def test_removed_web_actions_fail_without_loading_a_server(self):
        for action in ('--web', 'web'):
            with self.subTest(action=action):
                result, output, errors = self.invoke([action])
                self.assertEqual(result, 2)
                self.assertEqual(output, '')
                self.assertIn('Unknown category', errors)

    def test_governance_categories_preserve_preview_arguments(self):
        module = self.handler('manage_categories')
        with patch.dict(sys.modules, {module.__name__:module}):
            for category in ('agents', 'skills', 'plugins'):
                with self.subTest(category=category):
                    args = [category, '--list', '--codex-home', '/selected/home']
                    self.assertEqual(self.invoke(args)[0], 0)
                    module.main.assert_called_with(args)

    def test_mcp_selection_keeps_the_guided_cli(self):
        module = self.handler('install_development_tool')
        with patch.dict(sys.modules, {module.__name__:module}):
            self.assertEqual(self.invoke(['mcp', 'edge-devtools', '--apply'])[0], 0)
        module.main.assert_called_once_with(['--guided', '--interface', 'mcp', '--tool', 'edge-devtools', '--apply'])

    def test_mcp_listing_preserves_flags(self):
        module = self.handler('install_development_tool')
        with patch.dict(sys.modules, {module.__name__:module}):
            self.assertEqual(self.invoke(['mcp', '--list'])[0], 0)
        module.main.assert_called_once_with(['--guided', '--interface', 'mcp', '--list'])


if __name__ == '__main__':
    unittest.main()
