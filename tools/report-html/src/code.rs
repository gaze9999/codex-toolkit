//! Lightweight code tokenizer for `source` cells. It colors comments, strings, numbers, booleans,
//! keywords and keys with the Workbench UI token classes (`wb-code-*`); it does not build a syntax
//! tree or check that the code is valid. Unclassified text is escaped and kept as is.
use crate::escape;

/// Cells above this size are shown without colors.
const LIMIT: usize = 100_000;

/// Token rules for one language; `name` and `aliases` are the accepted `lang` values.
pub struct Lang {
    pub name: &'static str,
    aliases: &'static [&'static str],
    line: &'static [&'static str],
    block: bool,
    nested: bool,
    /// Characters that open a string; SQL identifiers are handled separately.
    quotes: &'static [u8],
    triple: bool,
    sql: bool,
    rust: bool,
    /// A string or word followed by this character is a key.
    key_mark: Option<u8>,
    bare_keys: bool,
    keywords: &'static [&'static str],
    booleans: &'static [&'static str],
    ignore_case: bool,
}

const fn lang(name: &'static str, aliases: &'static [&'static str]) -> Lang {
    Lang {
        name,
        aliases,
        line: &[],
        block: false,
        nested: false,
        quotes: b"\"'",
        triple: false,
        sql: false,
        rust: false,
        key_mark: None,
        bare_keys: false,
        keywords: &[],
        booleans: &[],
        ignore_case: false,
    }
}

const JS_WORDS: &[&str] = &[
    "abstract",
    "as",
    "async",
    "await",
    "break",
    "case",
    "catch",
    "class",
    "const",
    "continue",
    "debugger",
    "declare",
    "default",
    "delete",
    "do",
    "else",
    "enum",
    "export",
    "extends",
    "finally",
    "for",
    "from",
    "function",
    "get",
    "if",
    "implements",
    "import",
    "in",
    "instanceof",
    "interface",
    "keyof",
    "let",
    "namespace",
    "new",
    "of",
    "private",
    "protected",
    "public",
    "readonly",
    "return",
    "set",
    "static",
    "super",
    "switch",
    "this",
    "throw",
    "try",
    "type",
    "typeof",
    "var",
    "void",
    "while",
    "with",
    "yield",
];
const RUST_WORDS: &[&str] = &[
    "as", "async", "await", "break", "const", "continue", "crate", "dyn", "else", "enum", "extern",
    "fn", "for", "if", "impl", "in", "let", "loop", "match", "mod", "move", "mut", "pub", "ref",
    "return", "self", "Self", "static", "struct", "super", "trait", "type", "unsafe", "use",
    "where", "while",
];
const PYTHON_WORDS: &[&str] = &[
    "and", "as", "assert", "async", "await", "break", "case", "class", "continue", "def", "del",
    "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "match", "nonlocal", "not", "or", "pass", "raise", "return", "self", "try", "while",
    "with", "yield",
];
const SQL_WORDS: &[&str] = &[
    "all",
    "alter",
    "and",
    "as",
    "asc",
    "begin",
    "between",
    "by",
    "case",
    "commit",
    "create",
    "cross",
    "delete",
    "desc",
    "distinct",
    "drop",
    "else",
    "end",
    "exists",
    "foreign",
    "from",
    "full",
    "group",
    "having",
    "in",
    "index",
    "inner",
    "insert",
    "into",
    "is",
    "join",
    "key",
    "left",
    "like",
    "limit",
    "not",
    "offset",
    "on",
    "or",
    "order",
    "outer",
    "primary",
    "references",
    "returning",
    "right",
    "rollback",
    "select",
    "set",
    "table",
    "then",
    "union",
    "update",
    "values",
    "view",
    "when",
    "where",
    "with",
];
const SHELL_WORDS: &[&str] = &[
    "case", "do", "done", "elif", "else", "esac", "export", "fi", "for", "function", "if", "in",
    "local", "readonly", "return", "then", "until", "while",
];

pub const LANGS: [Lang; 10] = [
    lang("text", &["plain"]),
    Lang {
        line: &["//"],
        block: true,
        quotes: b"\"'`",
        keywords: JS_WORDS,
        booleans: &["true", "false", "null", "undefined"],
        ..lang(
            "typescript",
            &["ts", "tsx", "javascript", "js", "jsx", "mjs", "cjs"],
        )
    },
    Lang {
        line: &["//"],
        block: true,
        nested: true,
        quotes: b"\"'",
        rust: true,
        keywords: RUST_WORDS,
        booleans: &["true", "false"],
        ..lang("rust", &["rs"])
    },
    Lang {
        line: &["#"],
        triple: true,
        keywords: PYTHON_WORDS,
        booleans: &["True", "False", "None"],
        ..lang("python", &["py"])
    },
    Lang {
        line: &["--"],
        block: true,
        nested: true,
        quotes: b"'",
        sql: true,
        keywords: SQL_WORDS,
        booleans: &["true", "false", "null"],
        ignore_case: true,
        ..lang("sql", &[])
    },
    Lang {
        line: &["#"],
        keywords: SHELL_WORDS,
        booleans: &["true", "false"],
        ..lang("shell", &["sh", "bash", "zsh"])
    },
    Lang {
        quotes: b"\"",
        key_mark: Some(b':'),
        booleans: &["true", "false", "null"],
        ..lang("json", &[])
    },
    Lang {
        line: &["#"],
        key_mark: Some(b':'),
        bare_keys: true,
        booleans: &["true", "false", "null"],
        ignore_case: true,
        ..lang("yaml", &["yml"])
    },
    Lang {
        line: &["#"],
        key_mark: Some(b'='),
        bare_keys: true,
        booleans: &["true", "false"],
        ..lang("toml", &[])
    },
    Lang {
        block: true,
        ..lang("css", &[])
    },
];

/// Finds the rules for a `lang` value, or lists the accepted names.
pub fn find(name: &str) -> Result<&'static Lang, String> {
    let name = name.to_ascii_lowercase();
    LANGS
        .iter()
        .find(|lang| lang.name == name || lang.aliases.contains(&name.as_str()))
        .ok_or_else(|| {
            let names: Vec<&str> = LANGS.iter().map(|lang| lang.name).collect();
            format!("Unknown source lang {name:?}; use {}", names.join(", "))
        })
}

