#!/usr/bin/env python3
"""Bounded, read-only Angular maintenance review orchestration (no target execution)."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

VERSION = '0.1.0'
EXTENSIONS = {'.ts', '.tsx', '.mts', '.cts', '.html', '.css', '.scss'}
STATUSES = ('PASS', 'FAIL', 'WARN', 'SKIP', 'ERROR', 'MANUAL')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounded(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Path escapes the selected root')
    return path


def command(args, cwd, payload=None):
    return subprocess.run(args, cwd=cwd, input=payload, capture_output=True,
                          text=True, encoding='utf-8', timeout=90, shell=False,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def select(args, root):
    if Path(args.scope).is_absolute() or '..' in Path(args.scope).parts or args.scope.startswith(':'):
        raise ValueError('Scope must be a literal root-relative path without parent traversal')
    scope = bounded(root, args.scope)
    if args.mode == 'files':
        if not args.file:
            raise ValueError('files mode requires --file')
        candidates = [bounded(root, f) for f in args.file]
    else:
        if args.file:
            raise ValueError('--file belongs to files mode')
        candidates = []
        if args.mode == 'module':
            if not scope.is_dir():
                raise ValueError('module scope must be an existing directory')
            # Do not descend into dependency/output directories or directory symlinks.
            for base, dirs, files in os.walk(scope, followlinks=False):
                dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', 'dist', 'build', '.angular'}
                           and not (Path(base) / d).is_symlink()]
                candidates.extend(Path(base) / f for f in files)
        else:
            if not args.staged and not args.unstaged and not args.untracked:
                raise ValueError('diff mode requires a Git selection flag')
            prefix = ['git', '--no-optional-locks', '-C', str(root), '--literal-pathspecs']
            top = command(prefix + ['rev-parse', '--show-toplevel'], root)
            if top.returncode or Path(top.stdout.strip()).resolve() != root:
                raise ValueError('--root must be the Git root in diff mode')
            modes = []
            if args.staged:
                modes.append(['diff', '--cached', '--name-only', '-z', '--diff-filter=ACMRT'])
            if args.unstaged:
                modes.append(['diff', '--name-only', '-z', '--diff-filter=ACMRT'])
            if args.untracked:
                modes.append(['ls-files', '--others', '--exclude-standard', '-z'])
            for mode in modes:
                result = command(prefix + mode + ['--', scope.relative_to(root).as_posix()], root)
                if result.returncode:
                    raise ValueError('Git selection failed; no fallback scan')
                candidates.extend(bounded(root, f) for f in result.stdout.split('\0') if f)
    selected, skipped = [], []
    for candidate in sorted(set(candidates)):
        real = bounded(root, candidate)
        if not real.is_relative_to(scope) and real != scope:
            raise ValueError('Selected file escapes the explicit scope')
        if not real.is_file():
            skipped.append({'path': candidate.relative_to(root).as_posix(), 'reason': 'missing-or-not-file'})
        elif real.suffix not in EXTENSIONS:
            skipped.append({'path': real.relative_to(root).as_posix(), 'reason': 'unsupported-extension'})
        else:
            selected.append(real)
    if len(selected) > 1000 or sum(p.stat().st_size for p in selected) > 20_000_000:
        raise ValueError('Scope exceeds 1000 files or 20 MB; narrow it explicitly')
    return sorted(set(selected)), skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--scope', required=True, help='Literal root-relative directory or file')
    parser.add_argument('--mode', choices=['files', 'diff', 'module'], required=True)
    parser.add_argument('--file', action='append', default=[])
    parser.add_argument('--dependency', action='append', default=[], help='Explicit root-relative read dependency, not another scan root')
    parser.add_argument('--depth', choices=['static', 'semantic', 'runtime'], default='static')
    parser.add_argument('--profile', type=Path, help='Local JSON data only; never loaded as code')
    parser.add_argument('--typescript', type=Path, required=True, help='Approved installed TypeScript JS API entry')
    parser.add_argument('--angular-compiler', type=Path, help='Approved installed Angular compiler ESM entry')
    parser.add_argument('--node', default='node')
    parser.add_argument('--report', type=Path, required=True, help='New local JSON file outside the scan root')
    for flag in ['staged', 'unstaged', 'untracked']:
        parser.add_argument('--' + flag, action='store_true')
    args = parser.parse_args(argv)
    root = args.root.resolve(strict=True)
    report_path = args.report.resolve()
    if report_path.exists() or report_path.is_relative_to(root) or report_path.suffix != '.json':
        parser.error('Report must be a new .json file outside the scan root')
    result = {'schemaVersion': 1, 'toolVersion': VERSION, 'selection': {'mode': args.mode, 'scope': args.scope,
              'depth': args.depth, 'content': 'working-tree', 'dependencies': args.dependency}, 'results': []}
    try:
        if args.mode != 'diff' and (args.staged or args.unstaged or args.untracked):
            raise ValueError('Git selection flags require diff mode')
        files, skipped = select(args, root)
        dependencies = [bounded(root, d) for d in args.dependency]
        if any(not d.is_file() or d.suffix not in {'.ts', '.tsx', '.mts', '.cts'} for d in dependencies):
            raise ValueError('Dependencies must be explicit existing TypeScript files')
        if len(dependencies) > 1000 or sum(d.stat().st_size for d in dependencies) > 20_000_000:
            raise ValueError('Dependency scope exceeds limits')
        profile = json.loads(args.profile.read_text(encoding='utf-8-sig')) if args.profile else {'id': 'portable', 'version': '1'}
        allowed = {'id', 'version', 'explicitPublic', 'format', 'compilerOptions'}
        if not isinstance(profile, dict) or set(profile) - allowed or not isinstance(profile.get('id'), str) or not isinstance(profile.get('version'), str):
            raise ValueError('Invalid profile: explicit id/version and supported data fields required')
        if 'explicitPublic' in profile and not isinstance(profile['explicitPublic'], bool):
            raise ValueError('explicitPublic must be boolean')
        if 'format' in profile and (not isinstance(profile['format'], dict) or set(profile['format']) != {'indentSize', 'semicolons'}
                or type(profile['format']['indentSize']) is not int or not 1 <= profile['format']['indentSize'] <= 16
                or profile['format']['semicolons'] not in {'insert', 'remove', 'ignore'}):
            raise ValueError('Invalid explicit formatter settings')
        observed = sorted(set(files + dependencies))
        hashes = {p.relative_to(root).as_posix(): digest(p) for p in observed}
        result.update(inputs=hashes, skipped=skipped, profile=profile,
                      profileSha256=digest(args.profile) if args.profile else None)
        request = {'root': str(root), 'files': [str(p) for p in files], 'dependencies': [str(p) for p in dependencies],
                   'depth': args.depth, 'profile': profile, 'typescript': str(args.typescript.resolve()),
                   'angularCompiler': str(args.angular_compiler.resolve()) if args.angular_compiler else None}
        worker = command([args.node, str(Path(__file__).with_name('maintainability_ast.cjs'))], root, json.dumps(request))
        if worker.returncode:
            raise ValueError('AST worker failed; inspect approved local environment, raw stderr withheld')
        result.update(json.loads(worker.stdout))
        if any(not p.is_file() or digest(p) != hashes[p.relative_to(root).as_posix()] for p in observed):
            raise ValueError('Inputs changed during review; findings require a fresh snapshot')
        result['inputsUnchanged'] = True
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        result['results'].append({'ruleId': 'TOOL.INPUT', 'status': 'ERROR', 'severity': 'error', 'confidence': 'high',
            'path': None, 'line': None, 'scope': args.scope, 'depth': args.depth, 'method': 'input/runner boundary',
            'evidence': str(error) if isinstance(error, ValueError) else type(error).__name__,
            'sourceVersion': VERSION, 'impact': 'Coverage incomplete', 'verification': 'Correct inputs or environment; rerun',
            'autoFix': False})
    result['summary'] = {s: sum(row['status'] == s for row in result['results']) for s in STATUSES}
    result['exitCode'] = 2 if result['summary']['ERROR'] else 1 if result['summary']['FAIL'] else 0
    result['complete'] = not any(result['summary'][s] for s in ['ERROR', 'SKIP', 'MANUAL'])
    # Exclusive creation prevents overwriting evidence or any source through a symlink.
    with report_path.open('x', encoding='utf-8') as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps({'report': str(report_path), 'summary': result['summary'], 'exitCode': result['exitCode'],
                      'complete': result['complete']}))
    return result['exitCode']


if __name__ == '__main__':
    sys.exit(main())
