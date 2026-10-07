#!/usr/bin/env python3
"""Build a native portable CLI with a relocatable Python runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import tempfile
import tomllib
import zipfile

from prepare_mcp_release import copy_installer_resources, normalize_tag, source_hashes

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = "codex-setup.portable-release.v1"
SPEC = "mcp/tools/cli-release.requirements.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def target_name() -> str:
    machine = platform.machine().lower()
    arch = "x64" if machine in {"amd64", "x86_64"} else "arm64" if machine in {"arm64", "aarch64"} else ""
    system = {"Windows": "windows", "Darwin": "macos"}.get(platform.system(), "")
    target = system + "-" + arch
    if target not in {"windows-x64", "macos-arm64", "macos-x64"}:
        raise ValueError("Build on a supported native Windows or macOS runner")
    return target


def launchers(bundle: Path) -> None:
    cli_template = (bundle/'launch-cli.cmd').read_text(encoding='utf-8')
    kept = {'launch-cli.cmd', 'launch-cli.ps1'} if os.name == 'nt' else {'launch-cli.sh'}
    for name in ('launch-cli.cmd', 'launch-cli.ps1', 'launch-cli.sh'):
        if name not in kept:
            (bundle/name).unlink()
    if os.name == 'nt':
        launcher = 'launch-cli.cmd'
        (bundle/launcher).write_text(cli_template.replace('setlocal DisableDelayedExpansion', 'setlocal DisableDelayedExpansion\nset "CODEX_SETUP_PYTHON=%~dp0runtime\\python.exe"'), encoding='utf-8')
    else:
        launcher = 'launch-cli.command'
        path = bundle/launcher
        path.write_text('#!/bin/sh\nset -eu\nROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexport CODEX_SETUP_PYTHON="$ROOT_DIR/runtime/bin/python3"\nexec /bin/sh "$ROOT_DIR/launch-cli.sh" "$@"\n', encoding='utf-8')
        path.chmod(0o755)
    text = f'# Codex Setup CLI\n\n解壓後在終端機執行 `{launcher}`, 使用包內 Python, 不需安裝 Python 或 Node.js\n\n'
    if os.name == 'nt':
        text += 'PowerShell 也可執行 `./launch-cli.ps1`, 同樣使用包內 Python\n\n'
    command = launcher if os.name == 'nt' else './'+launcher
    text += f'以 `{command} --list` 列出 Agents、Skills、Plugins 與 MCP 四類, 操作見 [CLI 文件](docs/setup/cli.md)\n\n'
    text += '四類治理與安裝來源隨包提供, 個別工具的 runtime、browser 與帳戶依選定項目設定, 搬移時保留整個解壓資料夾. 來源與 checksum 見 `bundle-manifest.json`, 平台封裝見 [安裝包](docs/setup/packages.md)\n'
    (bundle/'README.md').write_text(text, encoding='utf-8')


def smoke(bundle: Path, powershell: bool = False) -> dict:
    env = {key:value for key,value in os.environ.items() if key not in {'PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV', 'CODEX_SETUP_PYTHON'}}
    env.update(PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    # Each entrypoint must select the bundled runtime without Python on PATH.
    env['PATH'] = str(Path(os.environ['SystemRoot'])/'System32') if os.name == 'nt' else '/usr/bin:/bin'
    if powershell and os.name != 'nt':
        raise ValueError('PowerShell smoke requires Windows')
    entry = bundle/('launch-cli'+('.ps1' if powershell else '.cmd' if os.name == 'nt' else '.command'))
    if powershell:
        shell = Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        command = [str(shell), '-NoLogo', '-NoProfile', '-ExecutionPolicy', 'RemoteSigned', '-File', str(entry)]
    else:
        command = [os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/c', str(entry)] if os.name == 'nt' else ['/bin/sh', str(entry)]
    with tempfile.TemporaryDirectory(prefix='cli-smoke-') as folder:
        home = Path(folder)
        config = home/'config.toml'
        config.write_bytes(b'')
        env['CODEX_HOME'] = str(home)
        commands = [['--list'], ['agents','--list','--codex-home',str(home)], ['skills','--list','--codex-home',str(home)], ['plugins','--list','--codex-home',str(home)], ['mcp','--list']]
        for args in commands:
            result = subprocess.run([*command,*args], cwd=bundle, env=env, capture_output=True, text=True, encoding='utf-8', timeout=60)
            if result.returncode or not result.stdout:
                raise ValueError('Portable CLI failed: '+result.stdout+result.stderr)
        if config.read_bytes() != b'':
            raise ValueError('CLI smoke changed its fixture config')
    return {'commands':len(commands), 'config_unchanged':True, 'system_python_required':False}


def build_sources() -> dict[str, str]:
    return source_hashes(ROOT) | {name:digest((ROOT/name).read_bytes()) for name in [SPEC, 'mcp/scripts/prepare_cli_release.py', '.github/workflows/cli-release.yml']}


def verify_archive(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError('Portable CLI ZIP CRC failed')
        manifest = json.loads(archive.read('bundle-manifest.json'))
        names = archive.namelist()
        if manifest.get('producer') != PRODUCER or len(names) != len(set(names)) or set(names) != set(manifest['files']) | {'bundle-manifest.json'}:
            raise ValueError('Portable manifest differs from ZIP contents')
        spec = json.loads((ROOT/SPEC).read_text(encoding='utf-8'))
        if manifest.get('source_files') != build_sources() or manifest.get('tag') != normalize_tag(manifest.get('tag', '')) or manifest.get('target') not in spec['targets']:
            raise ValueError('Portable CLI does not match the current reviewed source')
        if manifest.get('interface') != 'cli' or manifest.get('python') != spec['python_version'] or manifest.get('packages') != spec['packages'] or manifest.get('runtime_source') != spec['runtime_source']:
            raise ValueError('Portable CLI runtime differs from requirements')
        windows = manifest['target'].startswith('windows-')
        required = ['launch-cli.cmd', 'launch-cli.ps1', 'runtime/python.exe'] if windows else ['launch-cli.command', 'launch-cli.sh', 'runtime/bin/python3']
        forbidden = ['launch-cli.sh', 'launch-cli.command'] if windows else ['launch-cli.cmd', 'launch-cli.ps1']
        if any(name not in names for name in required) or any(name in names for name in forbidden) or any(name.startswith(('launch-gui', 'launch-web', 'mcp/tools/mcp-manager/', 'mcp/scripts/_workbench/')) for name in names):
            raise ValueError('Portable bundle must expose only its native CLI')
        for name, sha in manifest['files'].items():
            if Path(name).is_absolute() or '..' in Path(name).parts or digest(archive.read(name)) != sha:
                raise ValueError('Portable CLI file changed: '+name)
        if not windows:
            for name in ('launch-cli.command', 'runtime/bin/python3'):
                if not (archive.getinfo(name).external_attr >> 16) & stat.S_IXUSR:
                    raise ValueError('macOS CLI entry is not executable: '+name)
    return manifest


def prepare(python: Path, tag: str, output: Path, dry_run: bool = False) -> dict:
    tag = normalize_tag(tag)
    target = target_name()
    spec = json.loads((ROOT/SPEC).read_text(encoding='utf-8'))
    probe = subprocess.check_output([str(python), '-I', '-B', '-c', 'import json,sys,sysconfig,platform;print(json.dumps(dict(version=platform.python_version(),base=sys.base_prefix,prefix=sys.prefix,purelib=sysconfig.get_path("purelib"))))'], text=True)
    info = json.loads(probe)
    if info['version'] != spec['python_version'] or info['prefix'] != info['base']:
        raise ValueError('Select the pinned standalone base Python, not a virtual environment')
    base = Path(info['base']).resolve()
    purelib = Path(info['purelib']).resolve().relative_to(base)
    sources = build_sources()
    name = f'codex-setup-cli-{tag}-{target}.zip'
    output = output.resolve()
    if dry_run:
        return {'status':'preview', 'name':name, 'python':info['version'], 'target':target}
    output.mkdir(parents=True, exist_ok=True)
    destination = output/name
    if destination.exists():
        raise ValueError('Use a fresh output directory; existing CLI artifacts are preserved')
    with tempfile.TemporaryDirectory(prefix='cli-build-', dir=output) as folder:
        bundle = Path(folder)/'bundle'
        copy_installer_resources(ROOT, bundle)
        # No private user site or build environment enters the portable runtime.
        ignored = {'site-packages', '__pycache__', '.git', '.temp', 'Scripts'}
        for path in base.rglob('*'):
            if path.is_symlink() and not path.resolve().is_relative_to(base):
                raise ValueError('Runtime symlink leaves the selected distribution')
        shutil.copytree(base, bundle/'runtime', ignore=lambda _path,names:[name for name in names if name in ignored or name.startswith(('pip', 'idle', '2to3'))], symlinks=False)
        dependencies = tomllib.loads((ROOT/'mcp/mcp_servers/tool_setup/pyproject.toml').read_text(encoding='utf-8'))['project']['dependencies']
        if not set(dependencies) <= set(spec['packages']):
            raise ValueError('CLI package pins differ from setup requirements')
        subprocess.run([str(python), '-m', 'pip', '--isolated', 'install', '--only-binary=:all:', '--no-compile', '--no-deps', '--index-url', 'https://pypi.org/simple', '--target', str(bundle/'runtime'/purelib), *spec['packages']], check=True)
        launchers(bundle)
        evidence = smoke(bundle)
        if os.name == 'nt':
            evidence['powershell'] = smoke(bundle, powershell=True)
        files = {path.relative_to(bundle).as_posix():digest(path.read_bytes()) for path in sorted(bundle.rglob('*')) if path.is_file()}
        manifest = {'producer':PRODUCER, 'tag':tag, 'target':target, 'interface':'cli', 'python':info['version'], 'runtime_source':spec['runtime_source'], 'packages':spec['packages'], 'source_files':sources, 'smoke':evidence, 'files':files}
        (bundle/'bundle-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
        archive_path = Path(folder)/name
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(bundle.rglob('*')):
                if path.is_file():
                    item = zipfile.ZipInfo(path.relative_to(bundle).as_posix(), (1980,1,1,0,0,0))
                    item.create_system = 3
                    item.external_attr = (stat.S_IFREG | stat.S_IMODE(path.stat().st_mode)) << 16
                    item.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(item, path.read_bytes())
        verify_archive(archive_path)
        if sources != build_sources():
            raise ValueError('Source changed during CLI preparation')
        shutil.copyfile(archive_path, destination)
    (output/(name+'.sha256')).write_text(digest(destination.read_bytes())+'  '+name+'\n', encoding='utf-8')
    return {'status':'ready', 'path':str(destination), 'sha256':digest(destination.read_bytes()), 'target':target, 'smoke':evidence}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, help='Pinned native standalone base interpreter')
    parser.add_argument('--tag')
    parser.add_argument('--output', type=Path, default=ROOT/'dist/cli')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--verify', type=Path, help='Verify an existing CLI archive without rebuilding')
    args = parser.parse_args()
    try:
        if args.verify:
            manifest = verify_archive(args.verify)
            print(json.dumps({'status':'verified', 'target':manifest['target'], 'files':len(manifest['files'])}))
        else:
            if not args.python or not args.tag:
                parser.error('--python and --tag are required to build')
            print(json.dumps(prepare(args.python.resolve(), args.tag, args.output, args.dry_run)))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        parser.exit(2, str(error)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
