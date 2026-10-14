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

    def test_existing_git_marketplace_and_disabled_plugin_are_preserved(self):
        self.value['marketplace'] = {'source_type': 'git', 'source': 'https://example.com/owner/toolkit.git'}
        self.write_profile()
        self.home.mkdir()
        config = self.home / 'config.toml'
        original = '[marketplaces.codex-toolkit]\nsource_type="git"\nsource="git@example.com:owner/toolkit.git"\nref="main"\n[plugins."codex-agent-workflow@codex-toolkit"]\nenabled=false\ncustom="retain"\n'
        config.write_text(original)
        result = self.preview(('plugins',))
        self.assertEqual(result['blocked'], [])
        self.assertEqual(result['steps'], [])
        self.assertEqual(result['preserved_plugins'][0]['enabled'], False)
        self.assertEqual(restore.execute(result, self.home)['status'], 'unchanged')
        self.assertEqual(config.read_text(), original)

    def test_new_git_marketplace_uses_reviewed_ref(self):
        self.value['marketplace'] = {'source_type': 'git', 'source': 'https://example.com/owner/toolkit.git'}
        self.write_profile()
        result = self.preview(('plugins',))
        self.assertEqual(result['steps'][0]['command'][-2:], ['--ref', 'a' * 40])

    def test_other_git_source_blocks_all_writes(self):
        self.value['marketplace'] = {'source_type': 'git', 'source': 'https://example.com/owner/toolkit.git'}
        self.write_profile()
        self.home.mkdir()
        (self.home / 'config.toml').write_text('[marketplaces.codex-toolkit]\nsource_type="git"\nsource="https://example.com/other/toolkit.git"\n')
        self.assertTrue(self.preview(('plugins',))['blocked'])

    def test_credentials_in_marketplace_source_are_rejected(self):
        self.value['marketplace'] = {'source_type': 'git', 'source': 'https://token@example.com/owner/toolkit.git'}
        self.write_profile()
        with self.assertRaisesRegex(ValueError, 'credential-free'):
            self.preview(('plugins',))

    def test_explicit_plugin_subset_cannot_expand_profile(self):
        with self.git:
            with self.assertRaisesRegex(ValueError, 'outside the profile'):
                restore.plan(self.root, self.profile, self.home, ('plugins',), selected_plugins=['other'])

    def test_changed_config_stops_before_delegation(self):
        result = self.preview(('plugins',))
        self.home.mkdir()
        (self.home / 'config.toml').write_text('custom = true')
        with patch.object(restore.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'changed'):
                restore.execute(result, self.home)
            run.assert_not_called()
        self.assertFalse((self.home / '.setup-restore.lock').exists())

    def test_existing_lock_stops_without_removing_other_owner_lock(self):
        result = self.preview(('plugins',))
        self.home.mkdir()
        lock = self.home / '.setup-restore.lock'
        lock.write_text('other owner')
        with self.assertRaisesRegex(ValueError, 'device-local lock'):
            restore.execute(result, self.home)
        self.assertEqual(lock.read_text(), 'other owner')

    def test_config_backup_is_recoverable_after_partial_failure(self):
        self.home.mkdir()
        config = self.home / 'config.toml'
        config.write_text('custom = "original"')
        result = self.preview(('skills',))
        with patch.object(restore.subprocess, 'run', return_value=subprocess.CompletedProcess([], 7)):
            with self.assertRaisesRegex(ValueError, 'completed steps=0'):
                restore.execute(result, self.home)
        backups = list((self.home / 'backups').glob('setup-restore-*/config.toml'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), config.read_bytes())
        config.write_text('custom = "later"')
        config.write_bytes(backups[0].read_bytes())
        self.assertEqual(config.read_text(), 'custom = "original"')

    def test_windows_marketplace_git_options_are_process_local_and_preserve_existing_options(self):
        with patch.object(restore.sys, 'platform', 'win32'), patch.dict(restore.os.environ, {'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'fixture.option', 'GIT_CONFIG_VALUE_0': 'preserve'}, clear=True):
            environment = restore.child_environment(self.home)
            self.assertEqual(environment['GIT_CONFIG_COUNT'], '2')
            self.assertEqual(environment['GIT_CONFIG_VALUE_0'], 'preserve')
            self.assertEqual(environment['GIT_CONFIG_KEY_1'], 'core.longpaths')
            self.assertEqual(restore.os.environ['GIT_CONFIG_COUNT'], '1')

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
