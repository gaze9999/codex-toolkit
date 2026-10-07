"""Parse bounded documents and render Markdown without active HTML or remote images."""
import ast
import html
import json
from pathlib import Path
import tomllib
from urllib.parse import urlsplit
if __package__:
    from .skill_versions import VERSION
else:
    from skill_versions import VERSION

EDITABLE = {'.md', '.txt', '.rst', '.json', '.toml', '.yaml', '.yml'}
READABLE = EDITABLE | {'.py', '.sh', '.ps1', '.cmd', '.csv', '.ini'}


def safe_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    return value if parsed.scheme in {'http', 'https'} and parsed.hostname and not parsed.username and not parsed.password else None


def yaml_data(text):
    import yaml
    # Alias expansion and duplicate keys are inappropriate for small configuration files.
    if any(isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)) for token in yaml.scan(text)):
        raise ValueError('YAML 請直接列出欄位, 不使用 anchor 或 alias')
    class Loader(yaml.SafeLoader):
        pass
    def mapping(loader, node):
        pairs = loader.construct_pairs(node)
        result = {}
        for key, value in pairs:
            if not isinstance(key, str) or key in result:
                raise ValueError('YAML 欄位名稱必須是唯一字串')
            result[key] = value
        return result
    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    try:
        return yaml.load(text, Loader=Loader)
    except (yaml.YAMLError, RecursionError) as error:
        raise ValueError('YAML 格式無法解析') from error


def frontmatter(text):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != '---':
        raise ValueError('Skill 需要 YAML metadata')
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == '---'), None)
    if end is None:
        raise ValueError('YAML metadata 缺少結束標記')
    data = yaml_data(''.join(lines[1:end]))
    if not isinstance(data, dict) or not all(isinstance(data.get(k), str) and data[k].strip() for k in ('name', 'description')):
        raise ValueError('Skill 需要 name 與 description')
    metadata = data.get('metadata', {})
    if not isinstance(metadata, dict):
        raise ValueError('Skill metadata 需要使用欄位格式')
    version = metadata.get('version')
    if version is not None and (not isinstance(version, str) or not VERSION.fullmatch(version)):
        raise ValueError('Skill 版本需要使用 SemVer, 例如 1.2.3 或 1.2.3-rc.1')
    return data, ''.join(lines[end + 1:])


def parse_document(path, text):
    if len(text.encode('utf-8')) > 65536 or '\x00' in text:
        raise ValueError('文件超過 64 KiB 或含無效字元')
    suffix = Path(path).suffix.lower()
    parser = {'.md': 'Markdown', '.json': 'JSON', '.toml': 'TOML', '.yaml': 'YAML', '.yml': 'YAML', '.py': 'Python AST'}.get(suffix, '純文字')
    body = text
    data = None
    if Path(path).name == 'SKILL.md':
        data, body = frontmatter(text)
    elif suffix == '.json':
        data = json.loads(text)
    elif suffix == '.toml':
        data = tomllib.loads(text)
    elif suffix in {'.yaml', '.yml'}:
        data = yaml_data(text)
    elif suffix == '.py':
        ast.parse(text)
    elif Path(path).name.startswith('requirements') and suffix == '.txt':
        from packaging.requirements import Requirement
        parser = 'Python requirements'
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                # Preserve pip options/includes as text; validate ordinary PEP 508 entries.
                if not line.startswith('-'):
                    Requirement(line.split(' #', 1)[0])
    rendered = ''
    if suffix == '.md':
        from markdown_it import MarkdownIt
        md = MarkdownIt('commonmark', {'html': False}).enable('table')
        md.renderer.rules['image'] = lambda tokens, i, *args: html.escape('[圖片: ' + tokens[i].content + ']')
        rendered = md.render(body)
    return {'parser': parser, 'html': rendered, 'valid': True, 'data': data}


def document_view(path, text):
    try:
        result = parse_document(path, text)
        return {k: v for k, v in result.items() if k != 'data'}
    except (ValueError, SyntaxError, TypeError, RecursionError) as error:
        return {'parser': Path(path).suffix.lstrip('.').upper() or '純文字', 'html': '', 'valid': False, 'error': str(error)[:500]}


def personal_text(path):
    return path.read_text(encoding='utf-8') if path.is_file() else json.dumps(dict.fromkeys(('custom_instructions', 'nickname', 'occupation', 'about'), ''), ensure_ascii=False, indent=2)


def validate_personal(data):
    limits = {'custom_instructions': 5000, 'nickname': 200, 'occupation': 500, 'about': 5000}
    if not isinstance(data, dict) or set(data) != set(limits) or any(not isinstance(data[k], str) or len(data[k]) > limit for k, limit in limits.items()):
        raise ValueError('請確認自訂指示與個人資訊欄位及字元數')
