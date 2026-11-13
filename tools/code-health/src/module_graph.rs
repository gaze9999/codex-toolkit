use crate::lexer::{at, Kind, Token};
use crate::{Source, SourceId};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::path::{Component, Path, PathBuf};

#[derive(Debug)]
pub struct Module<'a> {
    pub imports: Vec<Import<'a>>,
    pub exports: Vec<Export<'a>>,
    pub review: Vec<(usize, &'static str)>,
    pub unknown_path: bool,
    pub decorated: bool,
}

#[derive(Debug)]
pub struct Import<'a> {
    pub path: &'a str,
    pub line: usize,
    pub names: Vec<&'a str>,
}

#[derive(Debug)]
pub struct Export<'a> {
    pub name: &'a str,
    pub local: &'a str,
    pub index: usize,
    pub line: usize,
    pub from: Option<&'a str>,
}

fn named(tokens: &[Token<'_>], start: usize, end: usize, type_only: bool) -> Vec<(usize, usize)> {
    let mut names = Vec::new();
    let mut i = start;
    while i < end {
        if type_only
            && at(tokens, i) == "type"
            && tokens
                .get(i + 1)
                .is_some_and(|t| t.kind == Kind::Word && t.text != "as")
        {
            i += 1;
        }
        if tokens[i].kind == Kind::Word || tokens[i].kind == Kind::String {
            let alias = if at(tokens, i + 1) == "as" && i + 2 < end {
                i + 2
            } else {
                i
            };
            names.push((i, alias));
            i = alias;
        }
        i += 1;
    }
    names
}

fn from_at<'a>(tokens: &[Token<'a>], index: usize) -> Option<&'a str> {
    (at(tokens, index) == "from")
        .then(|| tokens.get(index + 1)?.string())
        .flatten()
}

fn import_clause<'a>(
    tokens: &[Token<'a>],
    pairs: &[Option<usize>],
    index: usize,
) -> Option<Import<'a>> {
    let line = tokens[index].line;
    let mut i = index + 1;
    let mut names = Vec::new();
    if let Some(path) = tokens.get(i)?.string() {
        return Some(Import { path, line, names });
    }
    if at(tokens, i) == "type" && !matches!(at(tokens, i + 1), "from" | ",") {
        i += 1;
    }
    if tokens.get(i)?.kind == Kind::Word {
        names.push("default");
        i += 1;
        if at(tokens, i) == "," {
            i += 1;
        }
    }
    match at(tokens, i) {
        "*" if at(tokens, i + 1) == "as" => {
            names.push("*");
            i += 3;
        }
        "{" => {
            let end = pairs[i]?;
            names.extend(
                named(tokens, i + 1, end, true)
                    .into_iter()
                    .map(|(name, _)| tokens[name].text.trim_matches(['\'', '"'])),
            );
            i = end + 1;
        }
        _ => {}
    }
    Some(Import {
        path: from_at(tokens, i)?,
        line,
        names,
    })
}

