"""Preview or restore explicitly selected portable setup choices through existing installers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
import uuid
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
SECTIONS = ('agents', 'skills', 'plugins', 'tools')


def names(value, label):
    if not isinstance(value, list) or any(not isinstance(item, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', item) for item in value):
        raise ValueError('Invalid names: ' + label)
    if len(value) != len(set(value)):
        raise ValueError('Duplicate names: ' + label)
    return value


def git_identity(source):
    if source.startswith('git@'):
        host, separator, path = source[4:].partition(':')
        if not separator:
            raise ValueError('Invalid Git marketplace source')
    else:
        parsed = urlsplit(source)
        if parsed.scheme not in ('https', 'ssh') or not parsed.hostname or parsed.password or (parsed.username and parsed.scheme == 'https') or parsed.query or parsed.fragment:
            raise ValueError('Use a credential-free HTTPS/SSH Git source')
        host, path = parsed.hostname, parsed.path
    if len(path.strip('/').removesuffix('.git').split('/')) != 2:
        raise ValueError('Use an explicit Git repository source')
    return (host + '/' + path.strip('/').removesuffix('.git')).lower()


def subset(values, requested, label):
    if requested is None:
        return values
    names(requested, label)
    if set(requested) - set(values):
        raise ValueError('Selection is outside the profile: ' + label)
    return [name for name in values if name in requested]


def plan(root, profile, home, sections, apply=False, replace_agents=False,
         selected_plugins=None, selected_skills=None, selected_tools=None, platform=None):
    root, profile, home = root.resolve(), profile.resolve(), home.expanduser().resolve()
    if home == Path(home.anchor) or home == root or home.is_relative_to(root):
        raise ValueError('Use a dedicated Codex home outside the toolkit checkout')
    value = json.loads(profile.read_text(encoding='utf-8'))
    allowed = {'schema_version', 'toolkit_revision', 'agents_source', 'skills', 'plugins', 'tools', 'manual', 'marketplace'}
    if set(value) - allowed or value.get('schema_version') != 1:
        raise ValueError('Unsupported profile fields or schema')
    revision = value.get('toolkit_revision', '')
    if not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Pin a reviewed full Git commit SHA in toolkit_revision')
    head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=normal'], capture_output=True, text=True, check=True).stdout.strip()
    if head != revision or dirty:
        raise ValueError('Toolkit checkout must be clean and match the pinned revision')
    selected = set(sections)
    if not selected <= set(SECTIONS):
        raise ValueError('Unknown restore section')
    skills = subset(names(value.get('skills', []), 'skills'), selected_skills, 'skills')
    plugins = subset(names(value.get('plugins', []), 'plugins'), selected_plugins, 'plugins')
    catalog = json.loads((root / 'plugins/catalog.json').read_text(encoding='utf-8'))
    bundles = {'codex-' + item['id']: item for item in catalog['bundles'] if item['status'] == 'ready'}
    if any(name not in bundles for name in plugins):
        raise ValueError('Unknown or unavailable Plugin')
    plugin_skills = {skill for name in plugins for skill in bundles[name]['skills']}
    if set(skills) & plugin_skills:
        raise ValueError('Profile enables duplicate direct/Plugin Skills')
    if any(not (root / 'skills' / name / 'SKILL.md').is_file() for name in skills):
        raise ValueError('Profile refers to an unavailable Skill')
    scripts = root / 'mcp/scripts'
    base = [sys.executable, '-X', 'utf8', '-B']
    steps, blocked, preserved = [], [], []
    config = home / 'config.toml'
    config_digest = hashlib.sha256(config.read_bytes()).hexdigest() if config.is_file() else None
    if 'agents' in selected:
        source_value = value.get('agents_source')
        if not isinstance(source_value, str) or not source_value:
            raise ValueError('Set agents_source relative to the private profile')
        source = (profile.parent / source_value).resolve()
        if any(not (source / name).is_file() for name in ('AGENTS.md', 'subagents.config.toml')):
            raise ValueError('Personal agent sources are missing')
        command = base + [str(scripts / 'install_global_agents.py'), '--source-root', str(source), '--codex-home', str(home)]
        if apply:
            command += ['--install'] + (['--replace'] if replace_agents else [])
        steps.append({'section': 'agents', 'command': command})
    if 'skills' in selected:
        for name in skills:
            command = base + [str(scripts / 'manage_categories.py'), 'skills', name, '--codex-home', str(home)]
            if apply:
                command += ['--apply', '--yes']
            steps.append({'section': 'skills', 'item': name, 'command': command})
    if 'plugins' in selected and plugins:
        config = home / 'config.toml'
        settings = tomllib.loads(config.read_text(encoding='utf-8-sig')) if config.is_file() else {}
        enabled = {key for key, row in settings.get('plugins', {}).items() if row.get('enabled', True)}
        duplicate = [key for key in enabled if key.split('@')[0] in plugins and not key.endswith('@codex-toolkit')]
        if duplicate:
            blocked.append('Existing Plugin owner must be migrated first: ' + ', '.join(sorted(duplicate)))
        direct = {path.parent.name for path in (home / 'skills').glob('*/SKILL.md')}
        if direct & plugin_skills:
            blocked.append('Existing direct Skills overlap selected Plugins: ' + ', '.join(sorted(direct & plugin_skills)))
        market = settings.get('marketplaces', {}).get('codex-toolkit')
        wanted = value.get('marketplace', {'source_type': 'local', 'source': str(root)})
        if not isinstance(wanted, dict) or set(wanted) - {'source_type', 'source', 'ref'} or wanted.get('source_type') not in ('local', 'git') or not isinstance(wanted.get('source'), str) or not wanted['source']:
            raise ValueError('Invalid marketplace selection')
        if 'ref' in wanted and (wanted['source_type'] != 'git' or not isinstance(wanted['ref'], str) or not wanted['ref'] or wanted['ref'].startswith('-')):
            raise ValueError('Invalid Git marketplace ref')
        if wanted['source_type'] == 'git':
            identity = git_identity(wanted['source'])
            matching = bool(market and market.get('source_type') == 'git' and git_identity(market.get('source', '')) == identity and ('ref' not in wanted or market.get('ref') == wanted['ref']))
        else:
            if Path(wanted['source']).resolve() != root:
                raise ValueError('Local marketplace must use the reviewed toolkit checkout')
            matching = bool(market and market.get('source_type') == 'local' and Path(market.get('source', '')).resolve() == root)
        if market and not matching:
            blocked.append('Review the existing codex-toolkit marketplace source before restoring')
        cli = shutil.which('codex') or 'codex'
        if not market:
            command = [cli, 'plugin', 'marketplace', 'add', wanted['source'], '--json']
            if wanted['source_type'] == 'git':
                command += ['--ref', wanted.get('ref', revision)]
            steps.append({'section': 'plugins', 'command': command})
        for name in plugins:
            key = name + '@codex-toolkit'
            if key in settings.get('plugins', {}):
                preserved.append({'item': key, 'enabled': settings['plugins'][key].get('enabled', True)})
            else:
                steps.append({'section': 'plugins', 'item': name, 'command': [cli, 'plugin', 'add', key, '--json']})
    if 'tools' in selected:
        platform = platform or ('windows' if sys.platform == 'win32' else 'macos' if sys.platform == 'darwin' else 'linux')
        if platform not in ('windows', 'macos', 'linux'):
            raise ValueError('Unsupported target platform')
        native_platform = 'windows' if sys.platform == 'win32' else 'macos' if sys.platform == 'darwin' else 'linux'
        if apply and platform != native_platform:
            blocked.append('Apply tools on the actual target platform')
        tools = value.get('tools', {})
        if not isinstance(tools, dict) or set(tools) - {'windows', 'macos', 'linux'}:
            raise ValueError('Invalid platform tool choices')
        entries = tools.get(platform, [])
        if selected_tools is not None:
            selected_ids = subset([entry['id'] for entry in entries], selected_tools, 'tools')
            entries = [entry for entry in entries if entry['id'] in selected_ids]
        manifest = json.loads((root / 'mcp/tools/development-tools.requirements.json').read_text(encoding='utf-8'))
        seen = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {'id', 'interface'} or entry['id'] not in manifest['tools'] or entry['interface'] not in {'native', 'mcp'} or entry['id'] in seen:
                raise ValueError('Invalid or duplicate selected tool')
            seen.add(entry['id'])
            command = base + [str(scripts / 'install_development_tool.py'), '--tool', entry['id'], '--interface', entry['interface'], '--config', str(home / 'config.toml'), '--no-guide']
            if apply:
                command += ['--apply', '--yes']
            steps.append({'section': 'tools', 'item': entry['id'], 'command': command})
    return {'status': 'preview', 'revision': head, 'sections': sorted(selected), 'steps': steps, 'blocked': blocked, 'manual': value.get('manual', []), 'reload_verified': False, 'preserved_plugins': preserved, 'config_sha256': config_digest}


def child_environment(home):
    environment = {**os.environ, 'CODEX_HOME': str(home)}
    if sys.platform == 'win32':
        # Native marketplace staging may exceed MAX_PATH; keep this Git option process-local.
        count = int(environment.get('GIT_CONFIG_COUNT', '0'))
        if count < 0:
            raise ValueError('Invalid process-local Git configuration count')
        environment.update({'GIT_CONFIG_COUNT': str(count + 1),
                            'GIT_CONFIG_KEY_' + str(count): 'core.longpaths',
                            'GIT_CONFIG_VALUE_' + str(count): 'true'})
    return environment


def execute(preview, home):
    if preview['blocked']:
        raise ValueError('Resolve preview blockers before any restore writes')
    if not preview['steps']:
        return {'status': 'unchanged', 'completed': [], 'reload_verified': False}
    home = home.expanduser().resolve()
    home.mkdir(parents=True, exist_ok=True)
    lock = home / '.setup-restore.lock'
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('Another restore owns the device-local lock; review it before retrying')
    os.close(descriptor)
    completed = []
    try:
        config = home / 'config.toml'
        current = hashlib.sha256(config.read_bytes()).hexdigest() if config.is_file() else None
        if 'config_sha256' in preview and current != preview['config_sha256']:
            raise ValueError('Local configuration changed; preview again')
        if config.is_file():
            backup = home / 'backups' / ('setup-restore-' + uuid.uuid4().hex) / 'config.toml'
            backup.parent.mkdir(parents=True)
            shutil.copy2(config, backup)
            if hashlib.sha256(backup.read_bytes()).hexdigest() != current:
                raise ValueError('Configuration backup verification failed')
        for step in preview['steps']:
            result = subprocess.run(step['command'], env=child_environment(home), check=False)
            if result.returncode:
                raise ValueError(f"Restore stopped at {step['section']} / {step.get('item', 'sources')}, exit={result.returncode}; completed steps={len(completed)}, inspect installer backups")
            completed.append({'section': step['section'], 'item': step.get('item')})
        return {'status': 'applied', 'completed': completed, 'reload_verified': False}
    finally:
        lock.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--toolkit-root', type=Path, default=ROOT)
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex'))
    parser.add_argument('--section', choices=SECTIONS, action='append', help='Repeat to select scope; defaults to agents/skills/plugins, tools are opt-in')
    parser.add_argument('--plugin', action='append', help='Select an explicit subset of profile Plugins')
    parser.add_argument('--skill', action='append', help='Select an explicit subset of profile Skills')
    parser.add_argument('--tool', action='append', help='Select an explicit subset of platform tools')
    parser.add_argument('--platform', choices=('windows', 'macos', 'linux'), help='Preview a platform; apply requires the current platform')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--replace-agents', action='store_true', help='Explicitly back up and replace differing personal Global/profile files; requires --apply')
    args = parser.parse_args(argv)
    if args.replace_agents and not args.apply:
        parser.error('--replace-agents requires --apply')
    try:
        preview = plan(args.toolkit_root, args.profile, args.codex_home, args.section or SECTIONS[:3], args.apply, args.replace_agents, args.plugin, args.skill, args.tool, args.platform)
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        if args.apply:
            # Detect source/profile/config changes before any delegated writes.
            if plan(args.toolkit_root, args.profile, args.codex_home, args.section or SECTIONS[:3], True, args.replace_agents, args.plugin, args.skill, args.tool, args.platform) != preview:
                raise ValueError('Restore plan changed; preview again')
            print(json.dumps(execute(preview, args.codex_home), ensure_ascii=False, indent=2))
        return 1 if preview['blocked'] else 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
