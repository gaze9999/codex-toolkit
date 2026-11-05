"""Preview selected guidance snapshots, restoration, Claude adapters and local excludes.

No client settings, credentials, remote refs or tracked source files are changed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tomllib
import uuid

VERSION = "0.1.0"


def linked(path):
    try:
        return path.is_symlink() or bool(getattr(path.lstat(), 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))
    except FileNotFoundError:
        return False


def git(root, *args, data=None):
    return subprocess.check_output(['git', '-C', str(root), *args], input=data, stderr=subprocess.PIPE)


def identity(value):
    value = value.strip().removesuffix('.git').rstrip('/')
    value = value.removeprefix('https://').removeprefix('ssh://git@').replace('git@github.com:', 'github.com/')
    if not re.fullmatch(r'github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value):
        raise ValueError('Use a credential-free GitHub repository identity')
    return value.lower()


def repository(root):
    root = root.expanduser().resolve()
    if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
        raise ValueError('Select an exact Git checkout root')
    return root, identity(git(root, 'remote', 'get-url', 'origin').decode())


def safe(root, name):
    parts = PurePosixPath(name).parts
    if not parts or '\\' in name or ':' in name or name.startswith('/') or any(p in ('.', '..', '.git') for p in parts):
        raise ValueError('Use an explicit safe relative path')
    path = root
    for part in parts:
        path = path / part
        if linked(path):
            raise ValueError('Select the canonical source instead of a linked path: ' + name)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes selected root')
    return path


def guidance(name):
    path = PurePosixPath(name)
    if path.name in ('AGENTS.md', 'AGENTS.override.md', 'CLAUDE.md', 'CLAUDE.local.md'):
        return
    prefixes = ('.codex/agents/', '.codex/agent-guidance/', '.claude/agents/', '.claude/rules/', 'governance/', 'references/', 'agent-guidance/')
    if name.startswith(prefixes) and path.suffix in ('.md', '.toml'):
        return
    raise ValueError('Not an explicit instruction, reference or role file: ' + name)


def read(root, name):
    path = safe(root, name)
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError('Missing or oversized guidance: ' + name)
    return path.read_bytes()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def snapshot(root, names, output, apply=False):
    root, repo = repository(root)
    if not names or len(set(n.casefold() for n in names)) != len(names):
        raise ValueError('Select unique guidance files, including their required references')
    output = output.expanduser().absolute()
    if output.exists() or output.resolve().is_relative_to(root):
        raise ValueError('Choose a new private snapshot outside the source checkout')
    for parent in (output, *output.parents):
        if linked(parent):
            raise ValueError('Snapshot destination must not use links')
    payload = {}
    for name in names:
        guidance(name)
        payload[name] = read(root, name)
    manifest = {'schema_version': 1, 'repository': repo,
                'revision': git(root, 'rev-parse', 'HEAD').decode().strip(),
                'content_state': 'selected-working-tree-bytes',
                'files': {name: {'sha256': sha(raw), 'bytes': len(raw)} for name, raw in payload.items()}}
    if apply:
        if any(read(root, name) != raw for name, raw in payload.items()):
            raise ValueError('Source changed; preview again')
        output.mkdir(parents=True)
        for name, raw in payload.items():
            path = safe(output / 'files', name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        load_snapshot(output)
    return {'status': 'captured' if apply else 'preview', **manifest}


def load_snapshot(bundle):
    manifest = json.loads(read(bundle, 'manifest.json'))
    if manifest.get('schema_version') != 1 or not manifest.get('files'):
        raise ValueError('Unsupported or empty snapshot')
    identity(manifest['repository'])
    payload = {}
    for name, row in manifest['files'].items():
        guidance(name)
        raw = read(bundle / 'files', name)
        if sha(raw) != row['sha256'] or len(raw) != row['bytes']:
            raise ValueError('Snapshot hash mismatch: ' + name)
        payload[name] = raw
    if len({n.casefold() for n in payload}) != len(payload):
        raise ValueError('Case-colliding snapshot paths')
    return manifest, payload


def write_selected(root, payload, apply=False, replace=False):
    tracked = set(git(root, 'ls-files', '-z').decode().split('\0'))
    rows, before = [], {}
    for name, raw in payload.items():
        path = safe(root, name)
        if name in tracked:
            raise ValueError('Tracked source must be maintained through its owner: ' + name)
        before[name] = path.read_bytes() if path.exists() else None
        status = 'CURRENT' if before[name] == raw else 'MISSING' if before[name] is None else 'CONFLICT'
        rows.append({'path': name, 'status': status, 'sha256': sha(raw)})
    if apply:
        if any(row['status'] == 'CONFLICT' for row in rows) and not replace:
            raise ValueError('Conflicts preserved; review before using --replace')
        for name, raw in before.items():
            path = safe(root, name)
            if (path.read_bytes() if path.exists() else None) != raw:
                raise ValueError('Target changed; preview again')
        exclude(root, ['/' + name for name in payload], apply=True, label='guidance')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
        backup = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip()) / 'agent-file-backups' / stamp
        for name, raw in payload.items():
            if before[name] == raw:
                continue
            if before[name] is not None:
                saved = safe(backup, name)
                saved.parent.mkdir(parents=True, exist_ok=True)
                saved.write_bytes(before[name])
                if saved.read_bytes() != before[name]:
                    raise ValueError('Backup readback failed')
            target = safe(root, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            if target.read_bytes() != raw:
                raise ValueError('Target readback failed')
    return {'status': 'applied' if apply else 'preview', 'files': rows, 'client_loading_verified': False}


def restore(root, bundle, apply=False, replace=False):
    root, repo = repository(root)
    manifest, payload = load_snapshot(bundle)
    if identity(manifest['repository']) != repo:
        raise ValueError('Snapshot repository differs from target')
    return write_selected(root, payload, apply, replace)


def restore_project(root, store, project, names, apply=False, replace=False, historical=False):
    root, repo = repository(root)
    _, store_repo = repository(store.parent)
    manifest = json.loads(read(store, 'manifest.json'))
    entry = manifest['projects'][project]
    if identity(entry['source_repository']) != repo:
        raise ValueError('Project backup belongs to another repository')
    owner = entry.get('restoration_owner', {}).get('repository')
    if not owner or identity(owner) != store_repo:
        if not historical:
            raise ValueError('Historical snapshot; use its current restoration owner or explicitly review --historical')
    if not names or len(set(names)) != len(names):
        raise ValueError('Select unique --file entries from the project manifest')
    rows = {row['path']: row for row in entry['files']}
    payload = {}
    for name in names:
        guidance(name)
        row = rows[name]
        if row.get('source_status', 'present') != 'present':
            raise ValueError('Retired source must not be restored: ' + name)
        raw = read(safe(store, project), name)
        if sha(raw) != row['sha256'] or len(raw) != row['bytes']:
            raise ValueError('Project backup hash mismatch: ' + name)
        payload[name] = raw
    return write_selected(root, payload, apply, replace)


def claude(root, entry, role_names, apply=False, replace=False, roles_root=None, target_entry='CLAUDE.md'):
    root, _ = repository(root)
    roles_root, role_repository = repository(roles_root or root)
    if entry not in ('AGENTS.md', 'AGENTS.override.md'):
        raise ValueError('Select the effective root instruction entry')
    read(root, entry)
    if target_entry not in ('CLAUDE.md', 'CLAUDE.local.md'):
        raise ValueError('Select a native Claude instruction filename')
    payload = {target_entry: ('@' + entry + '\n').encode()}
    for name in role_names:
        if not name.startswith('.codex/agents/') or not name.endswith('.toml'):
            raise ValueError('Select explicit native Codex role files')
        role = tomllib.loads(read(roles_root, name).decode('utf-8'))
        if set(role) != {'name', 'description', 'developer_instructions'}:
            raise ValueError('Role has client-specific settings; review a native Claude definition: ' + name)
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', role['name']) or not all(isinstance(v, str) and v.strip() for v in role.values()):
            raise ValueError('Invalid role metadata')
        target = '.claude/agents/' + role['name'] + '.md'
        if target in payload:
            raise ValueError('Duplicate role name')
        payload[target] = ('---\nname: ' + json.dumps(role['name']) + '\ndescription: ' + json.dumps(role['description'])
                           + '\n---\n\n' + role['developer_instructions'].strip() + '\n').encode()
    return {**write_selected(root, payload, apply, replace), 'role_source_repository': role_repository}


def exclude(root, patterns, apply=False, label='temporary'):
    root, _ = repository(root)
    if not re.fullmatch('[a-z-]+', label):
        raise ValueError('Invalid exclusion group')
    if not patterns or any(not p or '\n' in p or '\r' in p or '\x00' in p or p.startswith('!') for p in patterns):
        raise ValueError('Use explicit nonempty ignore patterns without negation')
    path = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-path', 'info/exclude').decode().strip())
    if any(linked(p) for p in (path, *path.parents)):
        raise ValueError('Linked Git exclude path')
    before = path.read_bytes() if path.exists() else b''
    start, end = '# BEGIN managed-agent-files ' + label, '# END managed-agent-files ' + label
    text = before.decode('utf-8')
    if start in text or end in text:
        if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
            raise ValueError('Malformed managed exclusion block')
        a, b = text.index(start), text.index(end) + len(end)
        existing = text[a + len(start):text.index(end)].splitlines()
        patterns = [*filter(None, existing), *patterns]
    else:
        a = b = len(text)
    block = start + '\n' + '\n'.join(dict.fromkeys(patterns)) + '\n' + end
    after = (text[:a] + ('\n' if a and text[a-1] != '\n' else '') + block + text[b:] + ('\n' if not text[b:].endswith('\n') else '')).encode()
    tracked = git(root, 'ls-files', '-z')
    # --exclude-from checks these selected patterns, independent of other ignore files.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='agent-excludes-') as temp:
        selected = Path(temp) / 'patterns'
        selected.write_text('\n'.join(patterns) + '\n', encoding='utf-8')
        matched = git(root, 'ls-files', '-ci', '--exclude-from=' + str(selected), '-z').decode().split('\0')
    matched = list(filter(None, matched))
    if matched:
        raise ValueError('Patterns would conceal tracked source: ' + ', '.join(matched[:8]))
    if apply and before != after:
        path.parent.mkdir(parents=True, exist_ok=True)
        if (path.read_bytes() if path.exists() else b'') != before or git(root, 'ls-files', '-z') != tracked:
            raise ValueError('Git state changed; preview again')
        if before:
            saved = path.with_name('exclude.before-agent-files-' + uuid.uuid4().hex)
            saved.write_bytes(before)
            if saved.read_bytes() != before:
                raise ValueError('Exclude backup readback failed')
        path.write_bytes(after)
        if path.read_bytes() != after:
            raise ValueError('Exclude readback failed')
    return {'status': 'CURRENT' if before == after else 'applied' if apply else 'preview', 'patterns': list(dict.fromkeys(patterns)), 'tracked_matches': []}


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('snapshot', 'restore', 'claude', 'ignore'))
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--file', action='append', default=[])
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--project', help='Selected project in an existing private project-agents manifest')
    parser.add_argument('--historical', action='store_true', help='Use only after comparing a historical snapshot with its current owner')
    parser.add_argument('--entry', choices=('AGENTS.md', 'AGENTS.override.md'), default='AGENTS.md')
    parser.add_argument('--claude-entry', choices=('CLAUDE.md', 'CLAUDE.local.md'), default='CLAUDE.md', help='Use CLAUDE.local.md to preserve an existing tracked CLAUDE.md')
    parser.add_argument('--role', action='append', default=[])
    parser.add_argument('--roles-root', type=Path, help='Explicit canonical role checkout; do not read installed directory links')
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--group', action='append', default=[])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    try:
        if args.replace and not args.apply:
            raise ValueError('--replace requires --apply')
        if args.action in ('snapshot', 'restore'):
            if not args.bundle:
                raise ValueError('Select --bundle')
            if args.action == 'snapshot':
                result = snapshot(args.repo, args.file, args.bundle, args.apply)
            elif args.project:
                result = restore_project(args.repo, args.bundle.resolve(), args.project, args.file, args.apply, args.replace, args.historical)
            else:
                result = restore(args.repo, args.bundle, args.apply, args.replace)
        elif args.action == 'claude':
            result = claude(args.repo, args.entry, args.role, args.apply, args.replace, args.roles_root, args.claude_entry)
        else:
            if not args.profile or not args.group:
                raise ValueError('Select an ignore profile and groups')
            profile = json.loads(args.profile.read_text(encoding='utf-8'))
            if profile.get('schema_version') != 1 or set(args.group) - set(profile['groups']):
                raise ValueError('Unknown ignore profile or group')
            result = exclude(args.repo, [p for group in args.group for p in profile['groups'][group]], args.apply)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'blocked', 'error': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
