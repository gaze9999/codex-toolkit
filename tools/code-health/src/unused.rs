use crate::complexity::{angle_end, method_body};
use crate::lexer::{at, tokenize, Kind, Language, Token};
use crate::module_graph::{self, Graph};
use crate::{Source, SourceId, Span};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

struct Member<'a> {
    class: &'a str,
    name: &'a str,
    index: usize,
    private: bool,
    decorated: bool,
}

fn field_end(tokens: &[Token<'_>], pairs: &[Option<usize>], mut i: usize, end: usize) -> usize {
    while i < end {
        if at(tokens, i) == ";" {
            return i + 1;
        }
        if i > 0
            && tokens[i].line > tokens[i - 1].end_line
            && (matches!(
                at(tokens, i),
                "@" | "public" | "private" | "protected" | "static" | "readonly" | "#"
            ) || (tokens[i].kind == Kind::Word && matches!(at(tokens, i + 1), "=" | ":" | "(")))
        {
            return i;
        }
        i = match at(tokens, i) {
            "(" | "{" | "[" => pairs[i].unwrap_or(i) + 1,
            _ => i + 1,
        };
    }
    i
}

fn members<'a>(tokens: &[Token<'a>], pairs: &[Option<usize>]) -> Vec<Member<'a>> {
    let mut result = Vec::new();
    for (index, token) in tokens
        .iter()
        .enumerate()
        .filter(|(_, token)| token.text == "class")
    {
        let Some(class) = tokens
            .get(index + 1)
            .filter(|token| token.kind == Kind::Word && token.text != "extends")
        else {
            continue;
        };
        let mut body = index + 2;
        while body < tokens.len() && !matches!(at(tokens, body), "{" | ";") {
            body = match at(tokens, body) {
                "<" => angle_end(tokens, body).unwrap_or(body) + 1,
                "(" => pairs[body].unwrap_or(body) + 1,
                _ => body + 1,
            };
        }
        let Some(end) = pairs
            .get(body)
            .copied()
            .flatten()
            .filter(|_| at(tokens, body) == "{")
        else {
            continue;
        };
        let mut i = body + 1;
        while i < end {
            let mut decorated = false;
            while at(tokens, i) == "@" && i + 1 < end {
                decorated = true;
                i += 2;
                while at(tokens, i) == "." {
                    i += 2;
                }
                if at(tokens, i) == "(" {
                    i = pairs[i].unwrap_or(i) + 1;
                }
            }
            let mut private = false;
            while matches!(
                at(tokens, i),
                "public"
                    | "private"
                    | "protected"
                    | "static"
                    | "readonly"
                    | "override"
                    | "abstract"
                    | "declare"
                    | "async"
                    | "get"
                    | "set"
                    | "#"
                    | "*"
            ) && !matches!(at(tokens, i + 1), "(" | ":" | "=" | ";" | "?")
            {
                private |= matches!(at(tokens, i), "private" | "#");
                i += 1;
            }
            if matches!(at(tokens, i), "{" | "[") {
                i = pairs[i].unwrap_or(i) + 1;
                continue;
            }
            if i >= end || tokens[i].kind != Kind::Word {
                i += 1;
                continue;
            }
            let name = tokens[i].text;
            let start = i;
            let mut next = i + 1;
            if matches!(at(tokens, next), "?" | "!") {
                next += 1;
            }
            if at(tokens, next) == "<" {
                next = angle_end(tokens, next).map_or(next, |end| end + 1);
            }
            let method = at(tokens, next) == "(";
            if name != "constructor"
                && (method || matches!(at(tokens, next), "=" | ":" | ";" | "}"))
            {
                result.push(Member {
                    class: class.text,
                    name,
                    index: start,
                    private,
                    decorated,
                });
            }
            i = if method {
                method_body(tokens, pairs, next)
                    .and_then(|body| pairs[body])
                    .map_or_else(|| field_end(tokens, pairs, next, end), |end| end + 1)
            } else if matches!(at(tokens, next), "=" | ":") {
                field_end(tokens, pairs, next, end)
            } else {
                next.max(i + 1)
            };
        }
        let _ = token;
    }
    result
}

