#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Language {
    Script,
    Html,
    Style,
}

impl Language {
    pub fn from_path(path: &std::path::Path) -> Option<Self> {
        match path.extension()?.to_str()? {
            "ts" | "tsx" | "mts" | "cts" | "js" | "jsx" | "mjs" | "cjs" => Some(Self::Script),
            "html" | "htm" => Some(Self::Html),
            "css" | "scss" | "sass" | "less" => Some(Self::Style),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum Kind {
    Word,
    String,
    Template,
    Number,
    Regex,
    Symbol,
}

#[derive(Clone, Copy, Debug)]
pub struct Token<'a> {
    pub kind: Kind,
    pub text: &'a str,
    pub line: usize,
    pub end_line: usize,
}

impl<'a> Token<'a> {
    pub fn string(self) -> Option<&'a str> {
        if self.kind != Kind::String || self.text.len() < 2 {
            return None;
        }
        let value = &self.text[1..self.text.len() - 1];
        (self.text.as_bytes().first() == self.text.as_bytes().last() && !value.contains('\\'))
            .then_some(value)
    }
}

fn word_start(c: char) -> bool {
    c == '_' || c == '$' || c.is_alphabetic()
}

fn word_continue(c: char) -> bool {
    word_start(c)
        || c.is_alphanumeric()
        || matches!(c, '\u{200c}' | '\u{200d}' | '\u{0300}'..='\u{036f}')
}

fn quoted_end(bytes: &[u8], start: usize) -> usize {
    let quote = bytes[start];
    let mut index = start + 1;
    while index < bytes.len() {
        if bytes[index] == quote {
            return index + 1;
        }
        if bytes[index] == b'\\' {
            index += 1;
        }
        index += 1;
    }
    bytes.len()
}

fn template_end(bytes: &[u8], start: usize, depth: usize) -> usize {
    if depth >= 32 {
        return bytes.len();
    }
    let mut index = start + 1;
    let mut braces = 0usize;
    while let Some(&b) = bytes.get(index) {
        match b {
            b'\\' => index += 2,
            b'`' if braces == 0 => return index + 1,
            b'`' => index = template_end(bytes, index, depth + 1),
            b'\'' | b'"' if braces > 0 => index = quoted_end(bytes, index),
            b'$' if braces == 0 && bytes.get(index + 1) == Some(&b'{') => {
                braces = 1;
                index += 2;
            }
            b'{' if braces > 0 => {
                braces += 1;
                index += 1;
            }
            b'}' if braces > 0 => {
                braces -= 1;
                index += 1;
            }
            _ => index += 1,
        }
    }
    bytes.len()
}

fn regex_end(bytes: &[u8], start: usize) -> Option<usize> {
    let mut index = start + 1;
    let mut class = false;
    while let Some(&b) = bytes.get(index) {
        match b {
            b'\n' | b'\r' => return None,
            b'\\' => index += 1,
            b'[' => class = true,
            b']' => class = false,
            b'/' if !class => {
                index += 1;
                while bytes.get(index).is_some_and(u8::is_ascii_alphabetic) {
                    index += 1;
                }
                return Some(index);
            }
            _ => {}
        }
        index += 1;
    }
    None
}

pub fn tokenize(source: &str, language: Language) -> Vec<Token<'_>> {
    let mut tokens: Vec<Token> = Vec::new();
    let mut index = 0;
    let mut line = 1;
    let mut tag = false;
    let bytes = source.as_bytes();
    while index < bytes.len() {
        let rest = &source[index..];
        let c = rest.chars().next().unwrap();
        if c.is_whitespace() || c == '\u{feff}' {
            line += usize::from(c == '\n');
            index += c.len_utf8();
            continue;
        }
        let comment = if language == Language::Html && rest.starts_with("<!--") {
            Some(rest[4..].find("-->").map_or(rest.len(), |end| end + 7))
        } else if language != Language::Html && rest.starts_with("/*") {
            Some(rest[2..].find("*/").map_or(rest.len(), |end| end + 4))
        } else if (language != Language::Html && rest.starts_with("//"))
            || (index == 0 && rest.starts_with("#!"))
        {
            Some(rest.find('\n').unwrap_or(rest.len()))
        } else {
            None
        };
        if let Some(length) = comment {
            line += rest.as_bytes()[..length]
                .iter()
                .filter(|&&b| b == b'\n')
                .count();
            index += length;
            continue;
        }
        let starts_regex = language == Language::Script
            && c == '/'
            && tokens.last().is_none_or(|last| {
                matches!(
                    last.text,
                    "=" | "(" | "[" | ":" | "," | "return" | "=>" | "!" | "?" | "&&" | "||" | "??"
                )
            });
        let regex = starts_regex.then(|| regex_end(bytes, index)).flatten();
        let (end, kind) = if let Some(end) = regex {
            (end, Kind::Regex)
        } else if matches!(c, '\'' | '"') && (language != Language::Html || tag) {
            (quoted_end(bytes, index), Kind::String)
        } else if c == '`' && language == Language::Script {
            (template_end(bytes, index, 0), Kind::Template)
        } else if word_start(c) {
            let end = rest
                .char_indices()
                .find(|(i, ch)| *i > 0 && !word_continue(*ch))
                .map_or(source.len(), |(i, _)| index + i);
            (end, Kind::Word)
        } else if c.is_ascii_digit() {
            let end = rest
                .char_indices()
                .find(|(_, ch)| !ch.is_ascii_alphanumeric() && !matches!(ch, '_' | '.'))
                .map_or(source.len(), |(i, _)| index + i);
            (end, Kind::Number)
        } else {
            if language == Language::Html {
                if c == '<' {
                    tag = true;
                }
                if c == '>' {
                    tag = false;
                }
            }
            let operator = [
                "===", "!==", "...", "**=", "&&=", "||=", "??=", "=>", "?.", "??", "&&", "||",
                "==", "!=", "<=", ">=", "++", "--", "+=", "-=", "*=", "/=", "**",
            ]
            .iter()
            .find(|op| rest.starts_with(**op))
            .map_or(c.len_utf8(), |op| op.len());
            (index + operator, Kind::Symbol)
        };
        let content = &source[index..end];
        let end_line = line + content.as_bytes().iter().filter(|&&b| b == b'\n').count();
        tokens.push(Token {
            kind,
            text: content,
            line,
            end_line,
        });
        line = end_line;
        index = end;
    }
    tokens
}

