"""Plan, prepare and check one selected plugin runtime without changing client settings."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

DELEGATED = 'TOOLBOX_RUNTIME_DELEGATED'


def registry_path():
    selected = os.environ.get('TOOLBOX_RUNTIMES')
    if selected:
        path = Path(selected).expanduser()
        if not path.is_absolute():
            raise ValueError('TOOLBOX_RUNTIMES must be an absolute registry file path')
        return path
    if sys.platform == 'win32':
        return Path(os.environ.get('APPDATA', str(Path.home() / 'AppData/Roaming'))) / 'CodexToolbox/runtimes.json'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/CodexToolbox/runtimes.json'
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'codex-toolbox/runtimes.json'


def record_runtime(name, python):
    python = Path(python)
    if not python.is_absolute() or not python.is_file():
        raise ValueError('Register an existing absolute Python executable')
    path = registry_path()
    entries = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    if not isinstance(entries, dict):
        raise ValueError('Runtime registry must be a JSON object')
    entries[name] = {'python': str(python)}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)
    return path


def registered_python(name):
    path = registry_path()
    if not path.is_file():
        return None
    entry = json.loads(path.read_text(encoding='utf-8')).get(name)
    if entry is None:
        return None
    python = Path(entry.get('python', '')) if isinstance(entry, dict) else Path()
    if not python.is_absolute() or not python.is_file():
        raise ValueError('Registered runtime is missing; register it again: ' + name)
    return python


def runtime_matches(component):
    try:
        return all(importlib.metadata.version(name) == expected for name, expected in component.get('versions', {}).items())
    except importlib.metadata.PackageNotFoundError:
        return False


def probe_versions(python, component):
    probe = ('import importlib.metadata as m,json,sys\n'
             'def v(n):\n'
             '    try: return m.version(n)\n'
             '    except m.PackageNotFoundError: return None\n'
             'print(json.dumps({n: v(n) for n in json.loads(sys.argv[1])}))')
    call = subprocess.run([python, '-I', '-c', probe,
                           json.dumps(list(dict.fromkeys([*component.get('versions', {}), *component.get('checks', [])])))],
                          capture_output=True, text=True, check=True, timeout=30)
    actual = json.loads(call.stdout)
    return actual, all(actual.get(key) == value for key, value in component.get('versions', {}).items())


def source(root, relative):
    path = root / relative
    if not isinstance(relative, str) or Path(relative).is_absolute() or '\\' in relative or '..' in Path(relative).parts:
        raise ValueError('Runtime resources must stay inside the package')
    for item in (path, *path.parents):
        if item == root.parent:
            break
        if item.is_symlink() or getattr(item, 'is_junction', lambda: False)():
            raise ValueError('Linked runtime resources are not supported')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Runtime resource escapes the package')
    return path


def plan(root, component, destination, python=None):
    destination = destination.absolute()
    if destination.is_relative_to(root):
        raise ValueError('Keep installed runtimes outside the immutable plugin')
    if component['kind'] == 'python':
        executable = destination / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        specs = [str(source(root, item)) for item in component.get('projects', [])]
        specs.extend(component.get('requirements', []))
        return {'kind': 'python', 'executable': str(executable), 'commands': [
            [python or sys.executable, '-m', 'venv', str(destination)],
            [str(executable), '-m', 'pip', 'install', *specs],
            [str(executable), '-m', 'pip', 'check']]}
    if component['kind'] == 'node':
        node = shutil.which('node') or 'node'
        npm = shutil.which('npm')
        candidates = [] if npm is None else [Path(npm).resolve().parent / 'node_modules/npm/bin/npm-cli.js',
                                            Path(npm).resolve().parent.parent / 'lib/node_modules/npm/bin/npm-cli.js',
                                            Path(npm).resolve()]
        cli = next((path for path in candidates if path.is_file() and path.name == 'npm-cli.js'), None)
        if cli is None:
            raise ValueError('Resolve an existing Node.js and npm-cli.js before preparing a Node runtime')
        return {'kind': 'node', 'executable': node, 'prefix': str(destination), 'commands': [
            [node, str(cli), 'install', '--prefix', str(destination), '--no-audit', '--no-fund',
             *component['requirements']]]}
    raise ValueError('This capability uses the original provider or an existing application')


def install(root, name, component, destination, python=None):
    prepared = plan(root, component, destination, python)
    if destination.exists():
        raise ValueError('Use a new runtime destination; existing environments are preserved')
    for path in (destination, *destination.parents):
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise ValueError('Use an unlinked runtime destination')
    destination.mkdir(parents=True)
    marker = destination / '.toolbox-runtime.json'
    marker.write_text(json.dumps({'component': name, 'status': 'preparing'}, indent=2) + '\n', encoding='utf-8')
    try:
        commands = prepared['commands']
        if component['kind'] == 'python':
            for index, relative in enumerate(component.get('projects', [])):
                original = source(root, relative)
                staged = destination / '.sources' / str(index)
                shutil.copytree(original, staged)
                commands[1] = [str(staged) if part == str(original) else part for part in commands[1]]
        for command in commands:
            subprocess.run(command, check=True, stdout=sys.stderr)
        for item in component.get('copies', []):
            shutil.copytree(source(root, item['source']), destination / item['target'])
        result = {**prepared, 'component': name, 'status': 'installed-not-client-verified'}
        if component.get('entry_command'):
            result['server_executable'] = str(destination / ('Scripts' if os.name == 'nt' else 'bin') /
                                            (component['entry_command'] + ('.exe' if os.name == 'nt' else '')))
        if component['kind'] == 'python' and component.get('module'):
            result['registry'] = str(record_runtime(name, prepared['executable']))
        marker.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        return result
    except BaseException:
        marker.write_text(json.dumps({'component': name, 'status': 'incomplete'}, indent=2) + '\n', encoding='utf-8')
        raise


def serve(root, component, read_root=None, write_root=None, extra=(), name='toolbox'):
    """Validate roots, then run the module; an empty read root starts a status-only server with no file access."""
    module = component.get('module')
    if not module:
        raise ValueError('This component has no bundled Python server')
    args = [*component.get('args', []), *extra]
    if read_root:
        if not component.get('read_root'):
            raise ValueError('This server does not accept a read root')
        if not Path(read_root).is_absolute() or not Path(read_root).is_dir():
            raise ValueError('Select an existing absolute read root in the plugin settings')
        args.extend(['--read-root', read_root])
    if write_root:
        if not component.get('write_root') or not Path(write_root).is_absolute() or not Path(write_root).is_dir():
            raise ValueError('Select an existing absolute write root supported by this server')
        if not read_root:
            raise ValueError('Select a read root before a write root')
        args.extend(['--write-root', write_root])
    if not runtime_matches(component):
        raise ValueError('Prepare or register the declared runtime before starting this server: ' + name)
    if component.get('read_root') and not read_root:
        serve_unconfigured(name)
        return
    sys.argv = [module, *args]
    runpy.run_module(module, run_name='__main__', alter_sys=True)


def serve_unconfigured(name):
    from mcp.server import MCPServer
    server = MCPServer(name, instructions='File access is not configured. No path is readable or writable until the user selects a read root in the plugin settings and reloads the plugin.')

    @server.tool()
    def file_access_status() -> dict:
        """Report that file access is unconfigured and no path can be read or written."""
        return {'status': 'file-access-unconfigured', 'component': name, 'read_roots': [], 'write_roots': [],
                'next_step': 'Select an existing read root in the plugin settings, then reload the plugin.'}

    server.run(transport='stdio')


def delegate(name, argv):
    """Run serve again with the registered runtime when the launching Python lacks the declared packages."""
    if os.environ.get(DELEGATED):
        return None
    python = registered_python(name)
    if python is None or python.resolve() == Path(sys.executable).resolve():
        return None
    return subprocess.run([str(python), '-I', '-B', str(Path(__file__).resolve()), *argv],
                          env={**os.environ, DELEGATED: '1'}, check=False).returncode


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('list', 'plan', 'install', 'doctor', 'register', 'serve'))
    parser.add_argument('--component')
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--python')
    parser.add_argument('--read-root')
    parser.add_argument('--write-root')
    original = list(sys.argv[1:] if argv is None else argv)
    extra = original[original.index('--') + 1:] if '--' in original else []
    args = parser.parse_args(original[:original.index('--')] if '--' in original else original)
    root = Path(__file__).resolve().parent.parent
    try:
        catalog = json.loads((root / 'runtime/components.json').read_text(encoding='utf-8'))
        if args.action == 'list':
            result = {'components': {key: {k: value[k] for k in ('kind', 'description') if k in value}
                                      for key, value in catalog.items()}}
        else:
            if not args.component or args.component not in catalog:
                raise ValueError('Select a component returned by list')
            component = catalog[args.component]
            if extra and args.action != 'serve':
                raise ValueError('Server arguments after -- are only accepted by serve')
            if args.action == 'serve':
                if component.get('module') and not runtime_matches(component):
                    code = delegate(args.component, original)
                    if code is not None:
                        return code
                serve(root, component, args.read_root, args.write_root, extra, args.component)
                return 0
            if args.action == 'register':
                if component['kind'] != 'python' or not component.get('module'):
                    raise ValueError('Only bundled Python servers use the runtime registry')
                if not args.python:
                    raise ValueError('register requires --python with the prepared environment executable')
                actual, matches = probe_versions(args.python, component)
                result = {'component': args.component, 'versions': actual, 'matches': matches}
                if not matches:
                    print(json.dumps(result, indent=2))
                    return 1
                result['registry'] = str(record_runtime(args.component, args.python))
                result['scope'] = 'Package metadata and registry only; no client invocation.'
            elif args.action == 'doctor':
                if component['kind'] == 'python':
                    actual, matches = probe_versions(args.python or sys.executable, component)
                    result = {'component': args.component, 'versions': actual, 'matches': matches,
                              'scope': 'Package metadata only; no client, authentication or API check.'}
                    if not result['matches']:
                        print(json.dumps(result, indent=2))
                        return 1
                else:
                    if args.destination is None:
                        raise ValueError('doctor requires --destination for Node runtimes')
                    installed = {}
                    for name, expected in component.get('versions', {}).items():
                        metadata = args.destination / 'node_modules' / name / 'package.json'
                        installed[name] = json.loads(metadata.read_text(encoding='utf-8'))['version']
                    result = {'component': args.component, 'versions': installed,
                              'matches': installed == component.get('versions', {}),
                              'scope': 'Package metadata only; no client or browser invocation.'}
                    if not result['matches']:
                        print(json.dumps(result, indent=2))
                        return 1
            else:
                if args.destination is None:
                    raise ValueError('plan and install require a new --destination')
                operation = install if args.action == 'install' else lambda r, n, c, d, p: plan(r, c, d, p)
                result = operation(root, args.component, component, args.destination, args.python)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, ImportError, subprocess.SubprocessError) as error:
        print('Toolbox runtime: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
