"""Prepare source-backed Skills, connector catalogs and Plugins without installing or archiving."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mcp/scripts'))
sys.path.insert(0, str(ROOT / 'tooling'))
from audit_skills import FRONTMATTER_RE, METADATA_RE, scalar
from plugin_catalog import NAME, SCHEMA, VERSION, claude_manifest, load_catalog, marketplace_interface, payload, safe_source
from toolbox_integrations import augment

PRODUCER = 'codex-toolkit.toolbox.v1'
ADAPTER_VERSION = '0.3.1'


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(root, name):
    return json.loads(safe_source(root, name).read_text(encoding='utf-8'))


def identity(root):
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True, timeout=30).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=root, text=True, timeout=30)
    return {'revision': revision, 'state': 'working-tree' if dirty else 'committed'}


def skill_meta(raw):
    match = FRONTMATTER_RE.match(raw.decode('utf-8').replace('\r\n', '\n'))
    if not match:
        raise ValueError('Skill frontmatter is required')
    block = match.group(1)
    metadata = METADATA_RE.search(block)
    name, description = scalar(block, 'name'), scalar(block, 'description')
    version = scalar(metadata.group(1), 'version') if metadata else None
    if not name or not NAME.fullmatch(name) or not description or not version or not VERSION.fullmatch(version):
        raise ValueError('Skill needs a portable name, description and version: ' + str(name))
    return {'name': name, 'description': description, 'version': version}


def standalone(root, relative, repository):
    meta = skill_meta(safe_source(root, relative + '/SKILL.md').read_bytes())
    manifest = {'$schema': SCHEMA, 'name': 'skill-' + meta['name'], 'version': meta['version'],
                'description': meta['description'], 'author': {'name': repository.rsplit('/', 2)[-2]},
                'repository': repository}
    bundle = {'skills': [], 'resources': [{'source': relative, 'target': 'skills/' + meta['name']}],
              'runtime_profiles': [], 'manifest': manifest}
    return bundle


def connector_catalog(inventory):
    rows, names = [], set()
    for source in inventory['mcp_servers']:
        name = source.get('name')
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in names:
            raise ValueError('Connector names must be unique portable identifiers')
        names.add(name)
        variables = source.get('credential_env_names', [])
        if not isinstance(variables, list) or any(not isinstance(n, str) or not re.fullmatch(r'[A-Z][A-Z0-9_]*', n) for n in variables):
            raise ValueError('Connector credentials must be variable names only')
        rows.append({'name': name, 'owner': source.get('owner'), 'transport': source.get('transport'),
                     'observed_enabled': source.get('enabled'), 'credential_env_names': variables,
                     'evidence': 'recorded-inventory', 'loaded': None, 'authenticated': None,
                     'setup': 'Resolve the supported client, runtime, roots and login on the target device.',
                     'claude_chat': 'remote-connector-setup-required' if source.get('transport') in {'remote', 'http', 'sse'} else 'local-runtime-unavailable-in-chat'})
    return {'captured_at': inventory.get('captured_at'), 'captured_timezone': inventory.get('captured_timezone'),
            'verification_scope': 'Recorded selections only; no live client or account checks.', 'items': rows}


def publication_plan(catalog, settings=None):
    settings = settings or {}
    candidate = settings.get('candidate_repository')
    if candidate is not None and (not isinstance(candidate, str) or not re.fullmatch(
            r'https://github[.]com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', candidate)):
        raise ValueError('Publication candidate must be a credential-free GitHub repository URL')
    strategy = settings.get('strategy', 'private-git-marketplace')
    if strategy != 'private-git-marketplace' or settings.get('archive_policy', 'deferred') != 'deferred':
        raise ValueError('Only a private Git marketplace with deferred archives is supported')
    state = settings.get('repository_state', 'candidate-unverified')
    if state not in {'candidate-unverified', 'verified-private'}:
        raise ValueError('Unknown distribution repository state')
    verified = state == 'verified-private'
    if verified and (not candidate or not isinstance(settings.get('repository_id'), int) or settings['repository_id'] <= 0):
        raise ValueError('Verified private repository needs its URL and observed repository ID')
    committed = all(row.get('state') == 'committed' for row in catalog['source'].values())
    accepted = bool(catalog['platform_acceptance']) and all(
        value == 'passed' for value in catalog['platform_acceptance'].values())
    return {'schema_version': 1, 'strategy': strategy, 'audience': catalog['audience'],
            'candidate_repository': candidate, 'repository_visibility': 'private',
            'repository_state': state, 'repository_id': settings.get('repository_id') if verified else None,
            'generator_remote_actions': False,
            'marketplace': {'manifest': '.claude-plugin/marketplace.json',
                            'gui_route': 'Customize > Plugins > Add > Add marketplace',
                            'source_access': 'Grant the client access to the generated distribution repository.'},
            'maintenance': 'Edit canonical owners in the maintenance workspace; regenerate the distribution.',
            'release': {'role': 'optional-version-checkpoint-and-download', 'mode': 'manual-draft',
                        'proposed_tag': 'v' + catalog['version'], 'archive_policy': 'deferred',
                        'eligible': False, 'state': 'not-staged',
                        'checks': {'sources_committed': committed, 'platform_acceptance': accepted,
                                   'repository_verified': verified, 'tag_target_verified': False,
                                   'assets_verified': False}}}


def assemble(toolkit, private=None, audience='public'):
    if audience not in {'public', 'private', 'personal'}:
        raise ValueError('Invalid audience')
    public = audience in {'public', 'personal'}
    personal = audience in {'private', 'personal'}
    toolkit = toolkit.resolve()
    packages, owners, skills, source_inputs = [], {}, [], []
    selected_skills = selected_plugins = None
    config = None
    if personal:
        if private is None:
            raise ValueError('Private and personal output requires an explicit private root')
        private = private.resolve()
        config = read_json(private, 'profiles/personal-toolbox.json')
        if config.get('schema_version') != 1 or not NAME.fullmatch(config.get('name', '')):
            raise ValueError('Invalid private toolbox profile')
        if not isinstance(config.get('version'), str) or not VERSION.fullmatch(config['version']):
            raise ValueError('Private toolbox version must be semantic')
        if not isinstance(config.get('owner'), str) or not config['owner'].strip():
            raise ValueError('Private toolbox owner is required')
        selection = read_json(private, config['selection_source'])
        selected_skills, selected_plugins = set(selection['skills']), set(selection['plugins'])
        selected_skills.update(config.get('toolbox_skills', []))
        reviewed_revision = config.get('toolkit_revision', selection['toolkit_revision'])
        if not isinstance(reviewed_revision, str) or not re.fullmatch(r'[0-9a-f]{40}', reviewed_revision):
            raise ValueError('Toolbox source requires a full reviewed Toolkit revision')
        if reviewed_revision != identity(toolkit)['revision']:
            raise ValueError('Toolkit HEAD differs from the reviewed private selection')
        for relative in ('profiles/personal-toolbox.json', config['selection_source'], config['connector_inventory']):
            source_inputs.append({'owner': 'private', 'path': relative,
                                  'sha256': digest(safe_source(private, relative).read_bytes())})

    def add(root, bundle, visibility, owner):
        manifest = bundle['manifest']
        name = manifest['name']
        if not NAME.fullmatch(name) or name in owners:
            raise ValueError('Plugin names must be unique')
        if manifest.get('$schema') != SCHEMA or not VERSION.fullmatch(manifest.get('version', '')):
            raise ValueError('Plugin manifest needs the portable schema and a semantic version')
        owners[name] = owner
        files, provenance = payload(root, bundle, generated_manifest=not bundle.get('manifest_source'))
        members = []
        for path, raw in files.items():
            if path.startswith('skills/') and path.endswith('/SKILL.md'):
                meta = skill_meta(raw)
                if meta['name'] in {row['name'] for row in skills}:
                    raise ValueError('A Skill can have only one enabled package owner')
                members.append(meta['name'])
                skills.append({**meta, 'visibility': visibility, 'owner': owner, 'plugin': name,
                               'path': 'plugins/' + name + '/' + path, 'sha256': digest(raw)})
        if not members:
            raise ValueError('A workflow Plugin needs at least one Skill')
        adapter = claude_manifest(manifest, files)
        if visibility == 'public':
            adapter['license'] = 'MIT'
        files['.claude-plugin/plugin.json'] = encoded(adapter)
        packages.append({'name': name, 'version': manifest['version'], 'description': manifest['description'],
                         'visibility': visibility, 'owner': owner, 'skills': members,
                         'runtime_profiles': bundle.get('runtime_profiles', []), 'files': files,
                         'provenance': provenance['files']})

    if public:
        grouped = set()
        bundles = load_catalog(toolkit)
        repository = bundles[0]['manifest']['repository']
        for bundle in bundles:
            if bundle['status'] != 'ready' or selected_plugins is not None and bundle['manifest']['name'] not in selected_plugins:
                continue
            grouped.update(bundle['skills'])
            add(toolkit, bundle, 'public', 'toolkit')
        available = {p.parent.name for p in safe_source(toolkit, 'skills').glob('*/SKILL.md')}
        for name in sorted(available - grouped):
            if selected_skills is not None and name not in selected_skills:
                continue
            add(toolkit, standalone(toolkit, 'skills/' + name, repository), 'public', 'toolkit')
        if selected_skills is not None and selected_skills - {s['name'] for s in skills}:
            raise ValueError('Selected standalone Skills are missing')
        if selected_plugins is not None and selected_plugins - set(owners):
            raise ValueError('Selected Plugins are missing')
    if personal:
        for relative in config['private_bundles']:
            bundle = read_json(private, relative)
            bundle['manifest'] = read_json(private, bundle['manifest_source'])
            add(private, bundle, 'private', 'private')
        for relative in config['private_skills']:
            add(private, standalone(private, relative, config['repository']), 'private', 'private')

    integration_rows, integration_files = {}, {}
    if personal and config.get('integration_source'):
        integration_path = config['integration_source']
        integration_rows, integration_files = augment(toolkit, private, packages, read_json(private, integration_path))
        source_inputs.append({'owner': 'private', 'path': integration_path,
                              'sha256': digest(safe_source(private, integration_path).read_bytes())})
    files, mappings = {}, {}

    def put(name, raw, owner='generated', source=None):
        safe_source(toolkit, name)
        if name.casefold() in {p.casefold() for p in files}:
            raise ValueError('Duplicate toolbox output path')
        files[name] = raw
        mappings[name] = {'owner': owner, 'source': source, 'sha256': digest(raw)}

    for item in packages:
        for name, raw in item['files'].items():
            origin = item['provenance'].get(name, {}).get('source')
            owner = item['provenance'].get(name, {}).get('owner', item['owner'])
            put('plugins/' + item['name'] + '/' + name, raw, owner, origin)
    for name, raw in integration_files.items():
        put(name, raw)
    inputs = {'toolkit': identity(toolkit)}
    if personal:
        inputs['private'] = identity(private)
    connector_data = connector_catalog(read_json(private, config['connector_inventory'])) if personal else {'items': [], 'verification_scope': 'Add selected runtime connectors in a private profile.'}
    for row in connector_data['items']:
        row['integration'] = integration_rows.get(row['name'], {'state': 'not-bundled', 'loaded': None, 'authenticated': None})
    recorded_names = {row['name'] for row in connector_data['items']}
    for name, row in integration_rows.items():
        if name not in recorded_names:
            connector_data['items'].append({'name': name, 'owner': 'selected-integration', 'transport': row['transport'],
                'observed_enabled': None, 'credential_env_names': [], 'evidence': 'reviewed-integration-profile',
                'loaded': None, 'authenticated': None, 'integration': row})
    connector_data['integration_scope'] = 'Prepared declarations and resources; target-client loading and authentication remain separate.'
    plugin_rows = [{key: value for key, value in item.items() if key not in {'files', 'provenance'}} for item in packages]
    catalog = {'schema_version': 1, 'name': config['name'] if personal else 'codex-toolkit',
               'version': config['version'] if personal else safe_source(toolkit, 'VERSION').read_text(encoding='utf-8').strip(),
               'adapter_version': ADAPTER_VERSION, 'audience': audience, 'source': inputs,
               'categories': {'skills': skills, 'connectors': connector_data['items'], 'plugins': plugin_rows},
               'platform_acceptance': {'codex': 'pending-client-installation', 'claude_code': 'pending-client-installation',
                                       'claude_chat': 'pending-upload-and-connector-setup', 'cowork': 'pending-client-installation'}}
    if personal:
        catalog['publication'] = publication_plan(catalog, config.get('publication'))
        put('publication-plan.json', encoded(catalog['publication']))
        instructions = config.get('publication', {}).get('instructions_source')
        if instructions:
            put('AGENTS.md', safe_source(private, instructions).read_bytes(), 'private', instructions)
    put('.gitattributes', b'* -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n')
    put('skills/catalog.json', encoded({'items': skills}))
    put('connectors/catalog.json', encoded(connector_data))
    put('plugins/catalog.json', encoded({'items': plugin_rows}))
    skill_rows = '\n'.join(f"| [{row['name']}](../{row['path']}) | {row['version']} | {row['visibility']} | `{row['plugin']}` |" for row in skills)
    put('skills/README.md', ('# Skills\n\n每項保留正式來源內容, 由單一外掛提供, 依任務讀取所需的參照與腳本\n\n| Skill | 版本 | 範圍 | 外掛來源 |\n| --- | --- | --- | --- |\n' + skill_rows + '\n').encode('utf-8'))
    connector_rows = '\n'.join(f"| `{row['name']}` | {row['owner']} | {row['transport']} | {row['observed_enabled']} |" for row in connector_data['items'])
    connector_help = '# 連接器\n\n盤點值保留原觀察日期, 實際宣告與準備步驟另列如下, 載入與登入需在目的用戶端確認\n本機 stdio 工具需要目的裝置的執行環境與資料權限, Claude 網頁對話使用可連線的遠端服務\n用戶端內建工具由原用戶端供應, 外部服務沿其官方連線入口\n\n| 名稱 | owner | 傳輸類型 | 盤點啟用值 |\n| --- | --- | --- | --- |\n' + connector_rows + '\n'
    if integration_rows:
        connector_help += '\n| 已準備宣告 | 外掛與設定步驟 |\n| --- | --- |\n'
        connector_help += '\n'.join(f"| `{key}` | [{row['plugin']}](../{row['setup']}) |" for key, row in integration_rows.items()) + '\n'
    put('connectors/README.md', connector_help.encode('utf-8'))
    plugin_rows_md = '\n'.join(f"| [{row['name']}]({row['name']}/) | {row['version']} | {row['visibility']} | {len(row['skills'])} |" for row in packages)
    put('plugins/README.md', ('# 外掛程式\n\n每個資料夾保留 Codex manifest 與 Claude manifest, Skills 與資源共用同一份產生結果\nClaude 網頁版 / Desktop 每次上傳一個外掛, 本輪保留資料夾格式, 後續上傳時再依原生介面準備套件\n各工作流程所需的工具、帳戶、原生功能與常駐指示依目的端分別設定及驗收\n\n| 外掛 | 版本 | 範圍 | Skills |\n| --- | --- | --- | --- |\n' + plugin_rows_md + '\n').encode('utf-8'))
    if personal:
        recorded = read_json(private, config['connector_inventory'])
        external = [{'id': row['id'], 'owner': row['owner'], 'evidence': 'recorded-inventory', 'loaded': None}
                    for row in recorded['plugins'] if row.get('owner') not in {'codex-toolkit', 'private-authorized-source'}]
        put('plugins/external-sources.json', encoded({'items': external, 'policy': 'Install from the original provider.'}))
    selected = client_packages(packages, config.get('client_exclusions', {}) if personal else {})
    catalog['client_plugins'] = {client: [p['name'] for p in rows] for client, rows in selected.items()}
    marketplace = {'name': catalog['name'], 'owner': {'name': config['owner'] if personal else 'Codex Toolkit'},
                   'description': 'Source-backed Skills, connectors and Plugins', 'version': catalog['version'],
                   'plugins': [{'name': p['name'], 'source': './plugins/' + p['name'], 'description': p['description']} for p in selected['claude']]}
    put('.claude-plugin/marketplace.json', encoded(marketplace))
    interface = marketplace_interface(catalog['version'], config.get('display_name', catalog['name']) if personal else 'Codex Toolkit',
                                      config.get('display_icon', '🧰') if personal else '🧰')
    put('.agents/plugins/marketplace.json', encoded({'name': catalog['name'], 'interface': interface, 'plugins': [
        {'name': p['name'], 'source': {'source': 'local', 'path': './plugins/' + p['name']},
         'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_USE'}, 'category': 'Productivity'} for p in selected['codex']]}))
    put('catalog.json', encoded(catalog))
    readme = f'''# 個人工具整合包

此目錄依 Skills、連接器、外掛程式三類整理來源, audience 為 `{audience}`

| 類別 | 數量 | 入口 |
| --- | --- | --- |
| Skills | {len(skills)} | [Skills 目錄](skills/README.md) |
| 連接器 | {len(connector_data['items'])} | [連接器目錄](connectors/README.md) |
| 外掛程式 | {len(packages)} | [外掛目錄](plugins/README.md) |

Skills 的實際內容在各外掛的 skills/ 下, 每個 Skill 對應單一外掛 owner
Claude Code 可將此目錄加入本機市集, 再選擇外掛, Codex 使用其原生本機市集入口
Claude 網頁版 / Desktop 的上傳單位為每個 plugins/ 下的獨立外掛資料夾, 本輪只準備目錄
連接器清單保留記錄中的選擇, 執行環境、資料 roots、登入與實際工具呼叫需在目的端確認
個人工作規範由私人工作規範外掛提供按需參照, 常駐指示仍需透過各平台支援的設定入口套用

維護時修改正式來源, 再執行 prepare 產生新目錄, 使用 verify 檢查原目錄
source-manifest.json 記錄來源提交、檔案映射與 SHA-256, 平台驗收狀態見 catalog.json
'''
    if integration_rows:
        readme += '\n## 執行環境與雙平台設定\n\n[設定指南](SETUP.md) 包含 Codex / Claude 操作、必要條件與驗收方式\n各外掛的 mcp.json 提供 Codex 原生宣告, .mcp.json 提供 Claude 宣告, 工具程式與版本來源共用\n個人整合外掛的版本由私人 profile 管理, source_version 保留原元件版本, 安裝後依需求選擇單一來源\n'
    if personal:
        readme += '''
## 私人散布方式

日常安裝與更新使用專用私人 Git 市集, 維護來源保留在原 owner
Claude 的 GitHub App 取得散布用 repo 權限後, 從自訂 > 外掛程式 > Add > Add marketplace 加入
Release 保留為選用的版本快照與下載入口, ZIP 仍暫緩
repo、來源與平台檢查狀態見 [發布計畫](publication-plan.json), 產生器只準備檔案, Git 與 Release 由發布操作處理
'''
        if catalog['publication']['repository_state'] == 'verified-private':
            target = catalog['publication']['candidate_repository']
            readme += f'\n私人市集網址: [{target}]({target})\n'
    put('README.md', readme.encode('utf-8'))
    manifest = {'schema_version': 1, 'producer': PRODUCER, 'adapter_version': ADAPTER_VERSION,
                'audience': audience, 'source': inputs, 'inputs': source_inputs, 'files': mappings}
    manifest['generator_hashes'] = {name: digest((ROOT / name).read_bytes()) for name in
        ('tooling/toolbox.py', 'tooling/toolbox_integrations.py', 'tooling/toolbox_runtime.py',
         'tooling/toolbox_codex.py', 'mcp/scripts/plugin_catalog.py', 'mcp/scripts/audit_skills.py')}
    files['source-manifest.json'] = encoded(manifest)
    return catalog, files


def client_packages(packages, exclusions):
    if not isinstance(exclusions, dict) or set(exclusions) - {'codex', 'claude'}:
        raise ValueError('Client exclusions must name codex or claude')
    names = {p['name'] for p in packages}
    result = {}
    for client in ('codex', 'claude'):
        omitted = exclusions.get(client, [])
        if (not isinstance(omitted, list) or any(not isinstance(name, str) for name in omitted)
                or len(omitted) != len(set(omitted)) or set(omitted) - names):
            raise ValueError('Client exclusions need unique existing plugin names: ' + client)
        result[client] = [p for p in packages if p['name'] not in omitted]
    return result


def verify(output):
    output = output.absolute()
    manifest = read_json(output, 'source-manifest.json')
    if manifest.get('producer') != PRODUCER or not isinstance(manifest.get('files'), dict):
        raise ValueError('Unknown toolbox producer')
    for name, row in manifest['files'].items():
        if name == 'source-manifest.json' or digest(safe_source(output, name).read_bytes()) != row['sha256']:
            raise ValueError('Toolbox file hash mismatch: ' + name)
    entries = [p for p in output.rglob('*') if p.relative_to(output).parts[0] != '.git']
    if any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in entries):
        raise ValueError('Linked toolbox content is not permitted')
    actual = {p.relative_to(output).as_posix() for p in entries if p.is_file()}
    if actual != set(manifest['files']) | {'source-manifest.json'}:
        raise ValueError('Unexpected or missing toolbox files')
    return {'status': 'verified', 'files': len(actual), 'audience': manifest['audience']}


def prepare(toolkit, private, audience, output):
    output = output.absolute()
    if output.exists() or any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in (output, *output.parents)):
        raise ValueError('Use a new unlinked output directory')
    catalog, files = assemble(toolkit, private, audience)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.toolbox-', dir=output.parent) as temporary:
        staged = Path(temporary) / 'payload'
        staged.mkdir()
        for name, raw in files.items():
            path = safe_source(staged, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        result = verify(staged)
        if assemble(toolkit, private, audience)[1] != files:
            raise ValueError('Source changed during preparation')
        staged.rename(output)
    return {**result, 'status': 'prepared', 'output': str(output),
            'counts': {key: len(value) for key, value in catalog['categories'].items()}}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'publication-plan', 'prepare', 'verify'))
    parser.add_argument('--toolkit-root', type=Path, default=ROOT)
    parser.add_argument('--private-root', type=Path)
    parser.add_argument('--audience', choices=('public', 'private', 'personal'), default='public')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action in {'plan', 'publication-plan'}:
            catalog, _ = assemble(args.toolkit_root, args.private_root, args.audience)
            if args.action == 'publication-plan' and 'publication' not in catalog:
                parser.error('publication-plan requires a private or personal audience')
            result = catalog['publication'] if args.action == 'publication-plan' else catalog
        else:
            if args.output is None:
                parser.error(args.action + ' requires --output')
            result = verify(args.output) if args.action == 'verify' else prepare(args.toolkit_root, args.private_root, args.audience, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
