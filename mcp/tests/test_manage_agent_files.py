"""Guidance transport must preserve ownership, conflicts and native permissions."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('agent_files', Path(__file__).parents[1] / 'scripts/manage_agent_files.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class AgentFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.repo('source')
        self.target = self.repo('target')
        (self.source / 'AGENTS.md').write_bytes(b'Canonical instructions\r\n')

    def repo(self, name):
        path = self.base / name
        path.mkdir()
        subprocess.run(['git', 'init', '-q', str(path)], check=True)
        subprocess.run(['git', '-C', str(path), 'remote', 'add', 'origin', 'https://github.com/example/project.git'], check=True)
        subprocess.run(['git', '-C', str(path), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
        return path

    def bundle(self):
        path = self.base / 'snapshot'
        core.snapshot(self.source, ['AGENTS.md'], path, True)
        return path

    def test_preview_does_not_write_and_roundtrip_preserves_bytes(self):
        bundle = self.base / 'snapshot'
        core.snapshot(self.source, ['AGENTS.md'], bundle)
        self.assertFalse(bundle.exists())
        self.bundle()
        core.restore(self.target, bundle)
        self.assertFalse((self.target / 'AGENTS.md').exists())
        core.restore(self.target, bundle, True)
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), b'Canonical instructions\r\n')
        self.assertEqual(core.restore(self.target, bundle)['files'][0]['status'], 'CURRENT')
        self.assertEqual(core.git(self.target, 'status', '--porcelain'), b'')

    def test_conflict_preserved_until_replace_and_backup_verified(self):
        bundle = self.bundle()
        (self.target / 'AGENTS.md').write_bytes(b'Local edits')
        with self.assertRaises(ValueError):
            core.restore(self.target, bundle, True)
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), b'Local edits')
        core.restore(self.target, bundle, True, True)
        backups = list((self.target / '.git/agent-file-backups').glob('*/AGENTS.md'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), b'Local edits')

    def test_wrong_repository_and_tampered_snapshot_blocked(self):
        bundle = self.bundle()
        subprocess.run(['git', '-C', str(self.target), 'remote', 'set-url', 'origin', 'https://github.com/example/other.git'], check=True)
        with self.assertRaises(ValueError):
            core.restore(self.target, bundle, True)
        (bundle / 'files/AGENTS.md').write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            core.load_snapshot(bundle)
        self.assertFalse((self.target / 'AGENTS.md').exists())

    def test_settings_and_escape_cannot_be_snapshotted(self):
        for name in ['.codex/config.toml', '.claude/settings.json', '../AGENTS.md', 'C:/AGENTS.md']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                core.snapshot(self.source, [name], self.base / 'snapshot', True)
        self.assertFalse((self.base / 'snapshot').exists())

    def test_tracked_guidance_cannot_be_overwritten(self):
        bundle = self.bundle()
        (self.target / 'AGENTS.md').write_bytes(b'Owned source')
        core.git(self.target, 'add', 'AGENTS.md')
        with self.assertRaises(ValueError):
            core.restore(self.target, bundle, True, True)
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), b'Owned source')

    def test_ignore_preserves_rules_and_repeats_without_writes(self):
        path = self.target / '.git/info/exclude'
        path.write_bytes(b'# existing\nlocal-only.txt\n')
        core.exclude(self.target, ['/.playwright-mcp/', '/.pytest_cache/'], True)
        before = path.read_bytes()
        self.assertTrue(before.startswith(b'# existing\nlocal-only.txt\n'))
        self.assertEqual(core.exclude(self.target, ['/.playwright-mcp/', '/.pytest_cache/'], True)['status'], 'CURRENT')
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(core.git(self.target, 'check-ignore', '.playwright-mcp/output.png').strip(), b'.playwright-mcp/output.png')

    def test_ignore_refuses_tracked_matches(self):
        (self.target / 'docs').mkdir()
        (self.target / 'docs/design.md').write_text('source', encoding='utf-8')
        core.git(self.target, 'add', 'docs/design.md')
        with self.assertRaises(ValueError):
            core.exclude(self.target, ['/docs/'], True)

    def test_claude_import_uses_override_and_native_role(self):
        (self.target / 'AGENTS.override.md').write_text('effective', encoding='utf-8')
        name = '.codex/agents/reviewer.toml'
        path = self.target / name
        path.parent.mkdir(parents=True)
        path.write_text('name = "reviewer"\ndescription = "Review assigned changes"\ndeveloper_instructions = "Preserve scope"\n', encoding='utf-8')
        core.claude(self.target, 'AGENTS.override.md', [name], True)
        self.assertEqual((self.target / 'CLAUDE.md').read_text(), '@AGENTS.override.md\n')
        generated = (self.target / '.claude/agents/reviewer.md').read_text()
        self.assertIn('Preserve scope', generated)
        self.assertNotIn('permissionMode', generated)
        self.assertNotIn('model:', generated)
        path.write_text(path.read_text() + 'sandbox_mode = "read-only"\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            core.claude(self.target, 'AGENTS.override.md', [name], True)

    def test_existing_project_manifest_requires_current_owner_and_selected_files(self):
        store = self.source / 'project-agents'
        (store / 'example').mkdir(parents=True)
        raw = b'Private instructions\n'
        (store / 'example/AGENTS.md').write_bytes(raw)
        entry = {'source_repository': 'https://github.com/example/project.git',
                 'files': [{'path': 'AGENTS.md', 'sha256': core.sha(raw), 'bytes': len(raw)}]}
        manifest = {'projects': {'example': entry}}
        (store / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaises(ValueError):
            core.restore_project(self.target, store, 'example', ['AGENTS.md'], True)
        core.restore_project(self.target, store, 'example', ['AGENTS.md'], True, historical=True)
        self.assertEqual((self.target / 'AGENTS.md').read_bytes(), raw)
        entry['files'][0]['source_status'] = 'retained-backup-source-absent'
        (store / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaises(ValueError):
            core.restore_project(self.target, store, 'example', ['AGENTS.md'], True, historical=True)

    def test_local_claude_entry_preserves_tracked_project_instructions(self):
        (self.target / 'CLAUDE.md').write_bytes(b'Owned project instructions\n')
        core.git(self.target, 'add', 'CLAUDE.md')
        (self.target / 'AGENTS.override.md').write_bytes(b'Local workspace entry\n')
        core.claude(self.target, 'AGENTS.override.md', [], True, target_entry='CLAUDE.local.md')
        self.assertEqual((self.target / 'CLAUDE.md').read_bytes(), b'Owned project instructions\n')
        self.assertEqual((self.target / 'CLAUDE.local.md').read_bytes(), b'@AGENTS.override.md\n')


if __name__ == '__main__':
    unittest.main()
