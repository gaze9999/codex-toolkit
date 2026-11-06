"""Generate explicitly selected host adapters and portable runtime source mappings."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from plugin_catalog import NAME, SCHEMA, VERSION, source_files, safe_source, validate_components


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def augment(toolkit, private, packages, profile):
    if profile.get('schema_version') != 1:
        raise ValueError('Unsupported integration profile')
    indexed = {p['name']: p for p in packages}
    rows, components, generated = {}, {}, {}

    def put(item, target, raw, owner='generated', source=None):
        safe_source(toolkit, target)
        if target in item['files'] and item['files'][target] != raw:
            raise ValueError('Integration target already exists: ' + target)
        item['files'][target] = raw
        item['provenance'][target] = {'source': source, 'owner': owner,
                                      'sha256': hashlib.sha256(raw).hexdigest()}

    for entry in profile['plugins']:
        name, version = entry['name'], entry['version']
        if not NAME.fullmatch(name) or not VERSION.fullmatch(version):
            raise ValueError('Integration plugin needs a portable name and version')
        if entry.get('requires_plugin') and name not in indexed:
            continue
        if name not in indexed:
            manifest = {'name': name, 'version': version, 'description': entry['description'],
                        'author': {'name': profile['owner']}}
            item = {'name': name, 'version': version, 'description': entry['description'],
                    'visibility': 'private', 'owner': 'private', 'skills': [], 'runtime_profiles': [],
                    'files': {'plugin.json': encoded({'$schema': SCHEMA, **manifest}), '.claude-plugin/plugin.json': encoded(manifest)},
                    'provenance': {}}
            packages.append(item)
            indexed[name] = item
        item = indexed[name]
        item['source_version'] = item['version']
        item['version'] = version
        for target in ('plugin.json', '.claude-plugin/plugin.json'):
            manifest = json.loads(item['files'][target])
            manifest['version'] = version
            item['files'][target] = encoded(manifest)
            item['provenance'][target] = {'source': None}
        for mapping in entry.get('resources', []):
            owner = mapping['owner']
            if owner not in {'toolkit', 'private'}:
                raise ValueError('Unknown integration resource owner')
            root = toolkit if owner == 'toolkit' else private
            for path, relative in source_files(root, mapping['source']):
                target = mapping['target'] + ('/' + relative if path.is_file() and safe_source(root, mapping['source']).is_dir() else '')
                put(item, target, path.read_bytes(), owner, path.relative_to(root).as_posix())
        for mapping in entry.get('relocations', []):
            before, after = mapping['source'], mapping['target']
            safe_source(toolkit, before)
            safe_source(toolkit, after)
            if len(Path(before).parts) != len(Path(after).parts):
                raise ValueError('Reference relocation must preserve relative link depth')
            selected = [path for path in item['files'] if path.startswith(before + '/')]
            if not selected:
                raise ValueError('Relocated resource is missing')
            for path in selected:
                target = after + path[len(before):]
                put(item, target, item['files'][path], item['provenance'].get(path, {}).get('owner', item['owner']),
                    item['provenance'].get(path, {}).get('source'))
                del item['files'][path]
                item['provenance'].pop(path, None)
        servers, config, runtime, codex_args = {}, {}, dict(entry.get('tools', {})), {}
        for connector in entry.get('connectors', []):
            key = connector['name']
            if key in rows or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', key):
                raise ValueError('Integration connector names must be unique')
            server = connector['server']
            if set(server) - {'type', 'url', 'command', 'args', 'env', 'headers'}:
                raise ValueError('Unknown MCP server field')
            if 'url' in server:
                url = urlsplit(server['url'])
                if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
                    raise ValueError('Use a credential-free public HTTPS MCP endpoint')
                if server.get('headers', {}) not in ({}, {'X-Tavily-Access-Mode': 'keyless'}):
                    raise ValueError('Literal authentication headers are not portable')
            else:
                if not isinstance(server.get('command'), str) or not isinstance(server.get('args', []), list):
                    raise ValueError('Local MCP requires a command and argument list')
                if server.get('env') and any(not isinstance(v, str) or not v.startswith('${user_config.')
                                             and k not in {'MCP_TRANSPORT_TYPE', 'MCP_LOG_LEVEL', 'CHROME_DEVTOOLS_MCP_NO_UPDATE_CHECKS'}
                                             for k, v in server['env'].items()):
                    raise ValueError('Do not export credential values in local MCP settings')
            for field, value in connector.get('user_config', {}).items():
                if field in config and config[field] != value:
                    raise ValueError('Conflicting plugin configuration field')
                config[field] = value
            for reference in re.findall(r'\$\{user_config\.([A-Za-z0-9_]+)\}', json.dumps(server)):
                if reference not in config:
                    raise ValueError('Undeclared plugin configuration field: ' + reference)
            servers[key] = server
            if 'codex_args' in connector:
                arguments = connector['codex_args']
                if not isinstance(arguments, list) or any(not isinstance(arg, str) for arg in arguments):
                    raise ValueError('Codex arguments must be strings')
                for reference in re.findall(r'\$\{user_config\.([A-Za-z0-9_]+)\}', json.dumps(arguments)):
                    if reference not in config:
                        raise ValueError('Undeclared Codex configuration field')
                codex_args[key] = arguments
            if connector.get('runtime'):
                runtime[key] = connector['runtime']
            rows[key] = {'plugin': name, 'state': 'declaration-prepared',
                         'transport': 'http' if 'url' in server else 'stdio',
                         'runtime': 'bundled-source' if connector.get('runtime', {}).get('projects') else 'provider-package',
                         'setup': 'plugins/' + name + '/SETUP.md', 'loaded': None, 'authenticated': None}
        if servers:
            put(item, '.mcp.json', encoded({'mcpServers': servers}))
            portable = {}
            for key, server in servers.items():
                if 'url' in server:
                    portable[key] = {**server, 'type': 'streamable-http'}
                elif entry.get('native_stdio') and not config:
                    portable[key] = {**server, 'type': 'stdio'}
                else:
                    portable[key] = {'type': 'stdio', 'command': 'python',
                                     'args': ['runtime/codex.py', key], 'cwd': './'}
            put(item, 'mcp.json', encoded({'$schema': 'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json',
                                          'mcpServers': portable}))
        if config:
            manifest = json.loads(item['files']['.claude-plugin/plugin.json'])
            manifest['userConfig'] = config
            item['files']['.claude-plugin/plugin.json'] = encoded(manifest)
            example = {key: {field: value.get('default', '') for field, value in config.items()}
                       for key, server in servers.items() if 'command' in server}
            put(item, 'runtime/settings.example.json', encoded(example))
            put(item, 'runtime/codex.py', (toolkit / 'tooling/toolbox_codex.py').read_bytes(), 'toolkit', 'tooling/toolbox_codex.py')
            if codex_args:
                put(item, 'runtime/codex-args.json', encoded(codex_args))
        if runtime:
            for key, value in runtime.items():
                for path in value.get('projects', []):
                    safe_source(toolkit, path)
                    if not any(p.startswith(path + '/') for p in item['files']):
                        raise ValueError('Runtime project was not bundled: ' + path)
                for copy in value.get('copies', []):
                    safe_source(toolkit, copy['source'])
                    safe_source(toolkit, copy['target'])
                rooted = json.loads(json.dumps(value))
                rooted['projects'] = ['plugins/' + name + '/' + p for p in rooted.get('projects', [])]
                for copy in rooted.get('copies', []):
                    copy['source'] = 'plugins/' + name + '/' + copy['source']
                if key in components:
                    raise ValueError('Duplicate runtime component')
                components[key] = rooted
            put(item, 'runtime/setup.py', (toolkit / 'tooling/toolbox_runtime.py').read_bytes(), 'toolkit', 'tooling/toolbox_runtime.py')
            put(item, 'runtime/components.json', encoded(runtime))
        if entry.get('setup_source'):
            put(item, 'SETUP.md', safe_source(private, entry['setup_source']).read_bytes(), 'private', entry['setup_source'])
        else:
            body = '# ' + name + '\n\n' + entry['setup'] + '\n'
            if runtime:
                body += '\n在這個外掛資料夾執行, 選擇需要的元件, plan 使用套件外尚不存在的 RUNTIME_DIR, prepare 使用套件外的 RUNTIME_ROOT 並重用版本符合的環境:\n\n```sh\n'
                for key in runtime:
                    body += f'python runtime/setup.py plan --component {key} --destination RUNTIME_DIR\npython runtime/setup.py prepare --component {key} --destination RUNTIME_ROOT\n'
                body += '```\n\n將回傳的 Python 執行檔或 Node 安裝目錄填入 Claude Code 的外掛設定, 準備環境不會修改 Claude 帳戶或用戶端設定\n'
            body += '\n本機 MCP 由 Claude Code 或本機 Cowork 執行, chat 使用遠端連接器, 每項仍需在目的用戶端確認載入與代表操作\n'
            put(item, 'SETUP.md', body.encode('utf-8'))
        validate_components(item['files'], json.loads(item['files']['plugin.json']))
    if components:
        generated['runtime/setup.py'] = (toolkit / 'tooling/toolbox_runtime.py').read_bytes()
        generated['runtime/components.json'] = encoded(components)
    for row in profile.get('files', []):
        if row['owner'] not in {'private', 'toolkit'}:
            raise ValueError('Unknown supplemental file owner')
        root = private if row['owner'] == 'private' else toolkit
        safe_source(toolkit, row['target'])
        if row['target'] in generated:
            raise ValueError('Duplicate integration output')
        generated[row['target']] = safe_source(root, row['source']).read_bytes()
    return rows, generated
