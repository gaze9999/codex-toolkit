"""Bounded source/mirror inventory and previewable configuration edits."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import tomllib
import uuid
from urllib.parse import urlsplit

if __package__:
    from .manager_documents import frontmatter, yaml_data, safe_url, EDITABLE, READABLE, parse_document, personal_text, validate_personal
    from .bootstrap_mcp import atomic, toml_value
    from .uninstall_mcp import without_registration
else:
    from manager_documents import frontmatter, yaml_data, safe_url, EDITABLE, READABLE, parse_document, personal_text, validate_personal
    from bootstrap_mcp import atomic, toml_value
    from uninstall_mcp import without_registration


def safe_path(path, root):
    if not path.resolve().is_relative_to(root.resolve()) or any(p.is_symlink() for p in (path,*path.parents) if p==root or p.is_relative_to(root)):
        raise ValueError('檔案超出選定範圍或使用連結')
    return path


def content(path):
    if path.is_file() and path.stat().st_size<=65536:
        return path.read_text(encoding='utf-8-sig')
    raise ValueError('檔案不存在或超過編輯上限')


def tree_hash(folder):
    digest=hashlib.sha256()
    for path in sorted(folder.rglob('*')):
        relative=path.relative_to(folder)
        if not path.is_file() or any(part in {'__pycache__','.git','dist','build','.venv'} or part.endswith('.egg-info') for part in relative.parts) or path.suffix in {'.pyc','.pyo'}:
            continue
        safe_path(path,folder)
        digest.update(relative.as_posix().encode());digest.update(path.read_bytes())
    return digest.hexdigest()


def inventory(root, home, project=None):
    entries=[]
    personal=home/'manager/chatgpt-web.json'
    safe_path(personal,home)
    entries.append({'id':'web-personal','kind':'web','name':'帳戶自訂指示與個人資訊','path':str(personal),
                    'state':'本機草稿','editable':True,'can_sync':False,'personal':True,
                    'position':'ChatGPT 設定 → 個人化 → 自訂指示 / 個人資訊',
                    'steps':'維護自訂指示, 暱稱, 職業與更多資訊, 複製到網頁保存後讀回',
                    'source':'https://help.openai.com/en/articles/8096356-chatgpt-custom-instructions'})
    web=root/'agents/chatgpt-web'
    if (web/'profiles.json').is_file():
        for profile in json.loads(content(web/'profiles.json'))['profiles']:
            source=safe_path(web/(profile['id']+'.md'),root)
            text=content(source)
            entries.append({'id':'web:'+profile['id'],'kind':'web','name':profile['title'],'path':str(source),'state':'待在網頁套用',
                            'editable':True,'can_sync':False,'characters':len(text),'position':profile['position'],
                            'limit':profile.get('limit'),'steps':profile['steps'],'source':profile['source']})
    for folder in sorted((root/'skills').glob('*')):
        if not folder.is_dir() or not (folder/'SKILL.md').is_file():
            continue
        source=safe_path(folder/'SKILL.md',root)
        installed=home/'skills'/folder.name/'SKILL.md'
        text=content(source)
        metadata,_=frontmatter(text)
        interface=yaml_data(content(folder/'agents/openai.yaml')).get('interface',{}) if (folder/'agents/openai.yaml').is_file() else {}
        version=str(metadata.get('metadata',{}).get('version',''))
        source_hash=tree_hash(folder)
        installed_hash=tree_hash(installed.parent) if installed.is_file() and not installed.is_symlink() else None
        children=[]
        for child in sorted(folder.rglob('*')):
            relative=child.relative_to(folder)
            if not child.is_file() or any(part.startswith('.') or part in {'__pycache__','dist','build'} for part in relative.parts):
                continue
            safe_path(child,folder)
            if child==source:
                continue
            readable=child.suffix.lower() in READABLE and child.stat().st_size<=65536
            item={'id':'skill-file:'+folder.name+':'+relative.as_posix(),'kind':'skill-file','name':relative.as_posix(),
                  'parent_id':'skill:'+folder.name,'path':str(child),'size':child.stat().st_size,'readable':readable,
                  'editable':readable and child.suffix.lower() in EDITABLE,'can_sync':False,'state':'來源檔案'}
            children.append(item)
        entries.append({'id':'skill:'+folder.name,'kind':'skill','name':folder.name,'title':interface.get('display_name',folder.name).removesuffix(' (v'+version.removeprefix('v')+')'),
                        'description':metadata['description'],'version':version,
                        'repository':safe_url(metadata.get('metadata',{}).get('repository')),'children':children,
                        'state':'未安裝' if installed_hash is None else '已同步' if source_hash==installed_hash else '內容不同',
                        'path':str(source),'installed_path':str(installed),'editable':True,'can_sync':True})
        entries.extend(children)
    for name,source,target in [('global-instructions',root/'agents/AGENTS.md',home/'AGENTS.md')]:
        if source.is_file():
            entries.append({'id':name,'kind':'agent','name':'Global AGENTS.md','state':'來源文件','path':str(source),'installed_path':str(target),'editable':True,'can_sync':True})
    for name,filename,title in [('subagent-profile','subagents.config.toml','Subagent 預設'),
                                ('git-instructions','git-instructions.toml','Desktop Git 共用指示'),
                                ('desktop-preferences','desktop-preferences.toml','Desktop 與記憶偏好')]:
        source=safe_path(root/'agents'/filename,root)
        if source.is_file():
            entries.append({'id':name,'kind':'agent','name':title,'state':'來源設定' if name=='subagent-profile' else '需合併至本機 config.toml',
                            'path':str(source),'editable':True,'can_sync':name=='subagent-profile',
                            **({'installed_path':str(home/filename)} if name=='subagent-profile' else {})})
    for scope,base in [('user',home),('project',project/'.codex' if project else None)]:
        if base is None:
            continue
        if scope=='project' and (project/'AGENTS.md').is_file():
            entries.append({'id':'project-instructions','kind':'agent','name':'Project AGENTS.md','state':'專案指示','path':str(project/'AGENTS.md'),'editable':True,'can_sync':False})
        for role in sorted((base/'agents').glob('*.toml')):
            safe_path(role,base)
            parsed=tomllib.loads(content(role))
            entries.append({'id':scope+'-role:'+role.stem,'kind':'agent','name':parsed.get('name',role.stem),'description':parsed.get('description',''),
                            'state':'使用者角色' if scope=='user' else '專案角色','path':str(role),'editable':True,'can_sync':False})
    known={entry['name'] for entry in entries if entry['kind']=='skill'}
    for folder in sorted([*(home/'skills').glob('*'),*(home/'skills/.system').glob('*')]):
        if folder.name in known or folder.name.startswith('.') or not (folder/'SKILL.md').is_file():
            continue
        safe_path(folder/'SKILL.md',home)
        builtin=folder.parent.name=='.system'
        try:metadata,_=frontmatter(content(folder/'SKILL.md'))
        except ValueError:metadata={}
        entries.append({'id':('builtin-skill:' if builtin else 'external-skill:')+folder.name,'kind':'skill','name':folder.name,
                        'description':metadata.get('description',''),'version':str(metadata.get('metadata',{}).get('version','')),
                        'repository':safe_url(metadata.get('metadata',{}).get('repository')),
                        'state':'Codex 內建' if builtin else '獨立安裝','protected':True,'readable':True,
                        'path':str(folder/'SKILL.md'),'editable':False,'can_sync':False})
    for entry in entries:
        entry['backup_root']=str(home/'backups'/'codex-setup-manager')
    return entries


def file_plan(entry, text=None, *, sync=False, icons_only=False):
    source=Path(entry['path'])
    if entry.get('protected'):
        raise ValueError('Codex 內建或獨立管理的項目只提供檢視')
    if source.is_symlink():
        raise ValueError('來源使用連結, 請先確認擁有者')
    if sync:
        if not entry.get('can_sync'):
            raise ValueError('這個檔案不使用鏡像同步')
        target=Path(entry['installed_path'])
        after=source.read_bytes()
        if entry['kind']=='skill':
            files={str(p.relative_to(source.parent)):p.read_bytes() for p in source.parent.rglob('*') if p.is_file()
                   and not any(part in {'__pycache__','.git','dist','build','.venv'} or part.endswith('.egg-info') for part in p.relative_to(source.parent).parts)
                   and p.suffix not in {'.pyc','.pyo'}}
            if icons_only:
                files={name:value for name,value in files.items() if name=='agents\\openai.yaml' or name=='agents/openai.yaml' or name.startswith(('assets/','assets\\')) and Path(name).suffix in {'.png','.svg'}}
            present={str(p.relative_to(target.parent)):p.read_bytes() for p in target.parent.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}}
            if icons_only:present={name:value for name,value in present.items() if name in files}
            if present.keys()-files.keys():
                raise ValueError('鏡像含自訂檔案, 請先另存後再同步')
            for name in files:
                safe_path(source.parent/name,source.parent)
                safe_path(target.parent/name,target.parent)
            return {'kind':'skill-tree','name':entry['name'],'path':str(target.parent),'status':'preview',
                    'changed_files':[name for name,value in files.items() if present.get(name)!=value],
                    'changed':files!=present,'_source':source.parent,'_target':target.parent,'_files':files,'_present':present,'_icons_only':icons_only,
                    '_backup_root':Path(entry['backup_root']) if entry.get('backup_root') else None}
    else:
        if not entry.get('editable') or not isinstance(text,str) or len(text.encode('utf-8'))>65536 or '\x00' in text:
            raise ValueError('內容無法安全保存')
        target=source
        after=text.encode('utf-8')
        parsed=parse_document(target,text)
        if entry.get('personal'):
            validate_personal(parsed['data'])
        if target.suffix=='.toml' and entry['kind']=='agent' and entry.get('id') not in {'subagent-profile','git-instructions','desktop-preferences'}:
            role=parsed['data']
            if not all(isinstance(role.get(key),str) and role[key].strip() for key in ('name','description','developer_instructions')):
                raise ValueError('角色需要 name, description 與 developer_instructions')
    if target.is_symlink() or any(p.is_symlink() for p in target.parents):
        raise ValueError('目標使用連結, 請先確認擁有者')
    before=target.read_bytes() if target.is_file() else None
    import difflib
    diff=''.join(difflib.unified_diff((before or b'').decode('utf-8-sig').splitlines(keepends=True),after.decode('utf-8').splitlines(keepends=True),fromfile='before',tofile='after'))
    return {'kind':'file','name':entry['name'],'path':str(target),'status':'preview','changed':after!=before,'diff':diff[:32768],
            '_source':source,'_source_before':source.read_bytes() if source.is_file() else None,'_target':target,'_before':before,'_after':after,
            '_backup_root':Path(entry['backup_root']) if entry.get('backup_root') else None}


def mcp_plan(config, payload):
    before=config.read_bytes() if config.is_file() else None
    text=(before or b'').decode('utf-8-sig')
    parsed=tomllib.loads(text)
    name=payload.get('server')
    if not isinstance(name,str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,80}',name) or name=='node_repl':
        raise ValueError('請選擇可管理的 server 名稱')
    servers=parsed.get('mcp_servers',{})
    action=payload['action']
    if action=='add' and name in servers or action!='add' and name not in servers:
        raise ValueError('註冊名稱已存在或找不到選定 server')
    server=deepcopy(servers.get(name,{}))
    if action in {'enable','disable'}:
        server['enabled']=action=='enable'
    elif action=='remove-registration':
        server=None
    elif action in {'add','edit'}:
        values=payload.get('values')
        allowed={'command','args','url','env_vars','bearer_token_env_var','enabled'}
        if not isinstance(values,dict) or set(values)-allowed:
            raise ValueError('只接受連線與環境變數名稱欄位')
        server.update(values)
        if values.get('url'):
            if not isinstance(values['url'],str):raise ValueError('URL 需要字串')
            server.pop('command',None);server.pop('args',None)
            url=urlsplit(values['url'])
            if url.scheme not in {'https','http'} or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError('請用不含 credentials 或 query 的 HTTP(S) URL')
        elif values.get('command'):
            server.pop('url',None)
            if not isinstance(values['command'],str) or not values['command'].strip() or '\x00' in values['command']:
                raise ValueError('請填可執行檔或指令名稱')
        if ('url' in server)==('command' in server):
            raise ValueError('選擇 HTTP URL 或 stdio command 其中一種')
        if not isinstance(server.get('enabled',True),bool):
            raise ValueError('enabled 需要 boolean')
        for field in ('args','env_vars'):
            if field in server and (not isinstance(server[field],list) or not all(isinstance(x,str) and '\x00' not in x for x in server[field])):
                raise ValueError(field+' 需要字串陣列')
        if any(not name.isidentifier() for name in server.get('env_vars',[])):
            raise ValueError('環境變數需要有效名稱')
        for field in ('bearer_token_env_var',):
            if field in server and (not isinstance(server[field],str) or not server[field].isidentifier()):
                raise ValueError('Token 欄位請填環境變數名稱')
    else:
        raise ValueError('操作不存在')
    after=without_registration(text,name) if name in servers else text
    if server is not None:
        after=after.rstrip()+'\n\n[mcp_servers.'+json.dumps(name)+']\n'
        after+='\n'.join(key+' = '+toml_value(value) for key,value in server.items())+'\n'
    expected=deepcopy(parsed)
    expected.setdefault('mcp_servers',{})
    if server is None: expected['mcp_servers'].pop(name)
    else: expected['mcp_servers'][name]=server
    actual=tomllib.loads(after)
    for d in (expected,actual):
        if not d.get('mcp_servers'):d.pop('mcp_servers',None)
    if actual!=expected:
        raise ValueError('其他設定會變更, 未接受操作')
    public={key:value for key,value in (server or {}).items() if key in {'url','command','args','enabled','env_vars','bearer_token_env_var'}}
    if 'args' in public:
        args=list(public['args'])
        for index,arg in enumerate(args):
            if any(word in arg.lower() for word in ('--token','--api-key','--password','--secret')):
                if '=' in arg:args[index]=arg.split('=',1)[0]+'=[redacted]'
                elif index+1<len(args):args[index+1]='[redacted]'
        public['args']=args
    return {'kind':'registration','server':name,'action':action,'values':public,'path':str(config),'status':'preview',
            '_target':config,'_before':before,'_after':after.encode('utf-8'),'changed':before!=after.encode('utf-8')}


def public_connection(server):
    values={key:server[key] for key in ('command','args','url','enabled','env_vars','bearer_token_env_var') if key in server}
    if 'url' in values:
        url=urlsplit(values['url'])
        if url.username or url.password or url.query:values['url']='[private URL, edit only with a new credential-free endpoint]'
    if 'args' in values:
        args=list(values['args'])
        for index,arg in enumerate(args):
            if isinstance(arg,str) and any(word in arg.lower() for word in ('--token','--api-key','--password','--secret')):
                if '=' in arg:args[index]=arg.split('=',1)[0]+'=[redacted]'
                elif index+1<len(args):args[index+1]='[redacted]'
        values['args']=args
    values['env_names']=list(server.get('env',{}))
    return values


def apply_file(planned):
    target=planned['_target']
    backup_root=planned.get('_backup_root')
    if backup_root:backup_root=backup_root/uuid.uuid4().hex
    if planned['kind']=='skill-tree':
        for name,value in planned['_files'].items():
            if (planned['_source']/name).read_bytes()!=value:
                raise ValueError('Skill 來源已變更, 請重新預覽')
        present={str(p.relative_to(target)):p.read_bytes() for p in target.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}}
        if planned.get('_icons_only'):present={name:value for name,value in present.items() if name in planned['_files']}
        if present!=planned['_present']:
            raise ValueError('Skill 鏡像已變更, 請重新預覽')
        backups=[]
        for name in planned['changed_files']:
            backup=atomic(target/name,planned['_files'][name],present.get(name),backup_root/name if backup_root else None)
            if backup:backups.append(backup)
        return {'status':'applied','changed':planned['changed'],'backups':backups,'reload_required':True}
    if (target.read_bytes() if target.is_file() else None)!=planned['_before']:
        raise ValueError('檔案已變更, 請重新預覽')
    if '_source' in planned and (planned['_source'].read_bytes() if planned['_source'].is_file() else None)!=planned['_source_before']:
        raise ValueError('來源已變更, 請重新預覽')
    backup=atomic(target,planned['_after'],planned['_before'],backup_root/target.name if backup_root else None) if planned['changed'] else None
    return {'status':'applied','changed':planned['changed'],'backup':backup,'reload_required':True}
