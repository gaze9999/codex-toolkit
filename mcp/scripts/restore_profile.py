"""Preview or restore explicitly selected portable setup choices through existing installers."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
SECTIONS = ('agents', 'skills', 'plugins', 'tools')


def names(value, label):
    if not isinstance(value, list) or any(not isinstance(item, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', item) for item in value):
        raise ValueError('Invalid names: ' + label)
    if len(value) != len(set(value)):
        raise ValueError('Duplicate names: ' + label)
    return value


def plan(root, profile, home, sections, apply=False, replace_agents=False):
    root, profile, home = root.resolve(), profile.resolve(), home.expanduser().resolve()
    if home == Path(home.anchor) or home == root or home.is_relative_to(root):
        raise ValueError('Use a dedicated Codex home outside the toolkit checkout')
    value = json.loads(profile.read_text(encoding='utf-8'))
    allowed = {'schema_version', 'toolkit_revision', 'agents_source', 'skills', 'plugins', 'tools', 'manual'}
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
    skills = names(value.get('skills', []), 'skills')
    plugins = names(value.get('plugins', []), 'plugins')
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
    steps, blocked = [], []
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
        if market and (market.get('source_type') != 'local' or Path(market.get('source', '')).resolve() != root):
            blocked.append('Review the existing codex-toolkit marketplace source before restoring')
        cli = shutil.which('codex') or 'codex'
        if not market:
            steps.append({'section': 'plugins', 'command': [cli, 'plugin', 'marketplace', 'add', str(root), '--json']})
        for name in plugins:
            steps.append({'section': 'plugins', 'item': name, 'command': [cli, 'plugin', 'add', name + '@codex-toolkit', '--json']})
    if 'tools' in selected:
        platform = 'windows' if sys.platform == 'win32' else 'macos' if sys.platform == 'darwin' else 'linux'
        tools = value.get('tools', {})
        if not isinstance(tools, dict) or set(tools) - {'windows', 'macos', 'linux'}:
            raise ValueError('Invalid platform tool choices')
        entries = tools.get(platform, [])
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
    return {'status': 'preview', 'revision': head, 'sections': sorted(selected), 'steps': steps, 'blocked': blocked, 'manual': value.get('manual', []), 'reload_verified': False}


def execute(preview, home):
    if preview['blocked']:
        raise ValueError('Resolve preview blockers before any restore writes')
    completed = []
    for step in preview['steps']:
        result = subprocess.run(step['command'], env={**os.environ, 'CODEX_HOME': str(home)}, check=False)
        if result.returncode:
            raise ValueError(f"Restore stopped at {step['section']} / {step.get('item', 'sources')}, exit={result.returncode}; completed steps={len(completed)}, inspect installer backups")
        completed.append({'section': step['section'], 'item': step.get('item')})
    return {'status': 'applied', 'completed': completed, 'reload_verified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--toolkit-root', type=Path, default=ROOT)
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex'))
    parser.add_argument('--section', choices=SECTIONS, action='append', help='Repeat to select scope; defaults to agents/skills/plugins, tools are opt-in')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--replace-agents', action='store_true', help='Explicitly back up and replace differing personal Global/profile files; requires --apply')
    args = parser.parse_args(argv)
    if args.replace_agents and not args.apply:
        parser.error('--replace-agents requires --apply')
    try:
        preview = plan(args.toolkit_root, args.profile, args.codex_home, args.section or SECTIONS[:3], args.apply, args.replace_agents)
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        if args.apply:
            # Detect source/profile/config changes before any delegated writes.
            if plan(args.toolkit_root, args.profile, args.codex_home, args.section or SECTIONS[:3], True, args.replace_agents) != preview:
                raise ValueError('Restore plan changed; preview again')
            print(json.dumps(execute(preview, args.codex_home), ensure_ascii=False, indent=2))
        return 1 if preview['blocked'] else 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
