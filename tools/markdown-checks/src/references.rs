//! Bounded, read-only Markdown link and reverse-reference analysis among selected documents.
//!
//! Only ATX headings and inline links/images are parsed. Reference-style links, raw HTML,
//! multiline link syntax and nested-parenthesis destinations are reported as unsupported.
use crate::text::split_lines;
use regex::Regex;
use serde_json::{json, Value};
use std::collections::{BTreeMap, HashSet};
use std::io::Read;
use std::path::{Component, Path, PathBuf};

const MAX_DOCUMENTS: usize = 500;
const MAX_AFFECTED: usize = 5_000;
const MAX_FILE_BYTES: usize = 1_048_576;
const MAX_TOTAL_BYTES: usize = 16 * MAX_FILE_BYTES;
const MAX_REFERENCES: usize = 10_000;
const UNSUPPORTED: [&str; 5] = [
    "reference-style links",
    "raw HTML links",
    "multiline link syntax",
    "nested-parenthesis destinations",
    "setext headings",
];

/// Inline code spans as `(start, end, inner_start, inner_end)` byte ranges, matching the
/// backtracking behaviour of `` (`+)(.*?)\1 `` on one line.
fn code_spans(line: &str) -> Vec<(usize, usize, usize, usize)> {
    let bytes = line.as_bytes();
    let mut spans = Vec::new();
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] != b'`' {
            index += 1;
            continue;
        }
        let run = bytes[index..].iter().take_while(|b| **b == b'`').count();
        let found = (1..=run).rev().find_map(|size| {
            let fence = &bytes[index..index + size];
            (index + size..=bytes.len().saturating_sub(size))
                .find(|start| &bytes[*start..*start + size] == fence)
                .map(|start| (index, start + size, index + size, start))
        });
        match found {
            Some(span) => {
                index = span.1;
                spans.push(span);
            }
            None => index += 1,
        }
    }
    spans
}

/// Replace inline code with spaces of the same character count.
fn mask_code(line: &str) -> String {
    let mut out = String::new();
    let mut cursor = 0;
    for (start, end, _, _) in code_spans(line) {
        out.push_str(&line[cursor..start]);
        out.push_str(&" ".repeat(line[start..end].chars().count()));
        cursor = end;
    }
    out.push_str(&line[cursor..]);
    out
}

/// Replace inline code with its inner text.
fn unwrap_code(line: &str) -> String {
    let mut out = String::new();
    let mut cursor = 0;
    for (start, end, inner_start, inner_end) in code_spans(line) {
        out.push_str(&line[cursor..start]);
        out.push_str(&line[inner_start..inner_end]);
        cursor = end;
    }
    out.push_str(&line[cursor..]);
    out
}

/// GitHub-style heading slug: lowercase, drop punctuation, whitespace runs to hyphens.
pub fn slugify(text: &str) -> String {
    let kept: String = text
        .to_lowercase()
        .chars()
        .filter(|c| c.is_alphanumeric() || *c == '_' || *c == '-' || c.is_whitespace())
        .collect();
    let mut out = String::new();
    let mut gap = false;
    for ch in kept.trim().chars() {
        if ch.is_whitespace() {
            gap = true;
        } else {
            if gap {
                out.push('-');
                gap = false;
            }
            out.push(ch);
        }
    }
    out
}

/// Percent-decoding like Python `urllib.parse.unquote` (invalid UTF-8 becomes U+FFFD).
pub fn unquote(text: &str) -> String {
    let bytes = text.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] == b'%' && index + 2 < bytes.len() {
            let hex = std::str::from_utf8(&bytes[index + 1..index + 3]).ok();
            if let Some(value) = hex.and_then(|h| u8::from_str_radix(h, 16).ok()) {
                out.push(value);
                index += 3;
                continue;
            }
        }
        out.push(bytes[index]);
        index += 1;
    }
    String::from_utf8_lossy(&out).into_owned()
}

/// Lexical absolute path with symlinks resolved for the existing prefix, like `Path.resolve()`.
fn resolve(path: &Path) -> PathBuf {
    let mut normal = PathBuf::new();
    for part in path.components() {
        match part {
            Component::CurDir => {}
            Component::ParentDir => {
                let real = std::fs::canonicalize(&normal).unwrap_or(normal.clone());
                normal = real.parent().map(Path::to_path_buf).unwrap_or(real);
            }
            other => normal.push(other),
        }
    }
    let mut existing = normal.clone();
    let mut rest = Vec::new();
    loop {
        if let Ok(real) = std::fs::canonicalize(&existing) {
            let mut out = real;
            out.extend(rest.iter().rev());
            return out;
        }
        match (existing.parent(), existing.file_name()) {
            (Some(parent), Some(name)) => {
                rest.push(name.to_os_string());
                existing = parent.to_path_buf();
            }
            _ => return normal,
        }
    }
}

