"""List four setup categories and synchronize one managed instruction or Skill."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

if __package__:
    from .manager_registry import inventory, file_plan, apply_file
    from .plugin_catalog import inventory as plugin_inventory, load_catalog, payload
else:
    from manager_registry import inventory, file_plan, apply_file
    from plugin_catalog import inventory as plugin_inventory, load_catalog, payload

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments and arguments[0] == 'agents' and len(arguments) > 1 and arguments[1] in {'global', 'desktop'}:
        script = 'install_global_agents.py' if arguments[1] == 'global' else 'render_desktop_settings.py'
        return subprocess.run([sys.executable, '-X', 'utf8', '-B', str(ROOT/'mcp/scripts'/script), *arguments[2:]], check=False).returncode
    if arguments and arguments[0] == 'plugins' and '--sync-installed' in arguments:
        if __package__:
            from .sync_local_plugins import main as sync_plugins
        else:
            from sync_local_plugins import main as sync_plugins
        return sync_plugins([arg for arg in arguments[1:] if arg != '--sync-installed'])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('category', choices=['agents', 'skills', 'plugins'])
    parser.add_argument('item', nargs='?', help='Exact managed item name from the list')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--codex-home', type=Path)
    parser.add_argument('--apply', action='store_true', help='Apply the selected item after preview and confirmation')
    parser.add_argument('--yes', action='store_true', help='Confirm the selected --apply operation')
    args = parser.parse_args(arguments)
    if args.yes and not args.apply:parser.error('--yes requires --apply')
    if args.list and args.item:parser.error('Choose either --list or an item')
    if args.apply and not args.item:parser.error('--apply requires one selected item')
    home = (args.codex_home or Path(os.environ.get('CODEX_HOME') or Path.home()/'.codex')).expanduser().resolve()
    if home == Path(home.anchor) or home == ROOT or home.is_relative_to(ROOT):
        parser.error('Codex home must be outside this repository and not a filesystem root')
    try:
        if args.category == 'plugins':
            if args.apply:parser.error('Install Plugins through the supported Codex Plugin interface')
            config = home/'config.toml'
            if config.is_symlink():raise ValueError('設定檔使用連結, 請先確認擁有者')
            settings = tomllib.loads(config.read_text(encoding='utf-8-sig')) if config.is_file() else {}
            settings['_direct_skills'] = [path.parent.name for path in (home/'skills').glob('*/SKILL.md')]
            rows = plugin_inventory(ROOT, settings)
            if args.item:
                bundle = next((entry for entry in load_catalog(ROOT) if entry['id'] == args.item), None)
                if bundle is None:raise ValueError('找不到選定 Plugin, 請先使用 --list')
                files, provenance = payload(ROOT, bundle)
                print(json.dumps({'status':'preview', 'availability':bundle['status'], 'blocked_reason':bundle.get('blocked_reason'),
                                  'files':len(files), **provenance}, ensure_ascii=False, indent=2))
            else:
                print(json.dumps({'category':'plugins', 'items':rows, 'management':'Codex Plugin interface', 'guide':'docs/plugins.md'}, ensure_ascii=False, indent=2))
            return 0
        rows = [entry for entry in inventory(ROOT, home) if entry['kind'] == ('skill' if args.category == 'skills' else 'agent')]
        if not args.item:
            print(json.dumps({'category':args.category, 'items':[{key:entry[key] for key in ('id','name','version','state','can_sync') if key in entry} for entry in rows],
                'commands':['agents global', 'agents desktop', 'agents subagent-profile --apply'] if args.category == 'agents' else ['skills NAME', 'skills NAME --apply']}, ensure_ascii=False, indent=2))
            return 0
        item = args.item
        selected = next((entry for entry in rows if entry['id'] == item or entry['name'] == item), None)
        if selected is None:raise ValueError('找不到選定項目, 請先使用 --list')
        plan = file_plan(selected, sync=True)
        print(json.dumps({key:value for key,value in plan.items() if not key.startswith('_')}, ensure_ascii=False, indent=2))
        if not args.apply or not plan['changed']:return 0
        if not args.yes and (not sys.stdin.isatty() or input('套用此項目並備份既有檔案? [y/N] ').lower() not in {'y','yes'}):
            print('未套用, 保留預覽')
            return 0
        print(json.dumps(apply_file(plan), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
