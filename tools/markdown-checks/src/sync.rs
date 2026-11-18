//! Read one explicit Markdown sync target, then replace it only when its hash is unchanged.
use crate::text::{compact, pretty, sha256, suffix};
use regex::Regex;
use serde_json::{json, Map, Value};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

const MARKDOWN: [&str; 3] = [".md", ".markdown", ".mdx"];
const NOT_MARKDOWN: &str = "Target must be a Markdown file (.md, .markdown, or .mdx).";
const PAGE_KEYS: [&str; 4] = ["notion_page_id", "notion-page-id", "notion_id", "notion-id"];

fn is_markdown(path: &Path) -> bool {
    MARKDOWN.contains(&suffix(&path.to_string_lossy()).as_str())
}

/// Simple `key: value` front matter fields; nested, quoted-structure and indented lines are ignored.
fn frontmatter(text: &str) -> Vec<(String, String)> {
    let block = Regex::new(r"\A---\r?\n((?s:.*?))\r?\n---\r?\n?").unwrap();
    let Some(found) = block.captures(text) else {
        return Vec::new();
    };
    let mut values: Vec<(String, String)> = Vec::new();
    for raw in crate::text::split_lines(&found[1]) {
        if raw.trim().is_empty()
            || raw.trim_start().starts_with('#')
            || raw.starts_with(char::is_whitespace)
            || !raw.contains(':')
        {
            continue;
        }
        let (key, value) = raw.split_once(':').unwrap();
        let value = value.trim();
        if value.starts_with(['[', '{', '|', '>']) {
            continue;
        }
        let key = key.trim().to_string();
        let value = value.trim_matches(['"', '\'']).to_string();
        match values.iter_mut().find(|(seen, _)| *seen == key) {
            Some(slot) => slot.1 = value,
            None => values.push((key, value)),
        }
    }
    values
}

fn unique(items: impl IntoIterator<Item = String>) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    for item in items {
        if !out.contains(&item) {
            out.push(item);
        }
    }
    out
}

pub fn inspect(path: &Path, include_notion: bool) -> Result<Value, String> {
    if !is_markdown(path) {
        return Err(NOT_MARKDOWN.into());
    }
    if !path.is_file() {
        return Err(format!("Markdown target not found: {}", path.display()));
    }
    let data = fs::read(path).map_err(|error| error.to_string())?;
    let text = String::from_utf8_lossy(&data);
    let heading = Regex::new(r"(?m)^(#{1,6})\s+(.+?)\s*#*\s*$").unwrap();
    let headings: Vec<Value> = heading
        .captures_iter(&text)
        .map(|found| json!({ "level": found[1].len(), "text": found[2].trim() }))
        .collect();
    let resolved = fs::canonicalize(path).map_err(|error| error.to_string())?;
    let mut target = Map::new();
    target.insert("path".into(), resolved.to_string_lossy().into());
    target.insert("sha256".into(), sha256(&data).into());
    target.insert("bytes".into(), data.len().into());
    target.insert("headings".into(), headings.into());
    if include_notion {
        let fields = frontmatter(&text);
        let ids_re = Regex::new(
            r"(?im)^\s*(?:notion[ _-]?(?:page[ _-]?)?id)\s*[:=]\s*([0-9a-f-]{32,36})\s*$",
        )
        .unwrap();
        let ids = fields
            .iter()
            .filter(|(key, _)| PAGE_KEYS.contains(&key.to_lowercase().as_str()))
            .map(|(_, value)| value.clone())
            .chain(
                ids_re
                    .captures_iter(&text)
                    .map(|found| found[1].to_string()),
            );
        let urls_re = Regex::new(r"(?i)https?://(?:www\.)?notion\.so/[^\s)>]+").unwrap();
        let field = |name: &str| {
            fields
                .iter()
                .find(|(key, _)| key == name)
                .map(|(_, value)| value.clone())
                .filter(|value| !value.is_empty())
        };
        target.insert("notion_page_ids".into(), unique(ids).into());
        target.insert(
            "notion_urls".into(),
            unique(
                urls_re
                    .find_iter(&text)
                    .map(|found| found.as_str().to_string()),
            )
            .into(),
        );
        target.insert(
            "sync_mode".into(),
            field("sync_mode").or_else(|| field("sync-mode")).into(),
        );
    }
    Ok(Value::Object(target))
}

