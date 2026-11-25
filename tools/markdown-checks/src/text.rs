//! Text helpers that keep line splitting, case folding and JSON spacing compatible with the
//! scripts these commands replaced, so existing consumers see the same values.
use serde_json::Value;
use sha2::{Digest, Sha256};
use unicode_casefold::UnicodeCaseFold;

/// Line boundaries recognised by Python `str.splitlines`.
const BREAKS: [char; 10] = [
    '\n', '\r', '\u{0b}', '\u{0c}', '\u{1c}', '\u{1d}', '\u{1e}', '\u{85}', '\u{2028}', '\u{2029}',
];

pub fn is_break(ch: char) -> bool {
    BREAKS.contains(&ch)
}

pub fn split_lines(text: &str) -> Vec<&str> {
    let mut lines = Vec::new();
    let mut start = 0;
    let mut chars = text.char_indices().peekable();
    while let Some((index, ch)) = chars.next() {
        if BREAKS.contains(&ch) {
            lines.push(&text[start..index]);
            let mut end = index + ch.len_utf8();
            if ch == '\r' {
                if let Some((next, '\n')) = chars.peek().copied() {
                    chars.next();
                    end = next + 1;
                }
            }
            start = end;
        }
    }
    if start < text.len() {
        lines.push(&text[start..]);
    }
    lines
}

pub fn casefold(text: &str) -> String {
    text.case_fold().collect()
}

pub fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

/// Single-line JSON with `", "` and `": "` separators.
pub fn compact(value: &Value) -> String {
    match value {
        Value::Array(items) => format!(
            "[{}]",
            items.iter().map(compact).collect::<Vec<_>>().join(", ")
        ),
        Value::Object(fields) => {
            let body: Vec<String> = fields
                .iter()
                .map(|(key, item)| format!("{}: {}", Value::from(key.as_str()), compact(item)))
                .collect();
            format!("{{{}}}", body.join(", "))
        }
        other => other.to_string(),
    }
}

pub fn pretty(value: &Value) -> String {
    serde_json::to_string_pretty(value).unwrap_or_default()
}

/// Lower-case suffix of the final path component, empty for names such as `.env`.
pub fn suffix(name: &str) -> String {
    let base = name.rsplit(['/', '\\']).next().unwrap_or(name);
    match base.rfind('.') {
        Some(0) | None => String::new(),
        Some(index) if index + 1 == base.len() => String::new(),
        Some(index) => base[index..].to_lowercase(),
    }
}

/// Error text in the form Python's UTF-8 decoder uses.
pub fn utf8_error(bytes: &[u8], error: std::str::Utf8Error) -> String {
    let position = error.valid_up_to();
    let byte = bytes[position];
    let reason = match error.error_len() {
        None => "unexpected end of data",
        Some(_) if (0x80..0xc2).contains(&byte) || byte > 0xf4 => "invalid start byte",
        Some(_) => "invalid continuation byte",
    };
    format!("'utf-8' codec can't decode byte 0x{byte:02x} in position {position}: {reason}")
}