fn word_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'_' || byte == b'$' || byte >= 0x80
}

/// End of a block comment that starts at `start` (after the opening `/*`).
fn block_end(bytes: &[u8], start: usize, nested: bool) -> usize {
    let (mut depth, mut i) = (1, start);
    while i < bytes.len() {
        if nested && bytes[i..].starts_with(b"/*") {
            depth += 1;
            i += 2;
        } else if bytes[i..].starts_with(b"*/") {
            depth -= 1;
            i += 2;
            if depth == 0 {
                return i;
            }
        } else {
            i += 1;
        }
    }
    bytes.len()
}

/// End of a quoted value opened at `start`; backslash escapes, SQL also doubles the quote.
fn quote_end(bytes: &[u8], start: usize, close: u8, doubled: bool) -> usize {
    let mut i = start + 1;
    while i < bytes.len() {
        match bytes[i] {
            b'\\' if close != b']' => i += 2,
            byte if byte == close => {
                if doubled && bytes.get(i + 1) == Some(&close) {
                    i += 2;
                } else {
                    return i + 1;
                }
            }
            _ => i += 1,
        }
    }
    bytes.len()
}

fn number_end(bytes: &[u8], start: usize) -> usize {
    let mut i = start;
    if bytes[i..].starts_with(b"0x") || bytes[i..].starts_with(b"0X") {
        i += 2;
    }
    while i < bytes.len() && (bytes[i].is_ascii_alphanumeric() || bytes[i] == b'_') {
        i += 1;
    }
    if bytes.get(i) == Some(&b'.') && bytes.get(i + 1).is_some_and(u8::is_ascii_digit) {
        i += 1;
        while i < bytes.len() && (bytes[i].is_ascii_alphanumeric() || bytes[i] == b'_') {
            i += 1;
        }
    }
    // An exponent sign such as 1e-3 stays in the number
    if matches!(bytes.get(i), Some(b'-' | b'+'))
        && matches!(bytes.get(i - 1), Some(b'e' | b'E'))
        && bytes.get(i + 1).is_some_and(u8::is_ascii_digit)
    {
        i += 1;
        while i < bytes.len() && bytes[i].is_ascii_digit() {
            i += 1;
        }
    }
    i
}