fn export_clause<'a>(
    tokens: &[Token<'a>],
    pairs: &[Option<usize>],
    index: usize,
    exports: &mut Vec<Export<'a>>,
) -> Option<()> {
    let mut i = index + 1;
    if at(tokens, i) == "type" && matches!(at(tokens, i + 1), "{" | "*") {
        i += 1;
    }
    match at(tokens, i) {
        "default" => exports.push(Export {
            name: "default",
            local: "",
            index: i,
            line: tokens[i].line,
            from: None,
        }),
        "*" => {
            let alias = if at(tokens, i + 1) == "as" { i + 2 } else { i };
            exports.push(Export {
                name: at(tokens, alias),
                local: "*",
                index: i,
                line: tokens[i].line,
                from: Some(from_at(tokens, alias + 1)?),
            });
        }
        "{" => {
            let end = pairs[i]?;
            let from = from_at(tokens, end + 1);
            for (local, alias) in named(tokens, i + 1, end, true) {
                exports.push(Export {
                    name: tokens[alias].text.trim_matches(['\'', '"']),
                    local: tokens[local].text.trim_matches(['\'', '"']),
                    index: local,
                    line: tokens[local].line,
                    from,
                });
            }
        }
        _ => {
            while matches!(at(tokens, i), "abstract" | "async" | "declare") {
                i += 1;
            }
            let declaration = at(tokens, i);
            if !matches!(
                declaration,
                "function"
                    | "class"
                    | "const"
                    | "let"
                    | "var"
                    | "interface"
                    | "enum"
                    | "namespace"
                    | "type"
            ) {
                return None;
            }
            i += 1;
            if at(tokens, i) == "*" {
                i += 1;
            }
            loop {
                if tokens.get(i)?.kind != Kind::Word {
                    return None;
                }
                exports.push(Export {
                    name: tokens[i].text,
                    local: tokens[i].text,
                    index: i,
                    line: tokens[i].line,
                    from: None,
                });
                if !matches!(declaration, "const" | "let" | "var") {
                    break;
                }
                let line = tokens[i].line;
                i += 1;
                while i < tokens.len() {
                    if matches!(tokens[i].text, "," | ";" | "export")
                        || (tokens[i].line > line
                            && matches!(tokens[i].text, "const" | "let" | "var" | "import"))
                    {
                        break;
                    }
                    i = match tokens[i].text {
                        "(" | "[" | "{" => pairs[i].map_or(i + 1, |end| end + 1),
                        _ => i + 1,
                    };
                }
                if at(tokens, i) != "," {
                    break;
                }
                i += 1;
            }
        }
    }
    Some(())
}

fn loader_call<'a>(tokens: &[Token<'a>], pairs: &[Option<usize>], index: usize) -> Option<&'a str> {
    let end = pairs.get(index + 1).copied().flatten()?;
    if end == index + 3 || (at(tokens, index) == "import" && at(tokens, index + 3) == ",") {
        return tokens.get(index + 2)?.string();
    }
    None
}

pub fn parse<'a>(tokens: &[Token<'a>], pairs: &[Option<usize>]) -> Module<'a> {
    let mut module = Module {
        imports: Vec::new(),
        exports: Vec::new(),
        review: Vec::new(),
        unknown_path: false,
        decorated: false,
    };
    let mut block_end = None;
    for (i, token) in tokens.iter().enumerate() {
        let at_top = block_end.is_none_or(|end| i > end);
        if at_top && token.text == "{" {
            block_end = pairs[i];
        }
        if token.text == "@"
            && tokens.get(i + 1).is_some_and(|t| t.kind == Kind::Word)
            && !module.decorated
        {
            module.decorated = true;
            module.review.push((
                token.line,
                "Decorator registration or reflective consumers require manual confirmation",
            ));
        }
        if matches!(token.text, "import" | "require")
            && at(tokens, i + 1) == "("
            && (i == 0 || !matches!(at(tokens, i - 1), "." | "?."))
        {
            let path = loader_call(tokens, pairs, i);
            if let Some(path) = path {
                module.imports.push(Import {
                    path,
                    line: token.line,
                    names: vec!["*"],
                });
            } else {
                module.unknown_path = true;
            }
            if token.text == "import" || path.is_none() {
                module.review.push((
                    token.line,
                    "Dynamic module loading requires manual confirmation",
                ));
            }
        } else if at_top && token.text == "import" && at(tokens, i + 1) != "." {
            if let Some(import) = import_clause(tokens, pairs, i) {
                module.imports.push(import);
            } else if !matches!(at(tokens, i + 1), "(" | "=")
                && !tokens
                    .iter()
                    .skip(i + 1)
                    .take(4)
                    .any(|t| t.text == "require")
            {
                module.unknown_path = true;
                module.review.push((
                    token.line,
                    "Import clause could not be resolved syntactically",
                ));
            }
        } else if at_top
            && token.text == "export"
            && at(tokens, i + 1) != "="
            && export_clause(tokens, pairs, i, &mut module.exports).is_none()
        {
            module.review.push((
                token.line,
                "Export clause could not be resolved syntactically",
            ));
        }
        if (token.text == "module" && at(tokens, i + 1) == "." && at(tokens, i + 2) == "exports")
            || (token.text == "exports" && at(tokens, i + 1) == ".")
        {
            if !module
                .review
                .iter()
                .any(|(_, note)| *note == "CommonJS export shape requires manual confirmation")
            {
                module.review.push((
                    token.line,
                    "CommonJS export shape requires manual confirmation",
                ));
            }
        }
    }
    module
}