fn relative(base: &Path, path: &Path) -> Option<String> {
    let rest = path.strip_prefix(base).ok()?;
    let parts: Vec<String> = rest
        .components()
        .map(|part| part.as_os_str().to_string_lossy().into_owned())
        .collect();
    Some(if parts.is_empty() {
        ".".into()
    } else {
        parts.join("/")
    })
}

fn is_markdown(path: &Path) -> bool {
    matches!(
        crate::text::suffix(&path.to_string_lossy()).as_str(),
        ".md" | ".markdown" | ".mdx"
    )
}

fn read_document(path: &Path, limit: usize) -> Result<Vec<u8>, (String, usize)> {
    if !path.is_file() || !is_markdown(path) {
        return Err(("expected a readable Markdown file".into(), 0));
    }
    let mut raw = Vec::new();
    std::fs::File::open(path)
        .and_then(|file| file.take(limit as u64 + 1).read_to_end(&mut raw))
        .map_err(|error| (error.to_string(), 0))?;
    if raw.len() > limit {
        return Err((
            "document exceeds the remaining size limit".into(),
            raw.len(),
        ));
    }
    Ok(raw)
}

struct Link {
    source: String,
    line: usize,
    destination: String,
    kind: &'static str,
}

fn reference(base: &Path, headings: &BTreeMap<String, HashSet<String>>, link: &Link) -> Value {
    let (name, anchor) = match link.destination.split_once('#') {
        Some((name, anchor)) => (name, anchor),
        None => (link.destination.as_str(), ""),
    };
    let anchor_value = if anchor.is_empty() {
        Value::Null
    } else {
        anchor.into()
    };
    let document = base.join(&link.source);
    let target = if name.is_empty() {
        document.clone()
    } else {
        resolve(&document.parent().unwrap_or(base).join(unquote(name)))
    };
    let row = |exists: Value, reason: Value, key: Value| {
        json!({"source": link.source, "line": link.line, "target": link.destination,
            "anchor": anchor_value, "exists": exists, "kind": link.kind, "reason": reason,
            "resolved_target": key})
    };
    let Some(key) = relative(base, &target) else {
        return row(false.into(), "outside-or-invalid-path".into(), Value::Null);
    };
    let (exists, reason) = if !target.exists() {
        (Value::from(false), Value::from("missing-file"))
    } else if anchor.is_empty() {
        (true.into(), Value::Null)
    } else if let Some(names) = headings.get(&key) {
        let normalized = unquote(anchor).trim().to_lowercase().replace(' ', "-");
        let found = names.contains(&normalized);
        (
            found.into(),
            if found {
                Value::Null
            } else {
                "missing-anchor".into()
            },
        )
    } else {
        (Value::Null, "anchor-not-inspected".into())
    };
    row(exists, reason, key.into())
}

