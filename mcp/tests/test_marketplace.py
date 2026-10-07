from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'mcp/scripts'))
import prepare_marketplace as market

class MarketplaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'LICENSE').write_text('MIT fixture', encoding='utf-8')
        self.bundles = [{'status': 'ready', 'manifest': {'name': 'codex-example'}}]
        self.raw = b'original Skill'
        def payload(root, bundle):
            return ({'plugin.json': b'{"name":"codex-example"}', 'skills/example/SKILL.md': self.raw},
                    {'plugin': 'codex-example', 'version': '1.0.0', 'files': {
                        'plugin.json': {'source': 'plugins/example/plugin.json', 'sha256': market.hashlib.sha256(b'{"name":"codex-example"}').hexdigest()},
                        'skills/example/SKILL.md': {'source': 'skills/example/SKILL.md', 'sha256': market.hashlib.sha256(self.raw).hexdigest()}}})
        self.catalog = patch.object(market, 'load_catalog', side_effect=lambda root: self.bundles)
        self.payload = patch.object(market, 'payload', side_effect=payload)
        self.catalog.start(); self.payload.start()
        self.addCleanup(self.catalog.stop); self.addCleanup(self.payload.stop)

    def test_check_is_read_only_and_first_write_is_self_contained(self):
        self.assertEqual(market.synchronize(self.root)['status'], 'stale')
        self.assertFalse((self.root / 'marketplace').exists())
        self.assertEqual(market.synchronize(self.root, True)['status'], 'written')
        self.assertEqual(market.synchronize(self.root)['status'], 'pass')
        self.assertTrue((self.root / 'marketplace/plugins/codex-example/LICENSE').is_file())

    def test_filesystem_enumeration_order_does_not_change_manifest(self):
        expected = market.prepare(self.root)
        original = market.payload.side_effect
        def reversed_payload(root, bundle):
            files, provenance = original(root, bundle)
            provenance['files'] = dict(reversed(list(provenance['files'].items())))
            return dict(reversed(list(files.items()))), provenance
        with patch.object(market, 'payload', side_effect=reversed_payload):
            self.assertEqual(market.prepare(self.root), expected)

    def test_source_change_updates_intact_mirror(self):
        market.synchronize(self.root, True)
        self.raw = b'changed Skill'
        market.synchronize(self.root, True)
        self.assertEqual((self.root / 'marketplace/plugins/codex-example/skills/example/SKILL.md').read_bytes(), self.raw)

    def test_manual_payload_edit_is_not_overwritten(self):
        market.synchronize(self.root, True)
        target = self.root / 'marketplace/plugins/codex-example/skills/example/SKILL.md'
        target.write_bytes(b'local edit')
        with self.assertRaisesRegex(ValueError, 'edited'):
            market.synchronize(self.root, True)
        self.assertEqual(target.read_bytes(), b'local edit')

    def test_unmanaged_folder_is_preserved(self):
        path = self.root / 'marketplace/plugins/unmanaged/private.txt'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError, 'Unmanaged'):
            market.synchronize(self.root, True)
        self.assertTrue(path.exists())

    def test_source_change_during_preview_prevents_write(self):
        calls = 0
        original = market.prepare
        def changed(root):
            nonlocal calls
            calls += 1
            if calls == 2: self.raw = b'new concurrent source'
            return original(root)
        with patch.object(market, 'prepare', side_effect=changed), self.assertRaisesRegex(ValueError, 'changed'):
            market.synchronize(self.root, True)
        self.assertFalse((self.root / '.agents').exists())

    def test_removed_owned_payload_is_pruned_without_touching_unrelated_file(self):
        market.synchronize(self.root, True)
        unrelated = self.root / 'notes.txt'
        unrelated.write_text('keep', encoding='utf-8')
        self.bundles = [{'status': 'ready', 'manifest': {'name': 'codex-another'}}]
        with patch.object(market, 'payload', return_value=({'plugin.json': b'new'}, {'plugin': 'codex-another', 'version': '1.0.0', 'files': {'plugin.json': {'source': 'plugin.json', 'sha256': market.hashlib.sha256(b'new').hexdigest()}}})):
            market.synchronize(self.root, True)
        self.assertFalse((self.root / 'marketplace/plugins/codex-example').exists())
        self.assertEqual(unrelated.read_text(encoding='utf-8'), 'keep')

if __name__ == '__main__': unittest.main()