#[derive(Clone, Debug, Default)]
pub struct Settings {
    pub base: Option<PathBuf>,
    pub aliases: BTreeMap<String, Vec<PathBuf>>,
    pub entries: Vec<PathBuf>,
}

pub fn jsonc(source: &str) -> Result<Value, serde_json::Error> {
    let bytes = source.trim_start_matches('\u{feff}').as_bytes();
    let mut clean = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        let start = i;
        match &bytes[i..] {
            [b'"', ..] => {
                i += 1;
                while i < bytes.len() {
                    let next = bytes[i];
                    i += 1;
                    if next == b'"' {
                        break;
                    }
                    if next == b'\\' && i < bytes.len() {
                        i += 1;
                    }
                }
                clean.extend_from_slice(&bytes[start..i]);
            }
            [b'/', b'/', ..] => {
                i += 2;
                while i < bytes.len() && bytes[i] != b'\n' {
                    i += 1;
                }
                clean.push(b' ');
            }
            [b'/', b'*', ..] => {
                i += 2;
                while i + 1 < bytes.len() && bytes[i..i + 2] != *b"*/" {
                    i += 1;
                }
                if i + 1 == bytes.len() {
                    return serde_json::from_slice(bytes);
                }
                i += 2;
                clean.push(b' ');
            }
            [b'}' | b']', ..] => {
                if let Some(last) = clean.iter().rposition(|b| !b.is_ascii_whitespace()) {
                    if clean[last] == b',' {
                        clean[last] = b' ';
                    }
                }
                clean.push(bytes[i]);
                i += 1;
            }
            _ => {
                clean.push(bytes[i]);
                i += 1;
            }
        }
    }
    serde_json::from_slice(&clean)
}

pub fn normalize(path: &Path) -> Option<PathBuf> {
    let mut result = PathBuf::new();
    for part in path.components() {
        match part {
            Component::CurDir => {}
            Component::ParentDir => {
                if !result.pop() {
                    return None;
                }
            }
            _ => result.push(part),
        }
    }
    Some(result)
}

pub fn settings(
    path: &Path,
    configs: &BTreeMap<PathBuf, Value>,
    seen: &mut BTreeSet<PathBuf>,
    issues: &mut BTreeSet<PathBuf>,
) -> Settings {
    if !seen.insert(path.to_owned()) {
        issues.insert(path.to_owned());
        return Settings::default();
    }
    let value = &configs[path];
    let directory = path.parent().unwrap_or(Path::new(""));
    let mut result = Settings::default();
    for base in value["extends"].as_str().into_iter().chain(
        value["extends"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str),
    ) {
        let Some(base) = normalize(&directory.join(base)) else {
            issues.insert(path.to_owned());
            continue;
        };
        let json = base.with_file_name(format!(
            "{}.json",
            base.file_name().unwrap_or_default().to_string_lossy()
        ));
        let nested = base.join("tsconfig.json");
        let inherited_path = [&base, &json, &nested]
            .into_iter()
            .find(|candidate| configs.contains_key(*candidate));
        if let Some(base) = inherited_path {
            let inherited = settings(base, configs, seen, issues);
            if inherited.base.is_some() {
                result.base = inherited.base;
            }
            if !inherited.aliases.is_empty() {
                result.aliases = inherited.aliases;
            }
            if !inherited.entries.is_empty() {
                result.entries = inherited.entries;
            }
        } else {
            issues.insert(path.to_owned());
        }
    }
    if let Some(base) = value["compilerOptions"]["baseUrl"].as_str() {
        result.base = normalize(&directory.join(base));
    }
    if let Some(aliases) = value["compilerOptions"]["paths"].as_object() {
        let base = result.base.as_deref().unwrap_or(directory);
        result.aliases = aliases
            .iter()
            .map(|(key, targets)| {
                (
                    key.clone(),
                    targets
                        .as_array()
                        .into_iter()
                        .flatten()
                        .filter_map(Value::as_str)
                        .map(|target| base.join(target))
                        .collect(),
                )
            })
            .collect();
    }
    if let Some(files) = value["files"].as_array() {
        result.entries = files
            .iter()
            .filter_map(Value::as_str)
            .filter_map(|name| normalize(&directory.join(name)))
            .collect();
    }
    seen.remove(path);
    result
}

