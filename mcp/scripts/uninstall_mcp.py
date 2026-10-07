#!/usr/bin/env python3
"""Preview or remove one standalone MCP registration and, optionally, its server package."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

if __package__:
    from .bootstrap_mcp import absolute, atomic, digest, plugin_endpoint
    from .check_development_tools import ROOT, npm_prefix, tool_spec
    from .install_development_tool import install_command
    from .installer_language import InstallerUi
    from .plan_guard import require_same_plan
else:
    from bootstrap_mcp import absolute, atomic, digest, plugin_endpoint
    from check_development_tools import ROOT, npm_prefix, tool_spec
    from install_development_tool import install_command
    from installer_language import InstallerUi
    from plan_guard import require_same_plan


BASELINE = {
    'jev': {'module': 'codex_jev_mcp.mcp_server'},
    'local_documents': {'module': 'mcp_servers.local_documents.document_server'},
    'workspace_inspection': {'module': 'workspace_inspection_mcp.server'},
    'openaiDeveloperDocs': {'url': 'https://developers.openai.com/mcp'},
}


class RemovalError(ValueError):
    """A user-actionable message that contains no config values or credentials."""


def selected_spec(tool, manifest):
    if tool in BASELINE:
        return {'mcp': {'name': tool, **BASELINE[tool]}}
    spec = tool_spec(tool, manifest, 'mcp')
    if not spec.get('mcp'):
        raise RemovalError('This tool uses an app/connector setup, not a standalone MCP registration')
    return spec


def matches(server, spec):
    if not isinstance(server, dict):
        return False
    args = server.get('args', [])
    if not isinstance(args, list):
        return False
    if 'url' in spec:
        url = server.get('url', '')
        return isinstance(url, str) and url.rstrip('/') in {spec['url'].rstrip('/'), spec['url'].rstrip('/') + '/oauth'}
    if 'module' in spec:
        return '-m' in args and args[args.index('-m')+1:args.index('-m')+2] == [spec['module']] and (
            'tool' not in spec or '--tool' in args and args[args.index('--tool')+1:args.index('--tool')+2] == [spec['tool']])
    if 'entry_suffix' in spec:
        entry = any(isinstance(arg, str) and arg.replace('\\', '/').endswith(spec['entry_suffix'])
                    and (not spec.get('entry_directory') or '/'+spec['entry_directory']+'/' in arg.replace('\\','/')) for arg in args)
        suffix = spec.get('config_suffix')
        return entry and (not suffix or '--config' in args and any(isinstance(arg, str) and arg.replace('\\', '/').endswith(suffix) for arg in args[args.index('--config')+1:args.index('--config')+2]))
    return Path(server.get('command', '')).name in spec.get('native_command', [])


def advance_string(line, state):
    """Track TOML strings so a fake table header inside a multiline value stays literal."""
    index = 0
    while index < len(line):
        if state:
            if line.startswith(state, index):
                index += len(state)
                state = None
            elif state.startswith('"') and line[index] == '\\':
                index += 2
            else:
                index += 1
        elif line[index] == '#':
            break
        elif line.startswith(('"""', "'''"), index):
            state = line[index:index+3]
            index += 3
        elif line[index] in "\"'":
            quote = line[index]
            index += 1
            while index < len(line):
                if line[index] == quote:
                    index += 1
                    break
                index += 2 if quote == '"' and line[index] == '\\' else 1
        else:
            index += 1
    return state


def without_registration(text, name):
    before = tomllib.loads(text)
    if name not in before.get('mcp_servers', {}):
        return text
    headers, offset, state = [], 0, None
    for line in text.splitlines(keepends=True):
        header = re.fullmatch(r'\s*(\[(?!\[).*\])\s*(?:#.*)?', line.rstrip('\r\n')) if state is None else None
        if header:
            value = tomllib.loads(header.group(1) + '\n')
            keys = []
            while isinstance(value, dict) and len(value) == 1:
                key, value = next(iter(value.items()))
                keys.append(key)
            headers.append((offset, tuple(keys)))
        state = advance_string(line, state)
        offset += len(line)
    removed = [(start, headers[i+1][0] if i+1 < len(headers) else len(text)) for i, (start, keys) in enumerate(headers) if keys[:2] == ('mcp_servers', name)]
    if not removed:
        raise RemovalError('Selected MCP uses inline/dotted registration; preserve it and edit that entry explicitly')
    after = text
    for start, end in reversed(removed):
        after = after[:start] + after[end:]
    expected = deepcopy(before)
    expected['mcp_servers'].pop(name)
    parsed = tomllib.loads(after)
    for value in (expected, parsed):
        if not value.get('mcp_servers'):
            value.pop('mcp_servers', None)
    if parsed != expected:
        raise RemovalError('Unrelated TOML settings would change; nothing was removed')
    return after


