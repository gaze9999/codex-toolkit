"""Check or regenerate the self-contained Git marketplace from canonical sources."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys

from plugin_catalog import load_catalog, payload, safe_source

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = 'codex-toolkit.marketplace.v1'

def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')

def marketplace_interface(root):
    path = safe_source(root, 'VERSION')
    if not path.is_file():
        return {'displayName': 'Codex Toolkit'}
    version = path.read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid Toolkit version')
    return {'displayName': f'🧰 Codex Toolkit v{version}'}


def prepare(root):
    files = {}
    index = {'name': 'codex-toolkit', 'interface': marketplace_interface(root), 'plugins': []}
    license_bytes = safe_source(root, 'LICENSE').read_bytes()
    for bundle in load_catalog(root):
        if bundle['status'] != 'ready':
            continue
        package, provenance = payload(root, bundle)
        name = provenance['plugin']
        prefix = 'marketplace/plugins/' + name + '/'
        package['LICENSE'] = license_bytes
        provenance['files']['LICENSE'] = {'source': 'LICENSE', 'sha256': hashlib.sha256(license_bytes).hexdigest()}
        provenance.update({'producer': PRODUCER, 'source_state': 'canonical-file-hashes', 'license': 'MIT'})
        package['source-manifest.json'] = encode(provenance)
        files.update({prefix + relative: raw for relative, raw in package.items()})
        index['plugins'].append({'name': name, 'source': {'source': 'local', 'path': './marketplace/plugins/' + name},
                                 'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_USE'}, 'category': 'Productivity'})
    if not index['plugins']:
        raise ValueError('No ready Plugin payloads')
    files['.agents/plugins/marketplace.json'] = encode(index)
    return files

def existing(root):
    index = safe_source(root, '.agents/plugins/marketplace.json')
    result = {'.agents/plugins/marketplace.json': index.read_bytes()} if index.is_file() else {}
    base = safe_source(root, 'marketplace/plugins')
    if base.is_dir():
        for path in base.rglob('*'):
            safe_source(root, path.relative_to(root).as_posix())
            if path.is_file():
                result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result

def owned_before(root, before):
    """Only overwrite intact generated packages, never arbitrary files or hand edits."""
    prefixes = {Path(name).parts[2] for name in before if name.startswith('marketplace/plugins/')}
    for plugin in prefixes:
        prefix = f'marketplace/plugins/{plugin}/'
        raw = before.get(prefix + 'source-manifest.json')
        if raw is None:
            raise ValueError('Unmanaged generated folder: ' + plugin)
        manifest = json.loads(raw)
        if manifest.get('producer') != PRODUCER:
            raise ValueError('Unowned payload: ' + plugin)
        expected = manifest['files']
        actual = {name[len(prefix):]: raw for name, raw in before.items() if name.startswith(prefix) and name != prefix + 'source-manifest.json'}
        if set(actual) != set(expected) or any(hashlib.sha256(raw).hexdigest() != expected[name]['sha256'] for name, raw in actual.items()):
            raise ValueError('Generated payload was edited; preserve and review it: ' + plugin)
    if '.agents/plugins/marketplace.json' in before:
        expected_index = {'name': 'codex-toolkit', 'interface': marketplace_interface(root), 'plugins': []}
        for plugin in sorted(prefixes):
            expected_index['plugins'].append({'name': plugin, 'source': {'source': 'local', 'path': './marketplace/plugins/' + plugin},
                                               'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_USE'}, 'category': 'Productivity'})
        actual_index = json.loads(before['.agents/plugins/marketplace.json'])
        if actual_index.get('interface') == {'displayName': 'Codex Toolkit'}:
            actual_index['interface'] = marketplace_interface(root)
        actual_entries = actual_index.get('plugins')
        if isinstance(actual_entries, list):
            actual_index['plugins'] = sorted(actual_entries, key=lambda row: row.get('name', ''))
        if actual_index != expected_index:
            raise ValueError('Marketplace catalog was edited or is unmanaged')

def synchronize(root, write=False):
    root = root.resolve()
    expected = prepare(root)
    before = existing(root)
    changed = sorted(name for name in expected.keys() | before.keys() if expected.get(name) != before.get(name))
    if not write:
        return {'status': 'pass' if not changed else 'stale', 'changed_files': changed}
    owned_before(root, before)
    if prepare(root) != expected or existing(root) != before:
        raise ValueError('Source or generated target changed after preview')
    for name in changed:
        target = safe_source(root, name)
        if name in expected:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(expected[name])
        else:
            target.unlink()
    # Only empty owned directories are pruned; no recursive delete.
    base = safe_source(root, 'marketplace/plugins')
    if base.exists():
        for path in sorted((path for path in base.rglob('*') if path.is_dir()), key=lambda path: len(path.parts), reverse=True):
            safe_source(root, path.relative_to(root).as_posix())
            if not any(path.iterdir()):
                path.rmdir()
    if existing(root) != expected:
        raise ValueError('Generated readback differs from canonical payloads')
    return {'status': 'written', 'changed_files': changed}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true', help='Verify existing generated files without writes')
    group.add_argument('--write', action='store_true', help='Regenerate only intact owned payloads')
    args = parser.parse_args(argv)
    try:
        result = synchronize(ROOT, write=args.write)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] in {'pass', 'written'} else 1
    except (OSError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
