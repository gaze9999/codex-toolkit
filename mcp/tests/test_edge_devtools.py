import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('edge_launcher', ROOT / 'mcp_servers/edge_devtools/src/edge_devtools_mcp/launcher.py')
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class EdgeLaunchTests(unittest.TestCase):
    def test_windows_relaunch_flag_preserves_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = root / 'node.exe'
            node.touch()
            entry = root / 'build/src/bin/chrome-devtools-mcp.js'
            entry.parent.mkdir(parents=True)
            entry.touch()
            pin = json.loads((ROOT / 'mcp_servers/edge_devtools/upstream.json').read_text(encoding='utf-8'))
            (root / 'package.json').write_text(json.dumps(pin), encoding='utf-8')
            args = argparse.Namespace(node_path=node, browser_url=None, executable_path=None, headed=False)
            probe = subprocess.CompletedProcess([], 0, 'v24.22.1\n', '')
            with patch.object(launcher.subprocess, 'run', return_value=probe), patch.object(launcher, 'edge_path', return_value=root / 'edge.exe'):
                for platform in ('win32', 'darwin', 'linux'):
                    with self.subTest(platform=platform), patch.object(launcher.sys, 'platform', platform):
                        command = launcher.command(args, root)
                        self.assertEqual('--chromeArg=--edge-skip-compat-layer-relaunch' in command, platform == 'win32')
                        self.assertIn('--isolated', command)
                        self.assertIn('--headless', command)
                        self.assertNotIn('--no-sandbox', command)
                args.browser_url = 'http://127.0.0.1:9222'
                with patch.object(launcher.sys, 'platform', 'win32'):
                    command = launcher.command(args, root)
                    self.assertNotIn('--chromeArg=--edge-skip-compat-layer-relaunch', command)
                    self.assertIn('--browserUrl', command)


if __name__ == '__main__':
    unittest.main()