pub fn project_entries(path: &Path, value: &Value) -> Vec<PathBuf> {
    let mut names = Vec::new();
    for key in ["main", "browser"] {
        names.extend(value[key].as_str());
        for target in value["targets"]
            .as_object()
            .into_iter()
            .flat_map(|targets| targets.values())
        {
            names.extend(target["options"][key].as_str());
            if let Some(configs) = target["configurations"].as_object() {
                names.extend(configs.values().filter_map(|config| config[key].as_str()));
            }
        }
    }
    names
        .into_iter()
        .flat_map(|name| {
            [
                normalize(Path::new(name)),
                normalize(&path.parent().unwrap_or(Path::new("")).join(name)),
            ]
            .into_iter()
            .flatten()
        })
        .collect()
}

const SCRIPT_EXTENSIONS: &[&str] = &["ts", "tsx", "mts", "cts", "js", "jsx", "mjs", "cjs"];

fn resolve_path(path: &Path, sources: &BTreeMap<PathBuf, SourceId>) -> Option<SourceId> {
    let path = normalize(path)?;
    if let Some(id) = sources.get(&path) {
        return Some(*id);
    }
    let ext = path.extension().and_then(|ext| ext.to_str()).unwrap_or("");
    let remap: &[&str] = match ext {
        "js" => &["ts", "tsx"],
        "jsx" => &["tsx"],
        "mjs" => &["mts"],
        "cjs" => &["cts"],
        _ => &[],
    };
    for ext in remap {
        if let Some(id) = sources.get(&path.with_extension(ext)) {
            return Some(*id);
        }
    }
    for ext in SCRIPT_EXTENSIONS {
        if let Some(name) = path.file_name() {
            let name = format!("{}.{ext}", name.to_string_lossy());
            if let Some(id) = sources.get(&path.with_file_name(name)) {
                return Some(*id);
            }
        }
        if let Some(id) = sources.get(&path.join(format!("index.{ext}"))) {
            return Some(*id);
        }
    }
    None
}

pub fn resolve_entry(path: &Path, sources: &BTreeMap<PathBuf, SourceId>) -> Option<SourceId> {
    resolve_path(path, sources)
}

fn alias_match<'a>(pattern: &str, name: &'a str) -> Option<&'a str> {
    if let Some((start, end)) = pattern.split_once('*') {
        return name.strip_prefix(start)?.strip_suffix(end);
    }
    (pattern == name).then_some("")
}

fn resolve(
    from: &Path,
    name: &str,
    config: &Settings,
    paths: &BTreeMap<PathBuf, SourceId>,
) -> (Option<SourceId>, bool) {
    if name.starts_with("./") || name.starts_with("../") {
        return (
            resolve_path(&from.parent().unwrap_or(Path::new("")).join(name), paths),
            true,
        );
    }
    let alias = config
        .aliases
        .iter()
        .filter_map(|(pattern, values)| Some((pattern, values, alias_match(pattern, name)?)))
        .max_by_key(|(pattern, _, _)| {
            (
                !pattern.contains('*'),
                pattern.split('*').next().unwrap_or("").len(),
            )
        });
    if let Some((_, targets, capture)) = alias {
        return (
            targets.iter().find_map(|target| {
                resolve_path(
                    Path::new(&target.to_string_lossy().replace('*', capture)),
                    paths,
                )
            }),
            true,
        );
    }
    let resolved = config
        .base
        .as_ref()
        .and_then(|base| resolve_path(&base.join(name), paths));
    (resolved, false)
}