fn expression_words<'a>(expression: &'a str, names: &mut BTreeSet<String>) {
    names.extend(
        tokenize(expression, Language::Script)
            .into_iter()
            .filter(|token| token.kind == Kind::Word)
            .map(|token| token.text.to_owned()),
    );
}

fn template_words(source: &str, names: &mut BTreeSet<String>) {
    let tokens = tokenize(source, Language::Html);
    for (index, token) in tokens.iter().enumerate() {
        if token.kind == Kind::String
            && index >= 2
            && at(&tokens, index - 1) == "="
            && (matches!(at(&tokens, index - 2), "]" | ")")
                || (index >= 3 && at(&tokens, index - 3) == "*")
                || at(&tokens, index - 2).starts_with("bind"))
        {
            if let Some(expression) = token.string() {
                expression_words(expression, names);
            }
        }
    }
    for fragment in source.split("{{").skip(1) {
        if let Some((expression, _)) = fragment.split_once("}}") {
            expression_words(expression, names);
        }
    }
    for tag in ["@if", "@for", "@switch", "@case", "@let", "@defer"] {
        for block in source.split(tag).skip(1) {
            let expression = tokenize(block.trim_start(), Language::Script);
            if at(&expression, 0) == "(" {
                let pairs = crate::lexer::pairs(&expression);
                if let Some(end) = pairs[0] {
                    names.extend(
                        expression[..end]
                            .iter()
                            .filter(|token| token.kind == Kind::Word)
                            .map(|token| token.text.to_owned()),
                    );
                }
            } else if tag == "@let" {
                expression_words(block.split(';').next().unwrap_or_default(), names);
            }
        }
    }
}