pub fn analyze(root: &Path, documents: &[String], affected: &[String]) -> Result<Value, String> {
    let base =
        std::fs::canonicalize(root).map_err(|error| format!("{}: {error}", root.display()))?;
    if !base.is_dir() || documents.len() > MAX_DOCUMENTS || affected.len() > MAX_AFFECTED {
        return Err(
            "expected a directory and at most 500 documents and 5000 affected paths".into(),
        );
    }
    let link_re = Regex::new(r#"(!?)\[([^\]]*)\]\(([^)\s]+)(?:\s+(?:"[^"]*"|'[^']*'))?\s*\)"#)
        .expect("valid regex");
    let heading_re = Regex::new(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$").expect("valid regex");
    let fence_re = Regex::new(r"^ {0,3}(`{3,}|~{3,})").expect("valid regex");
    let scheme = Regex::new(r"^[A-Za-z][A-Za-z0-9+.-]*:").expect("valid regex");
    let mut diagnostics = Vec::new();
    let mut headings: BTreeMap<String, HashSet<String>> = BTreeMap::new();
    let mut links: Vec<Link> = Vec::new();
    let mut budget = MAX_TOTAL_BYTES as i64;
    let mut truncated = false;
    for item in documents {
        let path = resolve(&base.join(item));
        let rel = relative(&base, &path).ok_or(format!("document escapes root: {item}"))?;
        if headings.contains_key(&rel) {
            continue;
        }
        let limit = (MAX_FILE_BYTES as i64).min(budget).max(0) as usize;
        let decoded = match read_document(&path, limit) {
            Ok(raw) => {
                budget -= raw.len() as i64;
                let body = raw.strip_prefix(b"\xEF\xBB\xBF").unwrap_or(&raw);
                std::str::from_utf8(body)
                    .map(str::to_string)
                    .map_err(|error| crate::text::utf8_error(body, error))
            }
            Err((message, read)) => {
                budget -= read as i64;
                Err(message)
            }
        };
        let text = match decoded {
            Ok(text) => text,
            Err(reason) => {
                diagnostics.push(json!({"path": rel, "reason": reason}));
                if budget <= 0 {
                    truncated = true;
                    break;
                }
                continue;
            }
        };
        let mut names: HashSet<String> = HashSet::new();
        let mut counts: BTreeMap<String, usize> = BTreeMap::new();
        let mut fence: Option<String> = None;
        for (index, raw_line) in split_lines(&text).into_iter().enumerate() {
            if let Some(found) = fence_re.captures(raw_line) {
                let token = found[1].to_string();
                let end = found.get(0).map_or(0, |m| m.end());
                match &fence {
                    None => {
                        fence = Some(token);
                        continue;
                    }
                    Some(open)
                        if token.starts_with(open.as_str())
                            && raw_line[end..].trim().is_empty() =>
                    {
                        fence = None;
                        continue;
                    }
                    _ => {}
                }
            }
            if fence.is_some() {
                continue;
            }
            if let Some(found) = heading_re.captures(raw_line) {
                let slug = slugify(&unwrap_code(&found[2]));
                let mut count = counts.get(&slug).copied().unwrap_or(0);
                let label = |count: usize| {
                    if count == 0 {
                        slug.clone()
                    } else {
                        format!("{slug}-{count}")
                    }
                };
                while names.contains(&label(count)) {
                    count += 1;
                }
                names.insert(label(count));
                counts.insert(slug.clone(), count + 1);
            }
            for found in link_re.captures_iter(&mask_code(raw_line)) {
                let destination = found[3].to_string();
                if destination.is_empty()
                    || scheme.is_match(&destination)
                    || destination.starts_with("//")
                {
                    continue;
                }
                if links.len() >= MAX_REFERENCES {
                    truncated = true;
                    continue;
                }
                links.push(Link {
                    source: rel.clone(),
                    line: index + 1,
                    destination,
                    kind: if found[1].is_empty() { "link" } else { "image" },
                });
            }
        }
        headings.insert(rel, names);
    }
    let mut affected_keys = HashSet::new();
    for item in affected {
        let target = resolve(&base.join(item));
        let key = relative(&base, &target).ok_or(format!("affected path escapes root: {item}"))?;
        affected_keys.insert(key);
    }
    let references: Vec<Value> = links
        .iter()
        .map(|link| reference(&base, &headings, link))
        .collect();
    let reverse: Vec<Value> = references
        .iter()
        .filter(|row| {
            row["resolved_target"]
                .as_str()
                .is_some_and(|key| affected_keys.is_empty() || affected_keys.contains(key))
        })
        .cloned()
        .collect();
    let partial = !diagnostics.is_empty() || truncated;
    Ok(
        json!({"root": base.to_string_lossy(), "documents": headings.keys().collect::<Vec<_>>(),
        "references": references, "reverse_references": reverse, "diagnostics": diagnostics,
        "partial": partial, "truncated": truncated, "unsupported": UNSUPPORTED}),
    )
}

/// Pretty JSON with non-ASCII escaped as `\uXXXX`, like `json.dumps(ensure_ascii=True)`.
pub fn ascii_json(value: &Value) -> String {
    let mut out = String::new();
    for ch in crate::text::pretty(value).chars() {
        if ch.is_ascii() {
            out.push(ch);
        } else {
            let mut units = [0u16; 2];
            for unit in ch.encode_utf16(&mut units) {
                out.push_str(&format!("\\u{unit:04x}"));
            }
        }
    }
    out
}

/// Output and exit code: 0 complete, 1 partial, 2 invalid input.
pub fn run(root: &Path, documents: &[String], affected: &[String]) -> (String, String, i32) {
    match analyze(root, documents, affected) {
        Ok(result) => {
            let code = i32::from(result["partial"] == true);
            (ascii_json(&result), String::new(), code)
        }
        Err(message) => (
            String::new(),
            crate::text::compact(&json!({"status": "error", "message": message})),
            2,
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn masks_code_like_backtracking_regex() {
        assert_eq!(mask_code("a `x` b"), "a     b");
        assert_eq!(mask_code("``a`"), "  a`");
        assert_eq!(unwrap_code("`` a ` b ``"), " a ` b ");
    }

    #[test]
    fn slugs_and_unquote() {
        assert_eq!(slugify("Hello, World! 中文"), "hello-world-中文");
        assert_eq!(unquote("a%20b%zz%E4%B8%AD"), "a b%zz中");
    }

    #[test]
    fn resolves_links_and_anchors() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("a.md"),
            "# Top\n[b](b.md#part)\n[x](b.md#nope)\n`[c](c.md)`\n[web](https://x)\n",
        )
        .unwrap();
        std::fs::write(dir.path().join("b.md"), "## Part\n[up](a.md#top)\n").unwrap();
        let docs = vec!["a.md".to_string(), "b.md".to_string()];
        let result = analyze(dir.path(), &docs, &["b.md".to_string()]).unwrap();
        let rows = result["references"].as_array().unwrap();
        assert_eq!(rows.len(), 3);
        assert_eq!(rows[0]["exists"], true);
        assert_eq!(rows[1]["reason"], "missing-anchor");
        assert_eq!(result["reverse_references"].as_array().unwrap().len(), 2);
        assert_eq!(result["partial"], false);
    }
}