/// Rendered output and exit code for `sync-inspect`.
pub fn inspect_report(path: &Path, include_notion: bool, as_json: bool) -> (String, i32) {
    let target = match inspect(path, include_notion) {
        Ok(target) => target,
        Err(error) if as_json => {
            return (compact(&json!({ "status": "error", "message": error })), 2)
        }
        Err(error) => return (format!("ERROR: {error}"), 2),
    };
    if as_json {
        return (pretty(&json!({ "status": "ok", "target": target })), 0);
    }
    let text = |key: &str| target[key].as_str().unwrap_or_default().to_string();
    let mut lines = vec![
        format!("Markdown sync target: {}", text("path")),
        format!("- sha256: {}", text("sha256")),
        format!(
            "- headings: {}",
            target["headings"].as_array().map_or(0, Vec::len)
        ),
    ];
    if include_notion {
        let ids: Vec<&str> = target["notion_page_ids"]
            .as_array()
            .map(|ids| ids.iter().filter_map(Value::as_str).collect())
            .unwrap_or_default();
        lines.push(format!(
            "- notion_page_ids: {}",
            if ids.is_empty() {
                "none".into()
            } else {
                ids.join(", ")
            }
        ));
        lines.push(format!(
            "- sync_mode: {}",
            target["sync_mode"].as_str().unwrap_or("none")
        ));
    }
    (lines.join("\n"), 0)
}

pub struct WriteOptions {
    pub target: PathBuf,
    pub content: PathBuf,
    pub expected: String,
    pub dry_run: bool,
}

/// Writes `content` over `target` only when the target still has the hash read earlier.
/// Returns stdout text on success, or the exit code and stderr text.
pub fn write(options: &WriteOptions) -> Result<String, (i32, String)> {
    let fail = |code, message: &str| Err((code, format!("ERROR: {message}")));
    if !is_markdown(&options.target) {
        return fail(2, NOT_MARKDOWN);
    }
    if !options.target.is_file() || !options.content.is_file() {
        return fail(2, "Target or replacement content file was not found.");
    }
    let current = fs::read(&options.target).map_err(|error| (2, format!("ERROR: {error}")))?;
    if sha256(&current) != options.expected.to_lowercase() {
        return fail(
            3,
            "Target changed after it was read; re-inspect and merge before writing.",
        );
    }
    let replacement = fs::read(&options.content).map_err(|error| (2, format!("ERROR: {error}")))?;
    if std::str::from_utf8(&replacement).is_err() {
        return fail(2, "Replacement content must be UTF-8.");
    }
    let resolved =
        fs::canonicalize(&options.target).map_err(|error| (2, format!("ERROR: {error}")))?;
    if options.dry_run {
        return Ok(format!(
            "DRY-RUN: {} would be replaced ({} bytes).",
            resolved.display(),
            replacement.len()
        ));
    }
    let parent = resolved
        .parent()
        .ok_or((2, "ERROR: Target has no parent folder.".to_string()))?;
    let io = |error: std::io::Error| (2, format!("ERROR: {error}"));
    let permissions = fs::metadata(&resolved).map_err(io)?.permissions();
    let temporary = (0..100u32)
        .map(|attempt| {
            parent.join(format!(
                ".{}.{}-{attempt}.tmp",
                resolved.file_name().unwrap_or_default().to_string_lossy(),
                std::process::id()
            ))
        })
        .find_map(|path| {
            fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&path)
                .ok()
                .map(|file| (path, file))
        });
    let (temporary, mut file) = temporary.ok_or((
        2,
        "ERROR: Could not create a temporary file beside the target.".to_string(),
    ))?;
    let result = file
        .write_all(&replacement)
        .and_then(|()| file.sync_all())
        .and_then(|()| fs::set_permissions(&temporary, permissions))
        .and_then(|()| fs::rename(&temporary, &resolved));
    if let Err(error) = result {
        let _ = fs::remove_file(&temporary);
        return Err(io(error));
    }
    let written = fs::read(&resolved).map_err(io)?;
    Ok(format!(
        "WROTE: {} sha256={}",
        resolved.display(),
        sha256(&written)
    ))
}
