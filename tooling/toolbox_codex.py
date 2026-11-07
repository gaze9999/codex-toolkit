"""Launch the selected local MCP using non-secret device settings and no shell."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def settings_path():
    selected = os.environ.get('TOOLBOX_SETTINGS')
    if selected:
        path = Path(selected).expanduser()
        if not path.is_absolute():
            raise ValueError('TOOLBOX_SETTINGS must be an absolute settings file path')
        return path
    if sys.platform == 'win32':
        return Path(os.environ.get('APPDATA', str(Path.home() / 'AppData/Roaming'))) / 'CodexToolbox/settings.json'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/CodexToolbox/settings.json'
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'codex-toolbox/settings.json'


def resolve(root, connector, settings):
    manifest = json.loads((root / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))
    servers = json.loads((root / '.mcp.json').read_text(encoding='utf-8'))['mcpServers']
    server = dict(servers[connector])
    override = root / 'runtime/codex-args.json'
    if override.is_file():
        arguments = json.loads(override.read_text(encoding='utf-8'))
        server['args'] = arguments.get(connector, server.get('args', []))
    if 'command' not in server:
        raise ValueError('Use the direct portable declaration for remote MCP servers')
    declared = manifest.get('userConfig', {})
    supplied = settings.get(connector, {})
    if not isinstance(supplied, dict) or set(supplied) - set(declared):
        raise ValueError('Settings contain an unknown field for ' + connector)
    # userConfig is plugin-wide; only the fields this connector's declaration references are resolved.
    referenced = set(re.findall(r'\$\{user_config\.([A-Za-z0-9_]+)\}', json.dumps(server)))
    values = {}
    for key, field in declared.items():
        if key not in referenced:
            continue
        value = supplied.get(key, '')
        if value == '':
            value = field.get('default', '')
        if not isinstance(value, str) or '\x00' in value:
            raise ValueError('Local settings must be NUL-free strings: ' + key)
        if field.get('sensitive'):
            raise ValueError('Keep credentials outside the portable local settings file')
        if field.get('required') and not value:
            raise ValueError('Set ' + connector + '.' + key + ' in the device settings file')
        if value and field['type'] in {'directory', 'file'}:
            path = Path(value).expanduser()
            if not path.is_absolute() or (not path.is_dir() if field['type'] == 'directory' else not path.is_file()):
                raise ValueError('Select an existing absolute ' + field['type'] + ': ' + key)
            value = str(path)
        values[key] = value

    def expand(text):
        text = text.replace('${CLAUDE_PLUGIN_ROOT}', str(root))
        text = re.sub(r'\$\{user_config\.([A-Za-z0-9_]+)\}', lambda match: values[match.group(1)], text)
        if '${' in text:
            raise ValueError('Unsupported setting placeholder')
        return text

    command = expand(server['command'])
    if Path(command).name != command:
        command = str(Path(command).expanduser())
        if not Path(command).is_absolute():
            raise ValueError('Use a command name on PATH or an absolute executable path')
    executable = shutil.which(command) or (command if Path(command).is_file() else None)
    if not executable or Path(executable).suffix.lower() in {'.cmd', '.bat', '.ps1'}:
        raise ValueError('Select an existing native Python, Node or MCP executable')
    return executable, [expand(arg) for arg in server.get('args', [])], {k: expand(v) for k, v in server.get('env', {}).items()}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('connector')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        root = Path(__file__).resolve().parent.parent
        path = settings_path()
        settings = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
        if not isinstance(settings, dict):
            raise ValueError('The device settings file must contain a JSON object')
        executable, arguments, overrides = resolve(root, args.connector, settings)
        if args.check:
            print(json.dumps({'connector': args.connector, 'status': 'configuration-resolved',
                              'scope': 'Existing paths and configuration only; no server or authentication check.'}))
            return 0
        environment = {**os.environ, **overrides}
        if os.name != 'nt':
            os.execvpe(executable, [executable, *arguments], environment)
        with subprocess.Popen([executable, *arguments], env=environment,
                              stdin=sys.stdin.buffer, stdout=sys.stdout.buffer, stderr=sys.stderr.buffer) as child:
            try:
                return child.wait()
            finally:
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('Toolbox local MCP: ' + str(error) + '\nDevice settings: ' + str(settings_path()), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
