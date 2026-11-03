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
        component = {'kind': 'python', 'projects': ['resources/core'], 'requirements': []}
        with patch.object(runtime.subprocess, 'run') as run:
            runtime.install(root, 'example', component, destination)
        install = run.call_args_list[1].args[0]
        self.assertIn(str(destination / '.sources/0'), install)
        self.assertNotIn(str(project), install)
        self.assertEqual(len(list(project.iterdir())), 1)
        self.assertEqual(json.loads((destination / '.toolbox-runtime.json').read_text())['status'], 'installed-not-client-verified')
        with self.assertRaisesRegex(ValueError, 'existing environments'):
            runtime.install(root, 'example', component, destination)

    def test_runtime_destination_cannot_modify_plugin(self):
        root = self.base / 'plugin'
        root.mkdir()
        with self.assertRaisesRegex(ValueError, 'immutable'):
            runtime.plan(root, {'kind': 'python'}, root / 'venv')

    def test_serve_refuses_missing_or_relative_roots_before_module_execution(self):
        component = {'module': 'synthetic.never_run', 'read_root': True}
        for root in (None, 'relative'):
            with self.subTest(root=root), self.assertRaisesRegex(ValueError, 'absolute read root'):
                runtime.serve(self.base, component, root)

    def test_serve_rejects_unapproved_write_capability(self):
        component = {'module': 'synthetic.never_run'}
        with self.assertRaisesRegex(ValueError, 'write root'):
            runtime.serve(self.base, component, write_root=str(self.base))

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