def package_plan(tool, spec, server, servers, selected, prefix):
    command = Path(server.get('command', ''))
    if spec.get('python_package') or spec.get('mcp', {}).get('module') == 'development_tool_mcp.server':
        root = command.parent.parent
        marker = root/'.codex-setup-managed'
        if not command.is_absolute() or not command.is_file() or not (root/'pyvenv.cfg').is_file() or not marker.is_file() or marker.read_text(encoding='utf-8').strip() != tool or root.is_symlink():
            raise RemovalError('Package removal requires the selected setup-managed Python environment; registration-only removal remains available')
        if any(name != selected and Path(other.get('command', '')).parent.parent.resolve() == root.resolve() for name, other in servers.items()):
            raise RemovalError('Another MCP shares this Python runtime; keep its packages')
        package = spec.get('python_package', 'codex-development-tools-mcp').split('==')[0]
        python = root/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not python.is_file():
            raise RemovalError('Managed Python is missing; keep the environment for recovery')
        return {'kind': 'python', 'package': package, 'command': [str(python), '-I', '-m', 'pip', 'uninstall', '--yes', package]}
    suffix = spec.get('mcp', {}).get('entry_suffix')
    if suffix:
        entries = [Path(arg) for arg in server.get('args', []) if isinstance(arg, str) and arg.replace('\\', '/').endswith(suffix)]
        if len(entries) != 1 or not entries[0].is_absolute():
            raise RemovalError('Ambiguous installed Node package; keep it')
        entry = entries[0]
        module_root = next((parent for parent in entry.parents if parent.name == 'node_modules'), None)
        if module_root is None:
            raise RemovalError('Node package is outside the selected managed prefix')
        parts = entry.relative_to(module_root).parts
        package = '/'.join(parts[:2]) if parts[0].startswith('@') else parts[0]
        package_root = module_root/package
        if module_root.parent.resolve() != prefix.resolve() or package_root.is_symlink():
            raise RemovalError('Node package is outside the selected managed prefix')
        metadata = json.loads((package_root/'package.json').read_text(encoding='utf-8'))
        if metadata.get('name') != package:
            raise RemovalError('Node package identity mismatch')
        for name, other in servers.items():
            if name == selected:
                continue
            if any(isinstance(arg, str) and Path(arg).is_absolute() and Path(arg).resolve().is_relative_to(package_root.resolve()) for arg in other.get('args', [])):
                raise RemovalError('Another MCP uses ' + package + '; keep the shared package')
        return {'kind': 'npm', 'package': package, 'command': ['npm', 'uninstall', '--global', '--prefix', str(prefix), '--ignore-scripts', package]}
    return None


def plan(tool, manifest, config, *, server_name=None, remove_package=False, prefix=None):
    if config.is_symlink():
        raise RemovalError('Config is linked; inspect its owner before removing an entry')
    spec = selected_spec(tool, manifest)
    before = config.read_bytes() if config.exists() else None
    text = before.decode('utf-8-sig') if before is not None else ''
    parsed = tomllib.loads(text)
    servers = parsed.get('mcp_servers', {})
    candidates = [name for name, server in servers.items() if matches(server, spec['mcp'])]
    if spec.get('custom_endpoint') and spec['mcp']['name'] in servers:
        candidates = [spec['mcp']['name']]
    if server_name:
        if server_name not in candidates:
            raise RemovalError('Selected server does not match this tool; nothing was removed')
        candidates = [server_name]
    if len(candidates) > 1:
        raise RemovalError('Multiple matching registrations; select exactly one using --server')
    result = {'tool': tool, 'config': str(config), 'server': candidates[0] if candidates else None, 'config_sha256': digest(before) if before is not None else None,
              'package': None, 'preserved': ['other MCPs and built-in plugins', 'credentials and account authorization', 'shared runtimes/dependencies', 'rules, dictionaries, notebooks and user data'], '_before': before}
    if not candidates:
        result['status'] = 'not_registered'
        if spec['mcp'].get('url') and plugin_endpoint(config.parent, parsed, spec['mcp']['url']):
            result['manual_setup'] = 'This provider is client/plugin-managed; use its app settings to disconnect it'
        return result
    selected = candidates[0]
    if selected == 'node_repl':
        raise RemovalError('Client-managed MCP must remain unchanged')
    result['status'] = 'preview'
    result['_after'] = without_registration(text, selected).encode('utf-8')
    if remove_package:
        result['package'] = package_plan(tool, spec, servers[selected], servers, selected, prefix or npm_prefix())
        if result['package'] is None:
            result['manual_setup'] = 'No setup-managed server package selected, native apps and hosted accounts remain installed'
    return result


