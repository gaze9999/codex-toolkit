"""Preview and synchronize installed owned Plugins through native Codex commands."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

if __package__:
    from .plugin_catalog import NAME, load_catalog, payload, source_files
else:
    from plugin_catalog import NAME, load_catalog, payload, source_files

ROOT = Path(__file__).resolve().parents[2]
MARKET = 'codex-toolkit'


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def settings(home):
    path = home / 'config.toml'
    if path.is_symlink():
        raise ValueError('設定檔使用連結, 請先核對擁有者')
    return tomllib.loads(path.read_text(encoding='utf-8-sig'))


def owned_state(value):
    return {'marketplace': value.get('marketplaces', {}).get(MARKET),
            'plugins': {key: row for key, row in value.get('plugins', {}).items() if key.endswith('@' + MARKET)}}


def tree(root):
    return {relative: path.read_bytes() for path, relative in source_files(root, '.')}


def plan(root, home, selected=None):
    value = settings(home)
    state = owned_state(value)
    market = state['marketplace']
    if not isinstance(market, dict) or market.get('source_type') != 'local':
        raise ValueError('此入口只更新既有本機 codex-toolkit Marketplace')
    previous = Path(market['source']).resolve()
    if not previous.is_dir():
        raise ValueError('目前 Marketplace 來源不存在, 請先修復來源')
    index = json.loads((previous / '.agents/plugins/marketplace.json').read_text(encoding='utf-8'))
    if index.get('name') != MARKET:
        raise ValueError('目前來源不是 codex-toolkit Marketplace')
    entries = {row['name']: row for row in index['plugins']}
    bundles = {b['manifest']['name']: b for b in load_catalog(root)}
    names = sorted(key.removesuffix('@' + MARKET) for key in state['plugins'])
    if any(not NAME.fullmatch(name) for name in names):
        raise ValueError('Plugin 名稱不合法')
    if not names:
        raise ValueError('沒有已註冊 Plugin, 初次安裝請使用原生 Plugin 入口')
    # No guessed toggle or custom-config rewrite: preserve what the native CLI can restore.
    if any(row != {'enabled': True} for row in state['plugins'].values()):
        raise ValueError('含停用或自訂 Plugin 設定, 此版本僅預覽外另需原生介面處理, 不自動替換 Marketplace')
    selected_names = {'codex-' + item for item in selected} if selected else set(names)
    if not selected_names <= set(names):
        raise ValueError('只可選擇已註冊 Plugin, 不藉同步新增安裝')
    packages, changes, old_trees = {}, [], {}
    for name in names:
        entry = entries.get(name)
        if not entry or entry.get('source', {}).get('source') != 'local':
            raise ValueError('來源必須可本機復原: ' + name)
        folder = (previous / entry['source']['path']).resolve()
        if not folder.is_relative_to(previous):
            raise ValueError('舊 Plugin 超出 Marketplace 範圍')
        old = tree(folder)
        old_trees[name] = (folder, old)
        if name in selected_names:
            bundle = bundles.get(name)
            if not bundle or bundle['status'] != 'ready':
                raise ValueError('Plugin 未具備可同步來源: ' + name)
            files, provenance = payload(root, bundle)
            different = sorted(key for key in set(files) | (set(old) - {'source-manifest.json'}) if files.get(key) != old.get(key))
            changes.append({'name': name, 'version': provenance['version'], 'changed_files': different})
            packages[name] = (files, provenance)
        else:
            packages[name] = ({key: raw for key, raw in old.items() if key != 'source-manifest.json'},
                              json.loads(old['source-manifest.json']) if 'source-manifest.json' in old else None)
    return {'state': state, 'previous': previous, 'packages': packages, 'old_trees': old_trees,
            'selected': selected_names, 'changes': changes, 'root': root, 'home': home}


def recheck(planned):
    if owned_state(settings(planned['home'])) != planned['state']:
        raise ValueError('Marketplace 或 Plugin 設定已改變, 請重新預覽')
    for name, (folder, before) in planned['old_trees'].items():
        if tree(folder) != before:
            raise ValueError('原安裝來源已改變: ' + name)
        if name in planned['selected']:
            bundle = next(b for b in load_catalog(planned['root']) if b['manifest']['name'] == name)
            if payload(planned['root'], bundle) != planned['packages'][name]:
                raise ValueError('來源已改變, 請重新預覽: ' + name)


def snapshot(planned):
    recheck(planned)
    home = planned['home']
    base = home / 'plugin-sources' / MARKET
    if any(path.is_symlink() for path in (base, base.parent, home)):
        raise ValueError('快照位置使用連結, 請先核對範圍')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = base / ('local-sync-' + stamp)
    output.mkdir(parents=True)
    try:
        revision_result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=planned['root'], capture_output=True, text=True)
        revision = revision_result.stdout.strip() if revision_result.returncode == 0 else None
    except FileNotFoundError:
        revision = None
    index = {'name': MARKET, 'interface': {'displayName': 'Codex Toolkit'}, 'plugins': []}
    for name, (files, provenance) in planned['packages'].items():
        for relative, raw in files.items():
            target = output / 'plugins' / name / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        if provenance:
            metadata = {**provenance, 'source_revision': revision, 'source_state': 'working-tree'} if name in planned['selected'] else provenance
            (output / 'plugins' / name / 'source-manifest.json').write_bytes(encode(metadata))
        index['plugins'].append({'name': name, 'source': {'source': 'local', 'path': './plugins/' + name},
                                 'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_USE'}, 'category': 'Productivity'})
    target = output / '.agents/plugins/marketplace.json'
    target.parent.mkdir(parents=True)
    target.write_bytes(encode(index))
    for name, (files, _) in planned['packages'].items():
        if {k: v for k, v in tree(output / 'plugins' / name).items() if k != 'source-manifest.json'} != files:
            raise ValueError('快照內容核對失敗: ' + name)
    return output


def native(cli, home, *args):
    result = subprocess.run([cli, 'plugin', *args], env={**os.environ, 'CODEX_HOME': str(home)},
                            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    if result.returncode:
        raise ValueError(f'原生 Plugin 操作失敗 ({result.returncode}): ' + (result.stderr or result.stdout).strip()[-1500:])
    return json.loads(result.stdout) if result.stdout.strip().startswith('{') else None


def verify(planned, source, packages, cli):
    actual = owned_state(settings(planned['home']))
    if actual['plugins'] != planned['state']['plugins'] or not Path(actual['marketplace']['source']).samefile(source):
        raise ValueError('Marketplace 或啟用狀態核對失敗')
    rows = native(cli, planned['home'], 'list', '--marketplace', MARKET, '--json')['installed']
    by_name = {row['name']: row for row in rows}
    if set(by_name) != set(packages):
        raise ValueError('原生安裝項目核對失敗')
    for name, (files, _) in packages.items():
        cache = planned['home'] / 'plugins/cache' / MARKET / name / by_name[name]['version']
        actual_files = {k: v for k, v in tree(cache).items() if k != 'source-manifest.json'}
        if actual_files != files or not by_name[name]['enabled']:
            raise ValueError('原生 Plugin 快取內容核對失敗: ' + name)


def switch(planned, source, cli):
    native(cli, planned['home'], 'marketplace', 'remove', MARKET)
    native(cli, planned['home'], 'marketplace', 'add', str(source), '--json')
    for name in planned['packages']:
        native(cli, planned['home'], 'add', name + '@' + MARKET, '--json')


def apply(planned, cli):
    recheck(planned)
    output = snapshot(planned)
    recheck(planned)
    config = planned['home'] / 'config.toml'
    backup = planned['home'] / 'backups/codex-toolkit' / output.name / 'config.toml'
    backup.parent.mkdir(parents=True)
    shutil.copy2(config, backup)
    if os.name != 'nt':
        backup.chmod(0o600)
    untouched = settings(planned['home'])
    try:
        switch(planned, output, cli)
        verify(planned, output, planned['packages'], cli)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # Restore only the owned registration through native commands, never overwrite config/cache.
        try:
            current = owned_state(settings(planned['home']))
            if current['marketplace']:
                native(cli, planned['home'], 'marketplace', 'remove', MARKET)
            native(cli, planned['home'], 'marketplace', 'add', str(planned['previous']), '--json')
            for name in planned['packages']:
                native(cli, planned['home'], 'add', name + '@' + MARKET, '--json')
            old = {name: ({k: v for k, v in files.items() if k != 'source-manifest.json'}, None)
                   for name, (_, files) in planned['old_trees'].items()}
            verify(planned, planned['previous'], old, cli)
        except (OSError, ValueError, subprocess.SubprocessError) as rollback:
            raise ValueError(f'{error}; 復原未完成: {rollback}; 備份: {backup}') from error
        raise ValueError(f'{error}; 原生復原已核對, 備份: {backup}') from error
    after = settings(planned['home'])
    for value in (untouched, after):
        value.get('marketplaces', {}).pop(MARKET, None)
        value['plugins'] = {k: v for k, v in value.get('plugins', {}).items() if not k.endswith('@' + MARKET)}
    return {'status': 'applied', 'source': str(output), 'backup': str(backup),
            'verified_plugins': len(planned['packages']), 'other_settings_unchanged': untouched == after,
            'reload_verified': False, 'changes': planned['changes']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-home', type=Path)
    parser.add_argument('--plugin', action='append', help='Registered catalog ID; repeat for selected scope')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--yes', action='store_true')
    args = parser.parse_args(argv)
    if args.yes and not args.apply:
        parser.error('--yes requires --apply')
    home = (args.codex_home or Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')).expanduser().resolve()
    if home == Path(home.anchor) or home == ROOT or home.is_relative_to(ROOT):
        parser.error('Use a dedicated Codex home outside the source repository')
    try:
        planned = plan(ROOT, home, args.plugin)
        preview = {'status': 'preview', 'changes': planned['changes'], 'preserved_plugins': len(planned['packages']),
                   'native_reinstall_scope': sorted(planned['packages']), 'source_state': 'working-tree', 'reload_verified': False}
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        if not args.apply or not any(row['changed_files'] for row in planned['changes']):
            return 0
        if not args.yes and (not sys.stdin.isatty() or input('套用此預覽範圍並保存備份? [y/N] ').lower() not in {'y', 'yes'}):
            return 0
        cli = shutil.which('codex')
        if not cli:
            raise ValueError('找不到原生 Codex CLI, 保留預覽')
        print(json.dumps(apply(planned, cli), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
