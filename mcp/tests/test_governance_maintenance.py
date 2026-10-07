import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'mcp/scripts'))
import audit_skills
import sync_local_plugins as sync


class ReferenceChecks(unittest.TestCase):
    def audit(self, text, paths=()):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'README.md').write_text(text)
            for relative in paths:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('')
            errors = []
            audit_skills.audit_links(root, errors)
            return errors

    def test_missing_repository_document_is_detected(self):
        self.assertEqual(self.audit('Read `docs/setup/removed.md`'), ['inline_path:README.md->docs/setup/removed.md'])

    def test_existing_repository_document_is_accepted(self):
        self.assertEqual(self.audit('Read `docs/setup/cli.md`', ['docs/setup/cli.md']), [])

    def test_missing_launch_entry_is_detected(self):
        self.assertEqual(self.audit('Use `launch-removed.cmd action`'), ['inline_path:README.md->launch-removed.cmd'])

    def test_external_urls_and_placeholders_are_not_local_files(self):
        self.assertEqual(self.audit('Read `docs/<topic>.md` and `https://example.com/docs/x.md`'), [])

    def test_skill_agent_metadata_resolves_from_its_owner(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'README.md').write_text('')
            folder = root / 'skills/example'
            (folder / 'agents').mkdir(parents=True)
            (folder / 'agents/openai.yaml').write_text('')
            (folder / 'SKILL.md').write_text('Use `agents/openai.yaml`')
            errors = []
            audit_skills.audit_links(root, errors)
            self.assertEqual(errors, [])


class PluginChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root, self.home, self.old = [self.base / name for name in ('root', 'home', 'old')]
        self.home.mkdir()
        self.root.mkdir()
        self.bundles, self.contents, entries = [], {}, []
        for identifier in ('alpha', 'beta'):
            name = 'codex-' + identifier
            files = {'plugin.json': sync.encode({'name': name, 'version': '0.1.0'}), 'skills/example/SKILL.md': b'original'}
            folder = self.old / 'plugins' / name
            for relative, raw in files.items():
                target = folder / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            self.bundles.append({'id': identifier, 'status': 'ready', 'manifest': {'name': name}})
            self.contents[name] = (files.copy(), {'plugin': name, 'version': '0.1.0', 'files': {}})
            entries.append({'name': name, 'source': {'source': 'local', 'path': './plugins/' + name}})
        index = self.old / '.agents/plugins/marketplace.json'
        index.parent.mkdir(parents=True)
        index.write_bytes(sync.encode({'name': sync.MARKET, 'plugins': entries}))
        self.config = self.home / 'config.toml'
        self.config.write_text('[marketplaces.codex-toolkit]\nsource_type="local"\nsource=' + json.dumps(str(self.old)) + '\n' +
                               '\n'.join('[plugins."codex-' + identifier + '@codex-toolkit"]\nenabled=true\n' for identifier in ('alpha', 'beta')))
        self.catalog = patch.object(sync, 'load_catalog', return_value=self.bundles)
        self.payload = patch.object(sync, 'payload', side_effect=lambda root, bundle: self.contents[bundle['manifest']['name']])
        self.catalog.start()
        self.payload.start()
        self.addCleanup(self.payload.stop)
        self.addCleanup(self.catalog.stop)
        self.addCleanup(self.temp.cleanup)

    def plan(self, selected=None):
        return sync.plan(self.root, self.home, selected)

    def test_preview_does_not_create_files(self):
        before = sorted(str(p.relative_to(self.base)) for p in self.base.rglob('*'))
        self.plan()
        self.assertEqual(before, sorted(str(p.relative_to(self.base)) for p in self.base.rglob('*')))

    def test_one_selected_source_preserves_other_installed_content(self):
        self.contents['codex-alpha'][0]['skills/example/SKILL.md'] = b'new'
        self.contents['codex-beta'][0]['skills/example/SKILL.md'] = b'unrelated candidate'
        planned = self.plan(['alpha'])
        self.assertEqual(planned['packages']['codex-beta'][0]['skills/example/SKILL.md'], b'original')
        self.assertEqual(planned['changes'][0]['changed_files'], ['skills/example/SKILL.md'])

    def test_uninstalled_selection_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '已註冊'):
            self.plan(['new'])

    def test_concurrent_source_change_refuses_apply(self):
        planned = self.plan()
        self.contents['codex-alpha'] = ({**self.contents['codex-alpha'][0], 'new.txt': b'new'}, self.contents['codex-alpha'][1])
        with self.assertRaisesRegex(ValueError, '來源已改變'):
            sync.recheck(planned)

    def test_concurrent_target_change_refuses_apply(self):
        planned = self.plan()
        (self.old / 'plugins/codex-alpha/skills/example/SKILL.md').write_bytes(b'local edit')
        with self.assertRaisesRegex(ValueError, '原安裝來源已改變'):
            sync.recheck(planned)

    def test_concurrent_registration_change_refuses_apply(self):
        planned = self.plan()
        self.config.write_text(self.config.read_text().replace('enabled=true', 'enabled=false'))
        with self.assertRaisesRegex(ValueError, '設定已改變'):
            sync.recheck(planned)

    def test_snapshot_marks_working_tree_and_preserves_all_registered_names(self):
        with patch.object(sync.subprocess, 'run', return_value=type('Result', (), {'returncode': 0, 'stdout': 'abcdef\n'})()):
            output = sync.snapshot(self.plan(['alpha']))
        index = json.loads((output / '.agents/plugins/marketplace.json').read_text())
        self.assertEqual({row['name'] for row in index['plugins']}, {'codex-alpha', 'codex-beta'})
        provenance = json.loads((output / 'plugins/codex-alpha/source-manifest.json').read_text())
        self.assertEqual(provenance['source_state'], 'working-tree')
        self.assertEqual(provenance['source_revision'], 'abcdef')
        self.assertEqual((output / 'plugins/codex-beta/skills/example/SKILL.md').read_bytes(), b'original')

    def test_disabled_setting_refuses_native_replacement(self):
        self.config.write_text(self.config.read_text().replace('enabled=true', 'enabled=false'))
        with self.assertRaisesRegex(ValueError, '停用'):
            self.plan()

    def test_native_failure_restores_previous_source_without_rewriting_config(self):
        planned = self.plan()
        before = self.config.read_bytes()
        calls = []
        def fake_native(cli, home, *args):
            calls.append(args)
            return {}
        with patch.object(sync.subprocess, 'run', return_value=type('Result', (), {'returncode': 0, 'stdout': 'abcdef\n'})()), \
             patch.object(sync, 'switch', side_effect=ValueError('fixture failure')), \
             patch.object(sync, 'native', side_effect=fake_native), \
             patch.object(sync, 'verify') as verify:
            with self.assertRaisesRegex(ValueError, '原生復原已核對'):
                sync.apply(planned, 'codex')
        self.assertEqual(self.config.read_bytes(), before)
        self.assertIn(('marketplace', 'add', str(self.old), '--json'), calls)
        self.assertEqual(verify.call_count, 1)


class PackagedEntryChecks(unittest.TestCase):
    def test_resource_copy_supports_package_relative_plugin_entry(self):
        import importlib
        from prepare_mcp_release import copy_installer_resources
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'isolated_setup_resources'
            copy_installer_resources(root, target)
            sys.path.insert(0, temp)
            try:
                module = importlib.import_module('isolated_setup_resources.mcp.scripts.sync_local_plugins')
                self.assertEqual(module.ROOT, target)
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as exited:
                    module.main(['--help'])
                self.assertEqual(exited.exception.code, 0)
            finally:
                sys.path.remove(temp)
                for name in list(sys.modules):
                    if name.startswith('isolated_setup_resources'):
                        del sys.modules[name]


if __name__ == '__main__':
    unittest.main()