fn templates(
    source: &Source,
    tokens: &[Token<'_>],
    sources: &[Source],
    paths: &BTreeMap<PathBuf, SourceId>,
) -> (BTreeSet<String>, bool) {
    let mut names = BTreeSet::new();
    let mut incomplete = false;
    for extension in ["html", "htm"] {
        if let Some(&id) = paths.get(&source.path.with_extension(extension)) {
            template_words(&sources[id].text, &mut names);
        }
    }
    for (index, token) in tokens.iter().enumerate() {
        if !matches!(token.text, "template" | "templateUrl") || at(tokens, index + 1) != ":" {
            continue;
        }
        let Some(value) = tokens.get(index + 2) else {
            continue;
        };
        if token.text == "template" {
            if value.kind == Kind::Template && value.text.len() >= 2 && value.text.ends_with('`') {
                let raw = &value.text[1..value.text.len() - 1];
                template_words(raw, &mut names);
                incomplete |= raw.contains("${");
            } else if let Some(raw) = value.string() {
                template_words(raw, &mut names);
            } else {
                incomplete = true;
            }
        } else if let Some(name) = value.string() {
            let file = source.path.parent().unwrap_or(Path::new("")).join(name);
            if let Some(id) = module_graph::normalize(&file).and_then(|path| paths.get(&path)) {
                template_words(&sources[*id].text, &mut names);
            } else {
                incomplete = true;
            }
        } else {
            incomplete = true;
        }
    }
    (names, incomplete)
}

fn property_names<'a>(
    tokens: &[Token<'a>],
    mut visit: impl FnMut(&'a str, Option<&'a str>),
) -> bool {
    let mut computed = false;
    for (i, token) in tokens.iter().enumerate() {
        let receiver = i
            .checked_sub(1)
            .and_then(|index| tokens.get(index))
            .filter(|t| t.kind == Kind::Word)
            .map(|t| t.text);
        if matches!(token.text, "." | "?.") {
            let next = i + if at(tokens, i + 1) == "#" { 2 } else { 1 };
            if let Some(property) = tokens.get(next).filter(|t| t.kind == Kind::Word) {
                visit(property.text, receiver);
            }
        } else if token.text == "[" && receiver.is_some() {
            if at(tokens, i + 2) == "]" {
                if let Some(name) = tokens.get(i + 1).and_then(|t| t.string()) {
                    visit(name, receiver);
                    continue;
                }
            }
            computed |= receiver == Some("this");
        }
        computed |= token.text == "Reflect" && at(tokens, i + 1) == ".";
    }
    computed
}

pub fn find(
    sources: &[Source],
    tokens: &[Vec<Token<'_>>],
    delimiters: &[Vec<Option<usize>>],
    paths: &BTreeMap<PathBuf, SourceId>,
    graph: &Graph<'_>,
    retained: &[Vec<Span>],
    incomplete: bool,
) -> (Vec<Value>, Vec<Value>) {
    let mut candidates = Vec::new();
    let mut review = Vec::new();
    let uncertain_graph = incomplete
        || graph.modules.iter().any(|module| module.unknown_path)
        || graph
            .unresolved
            .iter()
            .any(|(id, _, _)| graph.reachable.contains(id));
    let mut external = BTreeMap::<&str, BTreeSet<SourceId>>::new();
    for (id, file) in tokens.iter().enumerate() {
        property_names(file, |name, _| {
            external.entry(name).or_default().insert(id);
        });
    }
    for (id, source) in sources
        .iter()
        .enumerate()
        .filter(|(_, source)| source.language == Language::Script)
    {
        let module = &graph.modules[id];
        let covered = |line| retained[id].iter().any(|span| span.intersects(line, line));
        let keep_file = retained[id]
            .iter()
            .any(|span| span.end_line == usize::MAX && span.start_line == 1);
        if keep_file {
            continue;
        }
        let path = &source.path;
        let file_known = !graph.entries.is_empty() && !uncertain_graph && !module.decorated;
        if !graph.reachable.contains(&id) && !source.path.to_string_lossy().ends_with(".d.ts") {
            if file_known && retained[id].is_empty() {
                candidates.push(json!({"kind":"file","path":path,"line":1,"name":"","evidence":"Unreachable from the selected entry points"}));
            } else {
                review.push(json!({"path":path,"line":1,"reason":"File reachability is unconfirmed under the selected graph or retention scope"}));
            }
        }
        for export in &module.exports {
            let line = tokens[id][export.index].line;
            if covered(line) || export.name == "*" || graph.used(id, export.name) {
                continue;
            }
            if !file_known {
                review.push(json!({"path":path,"line":line,"symbol":export.name,"reason":"Export use is unconfirmed under the selected graph or registration model"}));
                continue;
            }
            let local_uses = !export.local.is_empty()
                && export.from.is_none()
                && tokens[id].iter().enumerate().any(|(i, t)| {
                    let previous = i.checked_sub(1).map(|previous| at(&tokens[id], previous));
                    t.kind == Kind::Word
                        && t.text == export.local
                        && i != export.index
                        && !matches!(
                            previous,
                            Some(
                                "const"
                                    | "let"
                                    | "var"
                                    | "function"
                                    | "class"
                                    | "type"
                                    | "interface"
                                    | "enum"
                                    | "namespace"
                                    | "as"
                            )
                        )
                });
            candidates.push(json!({"kind":"export","path":path,"line":line,"name":export.name,"local_use":local_uses,
                "evidence":if local_uses {"Local occurrence found, no importing consumer in scope"} else {"No importing consumer in scope"}}));
        }
        let members = members(&tokens[id], &delimiters[id]);
        if members.is_empty() {
            continue;
        }
        let (template, missing_template) = templates(source, &tokens[id], sources, paths);
        let mut local = BTreeSet::new();
        let computed = property_names(&tokens[id], |name, _| {
            local.insert(name);
        });
        let mut checked = BTreeSet::new();
        for member in members {
            let line = tokens[id][member.index].line;
            if !checked.insert((member.class, member.name))
                || covered(line)
                || local.contains(member.name)
                || template.contains(member.name)
            {
                continue;
            }
            if !member.private
                && external
                    .get(member.name)
                    .is_some_and(|files| files.iter().any(|&file| file != id))
            {
                continue;
            }
            if member.decorated
                || computed
                || missing_template
                || (module.decorated && !member.private)
                || (!member.private && incomplete)
            {
                review.push(json!({"path":path,"line":line,"symbol":member.name,"reason":"Template, decorator, reflection or out-of-scope callers require manual confirmation"}));
            } else {
                candidates.push(json!({"kind":"member","path":path,"line":line,"name":member.name,"class":member.class,
                    "visibility":if member.private {"private"} else {"non-private"},"evidence":"No literal property or paired-template reference in scope"}));
            }
        }
    }
    (candidates, review)
}