fn followed_by(bytes: &[u8], mut i: usize, mark: u8) -> bool {
    while matches!(bytes.get(i), Some(b' ' | b'\t')) {
        i += 1;
    }
    bytes.get(i) == Some(&mark)
}

/// A bare key starts its line, after indentation or a YAML list marker.
fn line_start(bytes: &[u8], i: usize) -> bool {
    bytes[..i]
        .iter()
        .rev()
        .take_while(|b| **b != b'\n')
        .all(|b| matches!(b, b' ' | b'\t' | b'-'))
}

fn listed(list: &[&str], word: &str, ignore_case: bool) -> bool {
    list.iter()
        .any(|item| *item == word || ignore_case && item.eq_ignore_ascii_case(word))
}

/// Returns escaped HTML with `<span class="wb-code-…">` around recognized tokens.
pub fn highlight(text: &str, lang: &Lang) -> String {
    if lang.name == "text" || text.len() > LIMIT {
        return escape(text);
    }
    let bytes = text.as_bytes();
    let mut out = String::with_capacity(text.len() * 2);
    let (mut i, mut plain) = (0, 0);
    // Every token starts and ends on an ASCII byte or the end of the text, so slices stay on char boundaries
    while i < bytes.len() {
        let byte = bytes[i];
        let rest = &bytes[i..];
        let at_word_start = i == 0 || !word_byte(bytes[i - 1]);
        let (end, kind) = if lang.block && rest.starts_with(b"/*") {
            (block_end(bytes, i + 2, lang.nested), "comment")
        } else if lang.line.iter().any(|mark| {
            rest.starts_with(mark.as_bytes())
                && (*mark != "#" || i == 0 || bytes[i - 1].is_ascii_whitespace())
        }) {
            let end = rest
                .iter()
                .position(|b| *b == b'\n')
                .map_or(bytes.len(), |n| i + n);
            (end, "comment")
        } else if lang.triple && (rest.starts_with(b"\"\"\"") || rest.starts_with(b"'''")) {
            let end = text[i + 3..]
                .find(&text[i..i + 3])
                .map_or(bytes.len(), |n| i + 6 + n);
            (end, "string")
        } else if lang.sql && matches!(byte, b'"' | b'`' | b'[') {
            let close = if byte == b'[' { b']' } else { byte };
            (quote_end(bytes, i, close, true), "key")
        } else if lang.rust
            && byte == b'\''
            && rest.len() > 1
            && word_byte(rest[1])
            && !rest[1].is_ascii_digit()
            && {
                let mut n = 1;
                while n < rest.len() && word_byte(rest[n]) {
                    n += 1;
                }
                rest.get(n) != Some(&b'\'')
            }
        {
            // A lifetime such as 'a is not a character literal
            i += 1;
            continue;
        } else if lang.quotes.contains(&byte) {
            let end = quote_end(bytes, i, byte, lang.sql);
            let key = lang
                .key_mark
                .is_some_and(|mark| followed_by(bytes, end, mark));
            (end, if key { "key" } else { "string" })
        } else if byte.is_ascii_digit() && at_word_start {
            (number_end(bytes, i), "number")
        } else if word_byte(byte) && byte != b'$' && at_word_start {
            let mut end = i;
            while end < bytes.len() && word_byte(bytes[end]) {
                end += 1;
            }
            let word = &text[i..end];
            let kind = if lang.bare_keys
                && line_start(bytes, i)
                && lang
                    .key_mark
                    .is_some_and(|mark| followed_by(bytes, end, mark))
            {
                "key"
            } else if listed(lang.booleans, word, lang.ignore_case) {
                "boolean"
            } else if listed(lang.keywords, word, lang.ignore_case) {
                "keyword"
            } else {
                ""
            };
            (end, kind)
        } else {
            i += 1;
            continue;
        };
        if kind.is_empty() {
            i = end;
            continue;
        }
        out.push_str(&escape(&text[plain..i]));
        out.push_str(&format!(
            "<span class=\"wb-code-{kind}\">{}</span>",
            escape(&text[i..end])
        ));
        i = end;
        plain = end;
    }
    out.push_str(&escape(&text[plain..]));
    out
}