pub struct Graph<'a> {
    pub modules: Vec<Module<'a>>,
    pub entries: BTreeSet<SourceId>,
    pub edges: Vec<BTreeMap<&'a str, SourceId>>,
    pub reachable: BTreeSet<SourceId>,
    pub consumed: BTreeSet<(SourceId, &'a str)>,
    pub unresolved: Vec<(SourceId, usize, &'a str)>,
}

impl<'a> Graph<'a> {
    pub fn build(
        sources: &[Source],
        modules: Vec<Module<'a>>,
        settings: &BTreeMap<PathBuf, Settings>,
        paths: &BTreeMap<PathBuf, SourceId>,
        entries: BTreeSet<SourceId>,
    ) -> Self {
        let empty = Settings::default();
        let mut edges = vec![BTreeMap::new(); sources.len()];
        let mut unresolved = Vec::new();
        for (id, module) in modules.iter().enumerate() {
            let path = &sources[id].path;
            let config = path
                .ancestors()
                .skip(1)
                .find_map(|dir| settings.get(dir))
                .unwrap_or(&empty);
            for (name, line) in module.imports.iter().map(|i| (i.path, i.line)).chain(
                module
                    .exports
                    .iter()
                    .filter_map(|e| Some((e.from?, e.line))),
            ) {
                let (resolved, local) = resolve(path, name, config, paths);
                if let Some(target) = resolved {
                    edges[id].insert(name, target);
                } else if local {
                    unresolved.push((id, line, name));
                }
            }
        }
        let mut reachable = entries.clone();
        let mut queue: VecDeque<_> = entries.iter().copied().collect();
        while let Some(id) = queue.pop_front() {
            for target in edges[id].values() {
                if reachable.insert(*target) {
                    queue.push_back(*target);
                }
            }
        }
        let mut graph = Self {
            modules,
            entries,
            edges,
            reachable,
            consumed: BTreeSet::new(),
            unresolved,
        };
        graph.trace_usage();
        graph
    }

    fn trace_usage(&mut self) {
        let mut queue = VecDeque::new();
        for (id, module) in self.modules.iter().enumerate() {
            if self.entries.contains(&id) {
                queue.push_back((id, "*"));
            }
            for import in &module.imports {
                if let Some(target) = self.edges[id].get(import.path) {
                    queue.extend(import.names.iter().map(|name| (*target, *name)));
                }
            }
        }
        while let Some((id, name)) = queue.pop_front() {
            if !self.consumed.insert((id, name)) {
                continue;
            }
            let module = &self.modules[id];
            let explicit = module
                .exports
                .iter()
                .any(|e| e.name == name && e.name != "*");
            for export in &module.exports {
                let Some(target) = export
                    .from
                    .and_then(|from| self.edges[id].get(from))
                    .copied()
                else {
                    continue;
                };
                if export.name == "*" && (name == "*" || (!explicit && name != "default")) {
                    queue.push_back((target, if name == "*" { "*barrel" } else { name }));
                } else if export.name == name
                    || name == "*"
                    || (name == "*barrel" && export.name != "default" && export.name != "*")
                {
                    queue.push_back((target, export.local));
                } else if name == "*barrel" && export.name == "*" {
                    queue.push_back((target, "*barrel"));
                }
            }
        }
    }

    pub fn used(&self, id: SourceId, name: &str) -> bool {
        self.consumed.contains(&(id, name))
            || self.consumed.contains(&(id, "*"))
            || (name != "default" && self.consumed.contains(&(id, "*barrel")))
    }
}
