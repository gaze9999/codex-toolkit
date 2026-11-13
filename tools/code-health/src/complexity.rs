use crate::lexer::{at, keyword, Kind, Token};
use std::collections::BTreeMap;

#[derive(Clone, Debug)]
pub struct Function<'a> {
    pub name: &'a str,
    pub start: usize,
    pub body: usize,
    pub end: usize,
}

pub fn angle_end(tokens: &[Token<'_>], start: usize) -> Option<usize> {
    let mut level = 0;
    for i in start..tokens.len() {
        match tokens[i].text {
            "<" => level += 1,
            ">" => {
                level -= 1;
                if level == 0 {
                    return Some(i);
                }
            }
            ";" => return None,
            _ => {}
        }
    }
    None
}

pub fn method_body(tokens: &[Token<'_>], pairs: &[Option<usize>], paren: usize) -> Option<usize> {
    let mut next = pairs.get(paren).copied().flatten()? + 1;
    if at(tokens, next) == ":" {
        next += 1;
        if at(tokens, next) == "{" {
            next = pairs[next]? + 1;
        }
        while next < tokens.len() {
            match at(tokens, next) {
                "{" => break,
                "=" | "=>" | ";" | "," | "}" | ")" => return None,
                "<" => next = angle_end(tokens, next)? + 1,
                "(" | "[" => next = pairs[next]? + 1,
                _ => next += 1,
            }
        }
    }
    (at(tokens, next) == "{" && pairs[next].is_some()).then_some(next)
}

fn expression_end(tokens: &[Token<'_>], pairs: &[Option<usize>], mut i: usize) -> usize {
    let first = i;
    while let Some(token) = tokens.get(i) {
        match token.text {
            ";" | "," | ")" | "]" | "}" => break,
            "const" | "let" | "return" | "export" | "import"
                if i > first && token.line > tokens[i - 1].end_line =>
            {
                break
            }
            "(" | "[" | "{" => i = pairs[i].unwrap_or(i) + 1,
            _ => i += 1,
        }
    }
    i.saturating_sub(1).max(first)
}

fn arrow_name<'a>(tokens: &[Token<'a>], pairs: &[Option<usize>], arrow: usize) -> (usize, &'a str) {
    let mut start = arrow.saturating_sub(1);
    if at(tokens, start) == ")" {
        start = pairs[start].unwrap_or(start);
    }
    if start > 0 && at(tokens, start - 1) == "async" {
        start -= 1;
    }
    if start >= 2 && at(tokens, start - 1) == "=" && tokens[start - 2].kind == Kind::Word {
        return (start - 2, tokens[start - 2].text);
    }
    (start, "<arrow>")
}

pub fn functions<'a>(tokens: &[Token<'a>], pairs: &[Option<usize>]) -> Vec<Function<'a>> {
    let mut results = BTreeMap::new();
    for (i, token) in tokens.iter().enumerate() {
        let mut name = token.text;
        let mut start = i;
        let body = if token.text == "=>" && tokens.get(i + 1).is_some() {
            (start, name) = arrow_name(tokens, pairs, i);
            let body = i + 1;
            let end = if at(tokens, body) == "{" {
                pairs[body].unwrap_or(body)
            } else {
                expression_end(tokens, pairs, body)
            };
            results.entry(body).or_insert(Function {
                name,
                start,
                body,
                end,
            });
            continue;
        } else if token.text == "function" {
            let mut next = i + 1;
            if at(tokens, next) == "*" {
                next += 1;
            }
            name = "<function>";
            if tokens
                .get(next)
                .is_some_and(|token| token.kind == Kind::Word)
            {
                name = at(tokens, next);
                next += 1;
            }
            if at(tokens, next) == "<" {
                next = angle_end(tokens, next).map_or(next, |end| end + 1);
            }
            (at(tokens, next) == "(")
                .then(|| method_body(tokens, pairs, next))
                .flatten()
        } else if token.kind == Kind::Word
            && (!keyword(token.text) || token.text == "constructor")
            && (i == 0 || !matches!(at(tokens, i - 1), "." | "?." | "new" | "@" | "function"))
        {
            let mut paren = i + 1;
            if at(tokens, paren) == "<" {
                paren = angle_end(tokens, paren).map_or(paren, |end| end + 1);
            }
            (at(tokens, paren) == "(")
                .then(|| method_body(tokens, pairs, paren))
                .flatten()
        } else {
            None
        };
        if let Some(body) = body {
            results.entry(body).or_insert(Function {
                name,
                start,
                body,
                end: pairs[body].unwrap(),
            });
        }
    }
    results.into_values().collect()
}

pub fn branches(tokens: &[Token<'_>], functions: &[Function<'_>]) -> Vec<usize> {
    let mut counts = vec![0; functions.len()];
    let mut pending = 0;
    let mut parents: Vec<usize> = Vec::new();
    for (i, token) in tokens.iter().enumerate() {
        while parents.last().is_some_and(|&id| functions[id].end < i) {
            parents.pop();
        }
        while pending < functions.len() && functions[pending].body == i {
            parents.push(pending);
            pending += 1;
        }
        let Some(&id) = parents.last() else { continue };
        if matches!(
            token.text,
            "if" | "for" | "while" | "case" | "catch" | "&&" | "||" | "??" | "&&=" | "||=" | "??="
        ) || (token.text == "?" && !matches!(at(tokens, i + 1), ":" | ")" | ","))
        {
            counts[id] += 1;
        }
    }
    counts
}
