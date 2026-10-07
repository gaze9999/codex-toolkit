import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import restore_profile as restore


class RestoreChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root, self.home, self.private = [self.base / name for name in ('toolkit', 'home', 'private')]
        (self.root / 'plugins').mkdir(parents=True)
        (self.root / 'mcp/tools').mkdir(parents=True)
        (self.root / 'skills/readme-maintainer').mkdir(parents=True)
        (self.root / 'skills/readme-maintainer/SKILL.md').write_text('example')
        (self.root / 'plugins/catalog.json').write_text(json.dumps({'bundles': [{'id': 'agent-workflow', 'status': 'ready', 'skills': ['agent-governance']}]}))
        (self.root / 'mcp/tools/development-tools.requirements.json').write_text(json.dumps({'tools': {'context7': {}}}))
        (self.private / 'agents').mkdir(parents=True)
        (self.private / 'profiles').mkdir()
        for name in ('AGENTS.md', 'subagents.config.toml'):
            (self.private / 'agents' / name).write_text('personal')
        self.value = {'schema_version': 1, 'toolkit_revision': 'a' * 40, 'agents_source': '../agents', 'skills': ['readme-maintainer'], 'plugins': ['codex-agent-workflow'], 'tools': {'windows': [{'id': 'context7', 'interface': 'mcp'}], 'macos': [{'id': 'context7', 'interface': 'mcp'}]}}
        self.profile = self.private / 'profiles/workstation.json'
        self.write_profile()
        self.git = patch.object(restore.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0, 'a' * 40), subprocess.CompletedProcess([], 0, '')])

    def write_profile(self):
        self.profile.write_text(json.dumps(self.value))

    def preview(self, sections=('agents', 'skills', 'plugins')):
        with self.git:
            return restore.plan(self.root, self.profile, self.home, sections)

    def test_preview_does_not_create_home_or_include_tools(self):
        result = self.preview()
        self.assertFalse(self.home.exists())
        self.assertFalse(any(row['section'] == 'tools' for row in result['steps']))
        self.assertTrue(all('--apply' not in row['command'] for row in result['steps']))

    def test_profile_duplicate_direct_plugin_skill_is_rejected(self):
        self.value['skills'] = ['agent-governance']
        self.write_profile()
        with self.assertRaisesRegex(ValueError, 'duplicate direct'):
            self.preview()

    def test_unknown_profile_fields_are_rejected(self):
        self.value['env'] = {'TOKEN': 'do-not-import-values'}
        self.write_profile()
        with self.assertRaisesRegex(ValueError, 'Unsupported profile'):
            self.preview()

    def test_wrong_revision_is_rejected(self):
        self.value['toolkit_revision'] = 'b' * 40
        self.write_profile()
        with self.assertRaisesRegex(ValueError, 'pinned revision'):
            self.preview()

    def test_dirty_checkout_is_rejected(self):
        with patch.object(restore.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0, 'a' * 40), subprocess.CompletedProcess([], 0, ' M changed.py')]):
            with self.assertRaisesRegex(ValueError, 'clean'):
                restore.plan(self.root, self.profile, self.home, ('skills',))

    def test_existing_plugin_owner_blocks_all_writes(self):
        self.home.mkdir()
        (self.home / 'config.toml').write_text('[plugins."codex-agent-workflow@old-market"]\nenabled = true\n')
        result = self.preview()
        with patch.object(restore.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'blockers'):
                restore.execute(result, self.home)
            run.assert_not_called()

    def test_existing_direct_plugin_skill_blocks_writes(self):
        (self.home / 'skills/agent-governance').mkdir(parents=True)
        (self.home / 'skills/agent-governance/SKILL.md').write_text('custom')
        result = self.preview()
        self.assertTrue(any('overlap' in message for message in result['blocked']))

    def test_platform_tools_are_explicit_and_independent(self):
        with patch.object(restore.sys, 'platform', 'darwin'):
            result = self.preview(('tools',))
        self.assertEqual([row['item'] for row in result['steps']], ['context7'])
        self.assertIn('--interface', result['steps'][0]['command'])

    def test_failure_stops_later_steps(self):
        preview = {'blocked': [], 'steps': [{'section': 'skills', 'command': ['fake1']}, {'section': 'plugins', 'command': ['fake2']}]}
        with patch.object(restore.subprocess, 'run', return_value=subprocess.CompletedProcess([], 7)) as run:
            with self.assertRaisesRegex(ValueError, 'exit=7'):
                restore.execute(preview, self.home)
            self.assertEqual(run.call_count, 1)

    def test_personal_source_can_install_with_existing_global_installer(self):
        script = Path(restore.__file__).with_name('install_global_agents.py')
        result = subprocess.run([sys.executable, '-B', str(script), '--source-root', str(self.private / 'agents'), '--codex-home', str(self.home), '--install'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.home / 'AGENTS.md').read_text(), 'personal')
        (self.home / 'AGENTS.md').write_text('custom')
        result = subprocess.run([sys.executable, '-B', str(script), '--source-root', str(self.private / 'agents'), '--codex-home', str(self.home), '--install'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual((self.home / 'AGENTS.md').read_text(), 'custom')


if __name__ == '__main__':
    unittest.main()
