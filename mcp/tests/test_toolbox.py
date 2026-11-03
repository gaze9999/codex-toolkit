"""Verify audience isolation, source ownership and non-installing toolbox preparation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('toolbox', ROOT / 'tooling/toolbox.py')
toolbox = importlib.util.module_from_spec(spec)
spec.loader.exec_module(toolbox)


class ToolboxTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.public = self.base / 'public'
        self.private = self.base / 'private'
        self.mock_identity = patch.object(toolbox, 'identity', return_value={'revision': 'a' * 40, 'state': 'working-tree'})
        self.mock_identity.start()
        self.addCleanup(self.mock_identity.stop)
        self.write(self.public, 'VERSION', '1.0.0\n')
        self.write(self.public, 'LICENSE', 'Public fixture license\n')
        self.write(self.public, 'mcp/tools/development-tools.requirements.json', {'tools': {}})
        self.write(self.public, 'mcp/mcp_servers/presets/baseline.json', {'servers': []})
        self.write(self.public, 'skills/grouped/SKILL.md', self.skill('grouped'))
        self.write(self.public, 'skills/independent/SKILL.md', self.skill('independent'))
        self.write(self.public, 'plugins/workflow/plugin.json', self.manifest('codex-workflow'))
        self.write(self.public, 'plugins/catalog.json', {'schema_version': 1, 'bundles': [
            {'id': 'workflow', 'batch': '1', 'status': 'ready', 'skills': ['grouped'], 'resources': [], 'runtime_profiles': []}]})
        self.write(self.private, 'private-skills/private-flow/SKILL.md', self.skill('private-flow', 'PRIVATE_FIXTURE_SENTINEL'))
        self.write(self.private, 'profiles/personal-toolbox.json', {
            'schema_version': 1, 'name': 'personal-tools', 'version': '0.1.0', 'owner': 'Example',
            'repository': 'https://example.test/owner/private', 'selection_source': 'profiles/selection.json',
            'connector_inventory': 'profiles/inventory.json', 'private_bundles': [],
            'private_skills': ['private-skills/private-flow']})
        self.write(self.private, 'profiles/selection.json', {
            'toolkit_revision': 'a' * 40, 'skills': ['independent'], 'plugins': ['codex-workflow']})
        self.write(self.private, 'profiles/inventory.json', {'captured_at': 'historical', 'plugins': [
            {'id': 'vendor@original', 'owner': 'upstream/client'}], 'mcp_servers': [
                {'name': 'example', 'owner': 'external', 'transport': 'remote', 'enabled': True,
                 'credential_env_names': ['EXAMPLE_TOKEN'], 'env': {'EXAMPLE_TOKEN': 'SECRET_SENTINEL'},
                 'url': 'https://private.invalid/SECRET_SENTINEL', 'headers': {'Authorization': 'SECRET_SENTINEL'}}]})

    def write(self, root, relative, value):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(toolbox.encoded(value) if isinstance(value, dict) else value.encode('utf-8'))

    def skill(self, name, description='Example workflow'):
        return f'---\nname: {name}\ndescription: {description}\nmetadata:\n  version: "1.0.0"\n  author: "Example"\n---\n\n# Workflow\n'

    def manifest(self, name):
        return {'$schema': toolbox.SCHEMA, 'name': name, 'version': '1.0.0', 'description': 'Example workflow',
                'repository': 'https://example.test/owner/toolkit', 'author': {'name': 'Example'}}

    def test_public_output_excludes_private_content_and_identity(self):
        catalog, files = toolbox.assemble(self.public, self.private, 'public')
        self.assertEqual({s['name'] for s in catalog['categories']['skills']}, {'grouped', 'independent'})
        self.assertEqual(set(catalog['source']), {'toolkit'})
        self.assertFalse(any(b'PRIVATE_FIXTURE_SENTINEL' in raw or b'SECRET_SENTINEL' in raw for raw in files.values()))
        self.assertEqual(catalog['categories']['connectors'], [])
        self.assertNotIn('publication', catalog)
        self.assertNotIn('publication-plan.json', files)

    def test_publication_plan_keeps_release_unstaged(self):
        catalog, files = toolbox.assemble(self.public, self.private, 'personal')
        plan = catalog['publication']
        self.assertEqual(plan['strategy'], 'private-git-marketplace')
        self.assertFalse(plan['generator_remote_actions'])
        self.assertFalse(plan['release']['eligible'])
        self.assertFalse(plan['release']['checks']['sources_committed'])
        self.assertEqual(plan['release']['archive_policy'], 'deferred')
        self.assertEqual(json.loads(files['publication-plan.json']), plan)

    def test_publication_candidate_cannot_contain_credentials(self):
        catalog, _ = toolbox.assemble(self.public, self.private, 'personal')
        for candidate in ('https://token@github.com/owner/repo', 'https://github.com/owner/repo?token=secret',
                          'https://github.com/owner/repo/releases/download/v1/package.zip'):
            with self.subTest(candidate=candidate), self.assertRaisesRegex(ValueError, 'credential-free'):
                toolbox.publication_plan(catalog, {'candidate_repository': candidate})

    def test_committed_source_does_not_claim_client_acceptance(self):
        catalog, _ = toolbox.assemble(self.public, self.private, 'personal')
        catalog['source'] = {'toolkit': {'revision': 'a' * 40, 'state': 'committed'}}
        plan = toolbox.publication_plan(catalog)
        self.assertTrue(plan['release']['checks']['sources_committed'])
        self.assertFalse(plan['release']['checks']['platform_acceptance'])
        self.assertFalse(plan['release']['eligible'])

    def test_verified_private_repository_still_requires_release_gates(self):
        catalog, _ = toolbox.assemble(self.public, self.private, 'personal')
        plan = toolbox.publication_plan(catalog, {'candidate_repository': 'https://github.com/example/toolbox',
                                                'repository_state': 'verified-private', 'repository_id': 123})
        self.assertTrue(plan['release']['checks']['repository_verified'])
        self.assertFalse(plan['release']['eligible'])

    def test_verified_repository_requires_observed_identity(self):
        catalog, _ = toolbox.assemble(self.public, self.private, 'personal')
        with self.assertRaisesRegex(ValueError, 'observed repository ID'):
            toolbox.publication_plan(catalog, {'repository_state': 'verified-private'})

    def test_deferred_archive_policy_cannot_publish_implicitly(self):
        catalog, _ = toolbox.assemble(self.public, self.private, 'personal')
        with self.assertRaisesRegex(ValueError, 'deferred archives'):
            toolbox.publication_plan(catalog, {'archive_policy': 'automatic'})

    def test_personal_output_keeps_unique_skill_owners(self):
        catalog, files = toolbox.assemble(self.public, self.private, 'personal')
        skills = catalog['categories']['skills']
        self.assertEqual(len({s['name'] for s in skills}), 3)
        self.assertEqual(next(s for s in skills if s['name'] == 'private-flow')['visibility'], 'private')
        self.assertIn('plugins/skill-private-flow/.claude-plugin/plugin.json', files)
        self.assertIn('plugins/codex-workflow/plugin.json', files)

    def test_private_output_contains_only_private_workflows(self):
        catalog, _ = toolbox.assemble(self.public, self.private, 'private')
        self.assertEqual([s['name'] for s in catalog['categories']['skills']], ['private-flow'])

    def test_connector_export_drops_raw_configuration(self):
        catalog, files = toolbox.assemble(self.public, self.private, 'personal')
        connector = catalog['categories']['connectors'][0]
        self.assertIsNone(connector['loaded'])
        self.assertIsNone(connector['authenticated'])
        self.assertEqual(connector['credential_env_names'], ['EXAMPLE_TOKEN'])
        self.assertFalse(any(b'SECRET_SENTINEL' in raw for raw in files.values()))
        self.assertIn(b'recorded-inventory', files['connectors/catalog.json'])

    def test_credential_values_cannot_be_variable_names(self):
        with self.assertRaisesRegex(ValueError, 'variable names'):
            toolbox.connector_catalog({'mcp_servers': [{'name': 'sample', 'credential_env_names': ['Bearer secret']}]})

    def test_duplicate_connector_names_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unique'):
            toolbox.connector_catalog({'mcp_servers': [{'name': 'sample'}, {'name': 'sample'}]})

    def test_selection_revision_must_match(self):
        self.write(self.private, 'profiles/selection.json', {'toolkit_revision': 'b' * 40, 'skills': [], 'plugins': []})
        with self.assertRaisesRegex(ValueError, 'HEAD differs'):
            toolbox.assemble(self.public, self.private, 'personal')

    def test_private_version_must_be_valid_before_output(self):
        profile = json.loads((self.private / 'profiles/personal-toolbox.json').read_text())
        profile['version'] = 'latest'
        self.write(self.private, 'profiles/personal-toolbox.json', profile)
        with self.assertRaisesRegex(ValueError, 'version must be semantic'):
            toolbox.assemble(self.public, self.private, 'personal')

    def test_unknown_selected_skill_is_not_silently_dropped(self):
        self.write(self.private, 'profiles/selection.json', {'toolkit_revision': 'a' * 40, 'skills': ['missing'], 'plugins': []})
        with self.assertRaisesRegex(ValueError, 'missing'):
            toolbox.assemble(self.public, self.private, 'personal')

    def test_traversal_is_rejected(self):
        profile = json.loads((self.private / 'profiles/personal-toolbox.json').read_text())
        profile['private_skills'] = ['../outside']
        self.write(self.private, 'profiles/personal-toolbox.json', profile)
        with self.assertRaises(ValueError):
            toolbox.assemble(self.public, self.private, 'personal')

    def test_standalone_reuses_packager_link_validation(self):
        self.write(self.public, 'skills/independent/SKILL.md', self.skill('independent') + '\n[Missing](references/missing.md)\n')
        with self.assertRaisesRegex(ValueError, 'Unbundled reference'):
            toolbox.assemble(self.public)

    def test_generated_manifest_cannot_replace_existing_source_manifest(self):
        bundle = toolbox.load_catalog(self.public)[0]
        with self.assertRaisesRegex(ValueError, 'cannot be combined'):
            toolbox.payload(self.public, bundle, generated_manifest=True)

    def test_prepare_has_no_archives_and_verify_detects_tampering(self):
        output = self.base / 'prepared'
        result = toolbox.prepare(self.public, self.private, 'personal', output)
        self.assertEqual(result['counts'], {'skills': 3, 'connectors': 1, 'plugins': 3})
        self.assertFalse(list(output.rglob('*.zip')))
        self.assertEqual(toolbox.verify(output)['status'], 'verified')
        (output / 'README.md').write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            toolbox.verify(output)

    def test_existing_output_is_preserved(self):
        output = self.base / 'existing'
        output.mkdir()
        marker = output / 'keep.txt'
        marker.write_text('keep')
        with self.assertRaisesRegex(ValueError, 'new unlinked'):
            toolbox.prepare(self.public, self.private, 'personal', output)
        self.assertEqual(marker.read_text(), 'keep')

    def test_unexpected_output_is_rejected(self):
        output = self.base / 'prepared'
        toolbox.prepare(self.public, self.private, 'public', output)
        (output / 'extra.txt').write_text('extra')
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            toolbox.verify(output)

    def test_git_checkout_metadata_is_separate_from_payload(self):
        output = self.base / 'checkout'
        toolbox.prepare(self.public, self.private, 'public', output)
        self.write(output, '.git/config', 'Git metadata fixture\n')
        self.assertEqual(toolbox.verify(output)['status'], 'verified')
        self.assertIn(b'-text', (output / '.gitattributes').read_bytes())
        self.assertIn(b'cr-at-eol', (output / '.gitattributes').read_bytes())


if __name__ == '__main__':
    unittest.main()
