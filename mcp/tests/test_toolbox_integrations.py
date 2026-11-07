"""Check host declarations, source closure and non-overwriting runtime preparation."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tooling'))
sys.path.insert(0, str(ROOT / 'mcp/scripts'))
from toolbox_integrations import augment
import toolbox_runtime as runtime
import toolbox_codex as codex


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        registry = patch.dict(runtime.os.environ, {'TOOLBOX_RUNTIMES': str(self.base / 'runtimes.json')})
        registry.start()
        self.addCleanup(registry.stop)
        self.public = self.base / 'public'
        self.private = self.base / 'private'
        (self.public / 'tooling').mkdir(parents=True)
        self.private.mkdir()
        (self.public / 'tooling/toolbox_runtime.py').write_bytes(b'# runtime fixture\n')
        self.profile = {'schema_version': 1, 'owner': 'Example', 'plugins': [{
            'name': 'connector-example', 'version': '0.1.0', 'description': 'Example connector',
            'setup': 'Select the destination runtime.', 'connectors': [{
                'name': 'example', 'server': {'type': 'http', 'url': 'https://example.test/mcp'}}]}]}

    def test_connector_only_plugin_and_fixed_endpoint(self):
        packages = []
        rows, files = augment(self.public, self.private, packages, self.profile)
        self.assertEqual(rows['example']['state'], 'declaration-prepared')
        self.assertIsNone(rows['example']['loaded'])
        self.assertEqual(packages[0]['skills'], [])
        self.assertEqual(json.loads(packages[0]['files']['.mcp.json'])['mcpServers']['example']['type'], 'http')
        native = json.loads(packages[0]['files']['mcp.json'])['mcpServers']['example']
        self.assertEqual(native['type'], 'streamable-http')

    def test_url_credentials_and_literal_auth_are_rejected(self):
        for server in ({'type': 'http', 'url': 'https://secret@example.test/mcp'},
                       {'type': 'http', 'url': 'https://example.test/mcp?key=secret'},
                       {'type': 'http', 'url': 'https://example.test/mcp', 'headers': {'Authorization': 'Bearer secret'}}):
            with self.subTest(server=server), self.assertRaises(ValueError):
                self.profile['plugins'][0]['connectors'][0]['server'] = server
                augment(self.public, self.private, [], self.profile)

    def test_configuration_reference_must_be_declared(self):
        self.profile['plugins'][0]['connectors'][0]['server'] = {'command': '${user_config.python}', 'args': []}
        with self.assertRaisesRegex(ValueError, 'Undeclared'):
            augment(self.public, self.private, [], self.profile)

    def test_runtime_project_must_be_in_payload(self):
        self.profile['plugins'][0]['connectors'][0]['runtime'] = {'kind': 'python', 'projects': ['resources/missing']}
        with self.assertRaisesRegex(ValueError, 'not bundled'):
            augment(self.public, self.private, [], self.profile)

    def test_traversal_and_foreign_resource_owners_fail(self):
        entry = self.profile['plugins'][0]
        entry['resources'] = [{'owner': 'unknown', 'source': 'a', 'target': 'b'}]
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            augment(self.public, self.private, [], self.profile)
        entry['resources'] = [{'owner': 'toolkit', 'source': '../outside', 'target': 'resource'}]
        with self.assertRaises(ValueError):
            augment(self.public, self.private, [], self.profile)

    def test_runtime_install_stages_sources_outside_immutable_payload(self):
        root = self.base / 'plugin'
        project = root / 'resources/core'
        project.mkdir(parents=True)
        (project / 'pyproject.toml').write_text('[project]\nname="fixture"\n', encoding='utf-8')
        destination = self.base / 'environment'
        component = {'kind': 'python', 'projects': ['resources/core'], 'requirements': [], 'module': 'fixture.server'}
        executable = Path(runtime.plan(root, component, destination)['executable'])

        def fake_run(command, **kwargs):
            if command[1:3] == ['-m', 'venv']:
                executable.parent.mkdir(parents=True, exist_ok=True)
                executable.write_bytes(b'')
        with patch.object(runtime.subprocess, 'run', side_effect=fake_run) as run, \
                patch.object(runtime, 'matches_at', return_value=True):
            result = runtime.install(root, 'example', component, destination)
        install = run.call_args_list[1].args[0]
        self.assertIn(str(destination / '.sources/0'), install)
        self.assertNotIn(str(project), install)
        self.assertEqual(len(list(project.iterdir())), 1)
        self.assertEqual(json.loads((destination / '.toolbox-runtime.json').read_text())['status'], 'installed-not-client-verified')
        self.assertEqual(runtime.registered_python('example'), executable)
        self.assertEqual(result['registry'], str(self.base / 'runtimes.json'))
        with self.assertRaisesRegex(ValueError, 'existing environments'):
            runtime.install(root, 'example', component, destination)

    def test_prepare_reuses_matching_registered_runtime_without_install(self):
        runtime.record_runtime('example', sys.executable)
        component = {'kind': 'python', 'module': 'fixture', 'versions': {'fixture': '1'}}
        with patch.object(runtime, 'probe_versions', return_value=({'fixture': '1'}, True)), \
                patch.object(runtime, 'install') as install:
            result = runtime.prepare(self.public, ['example', 'example'], {'example': component}, self.base / 'envs')
        self.assertEqual([row['status'] for row in result['results']], ['reused'])
        install.assert_not_called()

    def test_prepare_preserves_old_environment_and_continues_after_failure(self):
        runtime.record_runtime('first', sys.executable)
        before = (self.base / 'runtimes.json').read_bytes()
        component = {'kind': 'python', 'module': 'fixture', 'versions': {'fixture': '2'}}
        def fake_install(root, name, spec, destination, python):
            if name == 'first':
                raise OSError('fixture install failed')
            return {'component': name, 'status': 'installed-not-client-verified'}
        with patch.object(runtime, 'matches_at', side_effect=[False, True]), \
                patch.object(runtime, 'install', side_effect=fake_install) as install:
            result = runtime.prepare(self.public, ['first', 'second'], {'first': component, 'second': component}, self.base / 'envs')
        self.assertFalse(result['success'])
        self.assertEqual([row['status'] for row in result['results']], ['failed', 'installed-not-client-verified'])
        self.assertEqual(install.call_count, 2)
        self.assertEqual((self.base / 'runtimes.json').read_bytes(), before)

    def test_prepare_rejects_unknown_selection_before_install(self):
        with patch.object(runtime, 'install') as install, self.assertRaises(ValueError):
            runtime.prepare(self.public, ['valid', 'missing'], {'valid': {}}, self.base / 'envs')
        install.assert_not_called()

    def test_prepare_reuses_node_prefix_and_preserves_incomplete_destination(self):
        component = {'kind': 'node', 'versions': {'fixture': '1'}}
        destination = self.base / 'envs'
        fingerprint = runtime.hashlib.sha256(json.dumps(component, sort_keys=True).encode()).hexdigest()[:12]
        old = destination / ('node-' + fingerprint)
        old.mkdir(parents=True)
        good = destination / ('node-' + fingerprint + '-1') / 'node_modules/fixture'
        good.mkdir(parents=True)
        (good / 'package.json').write_text('{"version":"1"}')
        with patch.object(runtime, 'install') as install:
            result = runtime.prepare(self.public, ['node'], {'node': component}, destination)
        self.assertTrue(result['success'])
        self.assertEqual(result['results'][0]['status'], 'reused')
        self.assertTrue(old.is_dir())
        install.assert_not_called()

    def test_registry_preserves_other_components_and_rejects_missing_runtime(self):
        runtime.record_runtime('first', sys.executable)
        runtime.record_runtime('second', sys.executable)
        self.assertEqual(set(json.loads((self.base / 'runtimes.json').read_text())), {'first', 'second'})
        with self.assertRaisesRegex(ValueError, 'existing absolute'):
            runtime.record_runtime('third', 'python')
        (self.base / 'runtimes.json').write_text(json.dumps({'gone': {'python': str(self.base / 'missing.exe')}}))
        with self.assertRaisesRegex(ValueError, 'register it again'):
            runtime.registered_python('gone')
        self.assertIsNone(runtime.registered_python('unregistered'))

    def test_delegation_uses_registered_runtime_once(self):
        other = self.base / 'python.exe'
        other.write_bytes(b'')
        runtime.record_runtime('example', other)
        with patch.object(runtime.subprocess, 'run') as run:
            run.return_value.returncode = 0
            self.assertEqual(runtime.delegate('example', ['serve', '--component', 'example']), 0)
        command = run.call_args.args[0]
        self.assertEqual(command[0], str(other))
        self.assertEqual(command[-3:], ['serve', '--component', 'example'])
        self.assertEqual(run.call_args.kwargs['env'][runtime.DELEGATED], '1')
        with patch.dict(runtime.os.environ, {runtime.DELEGATED: '1'}):
            self.assertIsNone(runtime.delegate('example', ['serve']))
        runtime.record_runtime('self', sys.executable)
        self.assertIsNone(runtime.delegate('self', ['serve']))
        self.assertIsNone(runtime.delegate('unregistered', ['serve']))

    def test_runtime_destination_cannot_modify_plugin(self):
        root = self.base / 'plugin'
        root.mkdir()
        with self.assertRaisesRegex(ValueError, 'immutable'):
            runtime.plan(root, {'kind': 'python'}, root / 'venv')

    def test_serve_refuses_relative_or_missing_roots_before_module_execution(self):
        component = {'module': 'synthetic.never_run', 'read_root': True}
        for root in ('relative', str(self.base / 'missing')):
            with self.subTest(root=root), self.assertRaisesRegex(ValueError, 'absolute read root'):
                runtime.serve(self.base, component, root)

    def test_empty_read_root_starts_status_only_server_without_file_access(self):
        component = {'module': 'synthetic.never_run', 'read_root': True, 'write_root': True}
        with patch.object(runtime, 'serve_unconfigured') as unconfigured, \
                patch.object(runtime.runpy, 'run_module') as module:
            for root in (None, ''):
                runtime.serve(self.base, component, root, name='example')
        self.assertEqual(unconfigured.call_count, 2)
        unconfigured.assert_called_with('example')
        module.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'read root before a write root'):
            runtime.serve(self.base, component, '', str(self.base))

    def test_valid_roots_are_passed_to_the_server(self):
        component = {'module': 'synthetic.server', 'read_root': True, 'write_root': True}
        with patch.object(runtime.runpy, 'run_module') as module, \
                patch.object(runtime.sys, 'argv', []):
            runtime.serve(self.base, component, str(self.base), str(self.base))
            self.assertEqual(runtime.sys.argv, ['synthetic.server', '--read-root', str(self.base), '--write-root', str(self.base)])
        module.assert_called_once()

    def test_serve_rejects_unapproved_write_and_read_capability(self):
        component = {'module': 'synthetic.never_run'}
        with self.assertRaisesRegex(ValueError, 'write root'):
            runtime.serve(self.base, component, write_root=str(self.base))
        with self.assertRaisesRegex(ValueError, 'does not accept a read root'):
            runtime.serve(self.base, component, str(self.base))

    def test_serve_reports_unprepared_runtime(self):
        component = {'module': 'synthetic.never_run', 'versions': {'synthetic-missing-distribution': '1.0'}}
        with self.assertRaisesRegex(ValueError, 'register the declared runtime'):
            runtime.serve(self.base, component, name='example')

    def test_main_passes_server_arguments_after_separator(self):
        root = self.base / 'plugin'
        (root / 'runtime').mkdir(parents=True)
        (root / 'runtime/components.json').write_text(json.dumps({'example': {'kind': 'python', 'module': 'synthetic'}}))
        with patch.object(runtime, '__file__', str(root / 'runtime/setup.py')), \
                patch.object(runtime, 'serve') as serve:
            self.assertEqual(runtime.main(['serve', '--component', 'example', '--', '--tool', 'rtk']), 0)
        self.assertEqual(serve.call_args.args[4], ['--tool', 'rtk'])
        with patch.object(runtime, '__file__', str(root / 'runtime/setup.py')):
            self.assertEqual(runtime.main(['doctor', '--component', 'example', '--', '--tool']), 2)

    def test_codex_resolves_only_declared_local_settings_without_a_shell(self):
        root = self.base / 'connector'
        (root / '.claude-plugin').mkdir(parents=True)
        (root / '.claude-plugin/plugin.json').write_text(json.dumps({'userConfig': {
            'python': {'type': 'file', 'required': True}, 'read_root': {'type': 'directory', 'required': True}}}), encoding='utf-8')
        (root / '.mcp.json').write_text(json.dumps({'mcpServers': {'example': {
            'command': '${user_config.python}', 'args': ['${CLAUDE_PLUGIN_ROOT}/runtime/server.py', '${user_config.read_root}']}}}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Set example.python'):
            codex.resolve(root, 'example', {})
        executable, args, env = codex.resolve(root, 'example', {'example': {'python': sys.executable, 'read_root': str(self.base)}})
        self.assertEqual(args, [str(root) + '/runtime/server.py', str(self.base)])
        self.assertEqual(env, {})
        (root / 'runtime').mkdir()
        (root / 'runtime/codex-args.json').write_text(json.dumps({'example': ['--context', 'codex']}), encoding='utf-8')
        _, overridden, _ = codex.resolve(root, 'example', {'example': {'python': sys.executable, 'read_root': str(self.base)}})
        self.assertEqual(overridden, ['--context', 'codex'])
        with self.assertRaisesRegex(ValueError, 'unknown field'):
            codex.resolve(root, 'example', {'example': {'shell': 'unexpected'}})

    def test_codex_resolves_only_fields_the_connector_references(self):
        root = self.base / 'shared'
        (root / '.claude-plugin').mkdir(parents=True)
        (root / '.claude-plugin/plugin.json').write_text(json.dumps({'userConfig': {
            'first_executable': {'type': 'file', 'required': True}, 'second_executable': {'type': 'file', 'required': True}}}), encoding='utf-8')
        (root / '.mcp.json').write_text(json.dumps({'mcpServers': {
            'first': {'command': '${user_config.first_executable}', 'args': []},
            'second': {'command': '${user_config.second_executable}', 'args': []}}}), encoding='utf-8')
        executable, args, _ = codex.resolve(root, 'first', {'first': {'first_executable': sys.executable}})
        self.assertEqual((executable, args), (sys.executable, []))
        with self.assertRaisesRegex(ValueError, 'Set second.second_executable'):
            codex.resolve(root, 'second', {'second': {'first_executable': sys.executable}})

    def test_codex_optional_executable_and_root_defaults(self):
        root = self.base / 'optional'
        (root / '.claude-plugin').mkdir(parents=True)
        (root / '.claude-plugin/plugin.json').write_text(json.dumps({'userConfig': {
            'python_executable': {'type': 'string', 'required': False, 'default': 'python'},
            'read_root': {'type': 'directory', 'required': False, 'default': ''}}}), encoding='utf-8')
        (root / '.mcp.json').write_text(json.dumps({'mcpServers': {'example': {
            'command': '${user_config.python_executable}', 'args': ['--read-root', '${user_config.read_root}']}}}), encoding='utf-8')
        with patch.object(codex.shutil, 'which', side_effect=lambda name: sys.executable if name == 'python' else None):
            for settings in ({}, {'example': {'python_executable': ''}}, {'example': {'python_executable': '', 'read_root': ''}}):
                with self.subTest(settings=settings):
                    executable, args, _ = codex.resolve(root, 'example', settings)
                    self.assertEqual((executable, args), (sys.executable, ['--read-root', '']))
            with self.assertRaisesRegex(ValueError, 'command name on PATH'):
                codex.resolve(root, 'example', {'example': {'python_executable': 'bin/python'}})
            with self.assertRaisesRegex(ValueError, 'existing absolute directory'):
                codex.resolve(root, 'example', {'example': {'read_root': str(self.base / 'missing')}})
        with patch.object(codex.shutil, 'which', return_value=None), self.assertRaisesRegex(ValueError, 'native Python'):
            codex.resolve(root, 'example', {'example': {'python_executable': 'missing-python'}})

    def test_workflow_integrations_do_not_create_unselected_owners(self):
        self.profile['plugins'][0]['requires_plugin'] = True
        packages = []
        rows, files = augment(self.public, self.private, packages, self.profile)
        self.assertEqual((packages, rows, files), ([], {}, {}))

    def test_reference_relocation_preserves_bytes_and_provenance(self):
        root = self.public / 'reference.md'
        root.write_bytes(b'[Skill](../../skills/example/SKILL.md)\n')
        entry = self.profile['plugins'][0]
        entry['resources'] = [{'owner': 'toolkit', 'source': 'reference.md', 'target': 'agents/references/entry.md'}]
        entry['relocations'] = [{'source': 'agents/references', 'target': 'references/agent-entries'}]
        packages = []
        augment(self.public, self.private, packages, self.profile)
        files = packages[0]['files']
        self.assertNotIn('agents/references/entry.md', files)
        self.assertEqual(files['references/agent-entries/entry.md'], root.read_bytes())


if __name__ == '__main__':
    unittest.main()