def apply_plan(planned, config, *, run=subprocess.run):
    if (config.read_bytes() if config.exists() else None) != planned['_before']:
        raise RemovalError('Config changed after preview; rerun before removal')
    if planned['status'] == 'not_registered':
        return {'status': 'not_registered', 'package_removed': False}
    # Unregister first so a package-manager failure cannot leave an enabled broken entry.
    backup = atomic(config, planned['_after'], planned['_before'])
    package = planned['package']
    if package:
        try:
            command = install_command(package['command'], os.environ.copy()) if package['kind'] == 'npm' else package['command']
            result = run(command, check=False, capture_output=True, timeout=180)
        except (ValueError, OSError, subprocess.SubprocessError):
            return {'status': 'registration_removed_package_failed', 'backup': backup, 'package_removed': False}
        if result.returncode:
            return {'status': 'registration_removed_package_failed', 'backup': backup, 'package_removed': False, 'exit_code': result.returncode}
    return {'status': 'removed', 'backup': backup, 'package_removed': bool(package), 'reload_required': True}


def main(argv=None):
    manifest = json.loads((ROOT/'mcp/tools/development-tools.requirements.json').read_text(encoding='utf-8'))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool', choices=sorted(set(manifest['tools']) | set(BASELINE)))
    parser.add_argument('--server', help='Select one exact name when this tool has multiple registrations')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--npm-prefix', type=Path)
    parser.add_argument('--remove-package', action='store_true', help='Also remove its unshared, managed server package, retaining dependencies and user data')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--expected-plan-sha256', help=argparse.SUPPRESS)
    parser.add_argument('--yes', action='store_true')
    parser.add_argument('--guided', action='store_true')
    parser.add_argument('--list', action='store_true', help='List recognized standalone registrations only')
    parser.add_argument('--lang', choices=['auto','zh-TW','en'], default='auto')
    args = parser.parse_args(argv)
    ui = InstallerUi(args.lang)
    try:
        location = args.config or Path(os.environ.get('CODEX_HOME') or Path.home()/'.codex')/'config.toml'
        if location.is_symlink():
            raise RemovalError('Config is linked; inspect its owner before removing an entry')
        config = absolute(location)
        if args.list or not args.tool and args.guided:
            choices = []
            for tool in sorted(set(manifest['tools']) | set(BASELINE)):
                try:
                    current = plan(tool, manifest, config)
                except ValueError:
                    continue
                if current['server']:
                    choices.append((tool, current['server']))
            if args.list:
                print(json.dumps({'registered': [{'tool': tool, 'server': name} for tool,name in choices]}, ensure_ascii=False, indent=2))
                return 0
            if not choices:
                print(ui.text('No standalone MCP registration found'))
                return 0
            for index, (tool, server) in enumerate(choices, 1):
                print(f'{index}. {tool} [{server}]')
            if not sys.stdin.isatty():
                raise RemovalError('Use --tool in a noninteractive terminal')
            answer = input(ui.text('MCP number to remove (Enter = cancel): ')).strip()
            if not answer:
                return 0
            if not answer.isdigit() or not 1 <= int(answer) <= len(choices):
                raise RemovalError('Select one number from the list')
            args.tool = choices[int(answer)-1][0]
        if not args.tool:
            parser.error('Select one --tool, --list or --guided')
        planned = plan(args.tool, manifest, config, server_name=args.server, remove_package=args.remove_package, prefix=absolute(args.npm_prefix) if args.npm_prefix else None)
        public = {key:value for key,value in planned.items() if not key.startswith('_')}
        print(json.dumps(public, ensure_ascii=False, indent=2))
        if planned['status'] == 'not_registered':
            return 0
        if not args.apply and not args.guided:
            return 0
        if not args.yes:
            if not sys.stdin.isatty():
                raise RemovalError('Review the preview, then use --apply --yes only for an authorized removal')
            if input(ui.text('Remove only this MCP and the listed package? [y/N] ')).strip().lower() not in {'y','yes'}:
                return 0
        elif not args.apply:
            return 0  # --yes never converts a preview into a write.
        require_same_plan(planned, args.expected_plan_sha256)
        result = apply_plan(planned, config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result['status'] == 'registration_removed_package_failed' else 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        # TOML/package errors may include private values, report a safe recovery action.
        print(json.dumps({'status':'error','reason':str(exc) if isinstance(exc, RemovalError) else 'Removal could not complete safely, inspect the selected config/package and rerun the preview'},ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