pub fn at<'a>(tokens: &[Token<'a>], index: usize) -> &'a str {
    tokens.get(index).map_or("", |token| token.text)
}

pub fn pairs(tokens: &[Token<'_>]) -> Vec<Option<usize>> {
    let mut matches = vec![None; tokens.len()];
    let mut stack = Vec::new();
    for (index, token) in tokens.iter().enumerate() {
        match token.text {
            "(" | "[" | "{" => stack.push(index),
            ")" | "]" | "}" => {
                if let Some(&open) = stack.last() {
                    if matches!(
                        (tokens[open].text, token.text),
                        ("(", ")") | ("[", "]") | ("{", "}")
                    ) {
                        stack.pop();
                        matches[open] = Some(index);
                        matches[index] = Some(open);
                    }
                }
            }
            _ => {}
        }
    }
    matches
}

pub fn keyword(word: &str) -> bool {
    matches!(
        word,
        "as" | "async"
            | "await"
            | "break"
            | "case"
            | "catch"
            | "class"
            | "const"
            | "continue"
            | "debugger"
            | "default"
            | "delete"
            | "do"
            | "else"
            | "enum"
            | "export"
            | "extends"
            | "false"
            | "finally"
            | "for"
            | "from"
            | "function"
            | "get"
            | "if"
            | "implements"
            | "import"
            | "in"
            | "instanceof"
            | "interface"
            | "let"
            | "new"
            | "null"
            | "of"
            | "private"
            | "protected"
            | "public"
            | "readonly"
            | "return"
            | "set"
            | "static"
            | "super"
            | "switch"
            | "this"
            | "throw"
            | "true"
            | "try"
            | "type"
            | "typeof"
            | "var"
            | "void"
            | "while"
            | "with"
            | "yield"
    )
}
