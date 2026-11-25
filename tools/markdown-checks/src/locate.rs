//! Locate Markdown extracts by recorded source path and SHA-256 metadata.
use crate::text::{casefold, split_lines};
use regex::Regex;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::io::Read;
use std::path::{Component, Path, PathBuf};

const SKIP_DIRECTORIES: [&str; 8] = [
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
];

#[derive(Debug, Clone, PartialEq)]
pub struct Record {
    pub source: String,
    pub source_sha256: Option<String>,
    pub extracted_on: Option<String>,
}

pub fn metadata_records(text: &str) -> Vec<Record> {
    let source_re = Regex::new(r"^- Source(?: path)?:\s+(?:`(?P<quoted>.+)`|(?P<plain>.+))$")
        .expect("valid regex");
    let hash_re = Regex::new(r"^- Source SHA-256:\s+`?([0-9a-fA-F]{64})`?$").expect("valid regex");
    let combined_re =
        Regex::new(r"^- `(.+)` \([^,]+, SHA-256 `([0-9a-fA-F]{64})`\)$").expect("valid regex");
    let extracted_re = Regex::new(r"^- Extracted on: (.+)$").expect("valid regex");
    let mut records = Vec::new();
    let mut current: Option<Record> = None;
    for line in split_lines(text) {
        if let Some(found) = combined_re.captures(line) {
            records.extend(current.take());
            current = Some(Record {
                source: found[1].to_string(),
                source_sha256: Some(found[2].to_lowercase()),
                extracted_on: None,
            });
            continue;
        }
        if let Some(found) = source_re.captures(line) {
            records.extend(current.take());
            let source = found
                .name("quoted")
                .or_else(|| found.name("plain"))
                .map_or("", |m| m.as_str());
            current = Some(Record {
                source: source.trim().to_string(),
                source_sha256: None,
                extracted_on: None,
            });
            continue;
        }
        let Some(record) = current.as_mut() else {
            continue;
        };
        if let Some(found) = hash_re.captures(line) {
            record.source_sha256 = Some(found[1].to_lowercase());
        } else if let Some(found) = extracted_re.captures(line) {
            record.extracted_on = Some(found[1].trim().to_string());
        }
    }
    records.extend(current);
    records
}

fn home(path: &str) -> PathBuf {
    match path.strip_prefix('~') {
        Some(rest) if rest.is_empty() || rest.starts_with(['/', '\\']) => std::env::var_os("HOME")
            .or_else(|| std::env::var_os("USERPROFILE"))
            .map(|home| PathBuf::from(home).join(rest.trim_start_matches(['/', '\\'])))
            .unwrap_or_else(|| PathBuf::from(path)),
        _ => PathBuf::from(path),
    }
}

/// `os.path.normcase(os.path.abspath(os.path.expanduser(value)))`: lexical, no symlinks.
fn normalized(value: &str) -> String {
    let path = home(value);
    let absolute = if path.is_absolute() {
        path
    } else {
        std::env::current_dir().unwrap_or_default().join(path)
    };
    let mut out = PathBuf::new();
    for part in absolute.components() {
        match part {
            Component::CurDir => {}
            Component::ParentDir => {
                out.pop();
            }
            other => out.push(other),
        }
    }
    let text = out.to_string_lossy().into_owned();
    if cfg!(windows) {
        text.replace('/', "\\").to_lowercase()
    } else {
        text
    }
}

fn file_name(value: &str) -> String {
    value
        .rsplit(['/', '\\'])
        .find(|part| !part.is_empty())
        .unwrap_or("")
        .to_string()
}

fn sha256_file(path: &Path) -> Result<String, String> {
    let mut file =
        std::fs::File::open(path).map_err(|error| format!("{}: {error}", path.display()))?;
    let mut digest = Sha256::new();
    let mut buffer = vec![0; 1024 * 1024];
    loop {
        let read = file.read(&mut buffer).map_err(|error| error.to_string())?;
        if read == 0 {
            return Ok(format!("{:x}", digest.finalize()));
        }
        digest.update(&buffer[..read]);
    }
}

/// Markdown files under each root, skipping hidden and generated directories without following links.
fn markdown_files(roots: &[PathBuf], max_files: usize) -> (Vec<PathBuf>, bool) {
    let mut files = Vec::new();
    for root in roots {
        let mut pending = vec![root.clone()];
        while let Some(current) = pending.pop() {
            let Ok(entries) = std::fs::read_dir(&current) else {
                continue;
            };
            let (mut directories, mut names) = (Vec::new(), Vec::new());
            for entry in entries.filter_map(Result::ok) {
                let name = entry.file_name().to_string_lossy().into_owned();
                let is_dir = entry.file_type().is_ok_and(|kind| kind.is_dir());
                let points_to_dir = entry.path().is_dir();
                if is_dir {
                    if !SKIP_DIRECTORIES.contains(&name.as_str()) && !name.starts_with('.') {
                        directories.push(name);
                    }
                } else if !points_to_dir {
                    names.push(name);
                }
            }
            names.sort_by_key(|name| casefold(name));
            for name in names {
                if !casefold(&name).ends_with(".md") {
                    continue;
                }
                files.push(current.join(&name));
                if files.len() >= max_files {
                    return (files, true);
                }
            }
            directories.sort();
            pending.extend(directories.into_iter().rev().map(|name| current.join(name)));
        }
    }
    (files, false)
}

pub struct Options {
    pub roots: Vec<PathBuf>,
    pub source: Option<PathBuf>,
    pub source_sha256: Option<String>,
    pub limit: i64,
    pub max_files: i64,
}

pub fn locate(options: &Options) -> Result<Value, String> {
    let roots = options
        .roots
        .iter()
        .map(|root| {
            let expanded = home(&root.to_string_lossy());
            std::fs::canonicalize(&expanded)
                .map_err(|error| format!("{}: {error}", expanded.display()))
        })
        .collect::<Result<Vec<_>, _>>()?;
    if roots.is_empty() || roots.iter().any(|root| !root.is_dir()) {
        return Err("At least one existing search root is required".into());
    }
    if !(1..=1000).contains(&options.limit) {
        return Err("limit must be between 1 and 1000".into());
    }
    if !(1..=100_000).contains(&options.max_files) {
        return Err("max_files must be between 1 and 100000".into());
    }
    let source = match &options.source {
        Some(path) => {
            let expanded = home(&path.to_string_lossy());
            let real = std::fs::canonicalize(&expanded)
                .map_err(|error| format!("{}: {error}", expanded.display()))?;
            if !real.is_file() {
                return Err(format!("Source is not a file: {}", real.display()));
            }
            Some(real)
        }
        None => None,
    };
    let expected = match (&options.source_sha256, &source) {
        (Some(hash), _) if !hash.is_empty() => hash.to_lowercase(),
        (_, Some(path)) => sha256_file(path)?,
        _ => String::new(),
    };
    if !expected.is_empty()
        && !Regex::new(r"^[0-9a-f]{64}$")
            .expect("valid regex")
            .is_match(&expected)
    {
        return Err("source_sha256 must be 64 hexadecimal characters".into());
    }
    if source.is_none() && expected.is_empty() {
        return Err("Provide source or source_sha256".into());
    }
    let source_path = source
        .as_ref()
        .map(|path| normalized(&path.to_string_lossy()));
    let source_name = source
        .as_ref()
        .map(|path| casefold(&path.file_name().unwrap_or_default().to_string_lossy()));
    let (files, scan_truncated) = markdown_files(&roots, options.max_files as usize);
    let mut candidates: Vec<(u8, Value)> = Vec::new();
    let mut errors = Vec::new();
    for markdown in &files {
        let text = std::fs::read(markdown)
            .map_err(|error| error.to_string())
            .and_then(|bytes| {
                let body = bytes
                    .strip_prefix(b"\xEF\xBB\xBF")
                    .unwrap_or(&bytes)
                    .to_vec();
                std::str::from_utf8(&body)
                    .map(str::to_string)
                    .map_err(|error| crate::text::utf8_error(&body, error))
            });
        let text = match text {
            Ok(text) => text.replace("\r\n", "\n").replace('\r', "\n"),
            Err(error) => {
                errors.push(json!({"path": markdown.to_string_lossy(), "error": error}));
                continue;
            }
        };
        for record in metadata_records(&text) {
            let recorded_hash = record
                .source_sha256
                .clone()
                .unwrap_or_default()
                .to_lowercase();
            let path_match = source_path
                .as_ref()
                .is_some_and(|path| normalized(&record.source) == *path);
            let hash_match = !expected.is_empty() && recorded_hash == expected;
            let name_match = source_name
                .as_ref()
                .is_some_and(|name| casefold(&file_name(&record.source)) == *name);
            if !(path_match || hash_match || name_match) {
                continue;
            }
            let (status, rank) = if hash_match {
                ("current", 0)
            } else if path_match && !recorded_hash.is_empty() {
                ("stale", 1)
            } else {
                ("candidate", 2)
            };
            let reasons: Vec<&str> = [
                (path_match, "source_path"),
                (hash_match, "source_sha256"),
                (name_match, "source_filename"),
            ]
            .iter()
            .filter(|(matched, _)| *matched)
            .map(|(_, reason)| *reason)
            .collect();
            let resolved = std::fs::canonicalize(markdown).unwrap_or(markdown.clone());
            candidates.push((
                rank,
                json!({"markdown": resolved.to_string_lossy(), "recorded_source": record.source,
                    "recorded_source_sha256": if recorded_hash.is_empty() { Value::Null } else { recorded_hash.into() },
                    "extracted_on": record.extracted_on, "status": status, "match_reasons": reasons}),
            ));
        }
    }
    candidates.sort_by(|(rank_a, a), (rank_b, b)| {
        let key = |row: &Value, field: &str| casefold(row[field].as_str().unwrap_or(""));
        rank_a
            .cmp(rank_b)
            .then_with(|| key(a, "markdown").cmp(&key(b, "markdown")))
            .then_with(|| key(a, "recorded_source").cmp(&key(b, "recorded_source")))
    });
    let count = candidates.len();
    let selected: Vec<Value> = candidates
        .into_iter()
        .take(options.limit as usize)
        .map(|(_, row)| row)
        .collect();
    Ok(json!({
        "source": source.as_ref().map(|path| path.to_string_lossy().into_owned()),
        "source_sha256": if expected.is_empty() { Value::Null } else { expected.into() },
        "roots": roots.iter().map(|root| root.to_string_lossy().into_owned()).collect::<Vec<_>>(),
        "candidates": selected,
        "candidate_count": count,
        "candidate_truncated": count > options.limit as usize,
        "scanned_markdown_files": files.len(),
        "scan_truncated": scan_truncated,
        "errors": errors,
    }))
}

/// Output, stderr and exit code: 0 complete, 1 unreadable candidates, 2 invalid input.
pub fn run(options: &Options) -> (String, String, i32) {
    match locate(options) {
        Ok(result) => {
            let code = i32::from(
                result["errors"]
                    .as_array()
                    .is_some_and(|rows| !rows.is_empty()),
            );
            (crate::text::pretty(&result), String::new(), code)
        }
        Err(message) => (String::new(), format!("error: {message}"), 2),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_single_and_combined_records() {
        let hash = "A".repeat(64);
        let text = format!(
            "- Source: `C:/a b.pdf`\n- Source SHA-256: `{hash}`\n- Extracted on: 2026-01-01\n- `x.docx` (DOCX, SHA-256 `{}`)\n",
            "b".repeat(64)
        );
        let records = metadata_records(&text);
        assert_eq!(records.len(), 2);
        assert_eq!(records[0].source, "C:/a b.pdf");
        assert_eq!(
            records[0].source_sha256.as_deref(),
            Some("a".repeat(64).as_str())
        );
        assert_eq!(records[0].extracted_on.as_deref(), Some("2026-01-01"));
        assert_eq!(records[1].source, "x.docx");
    }

    #[test]
    fn ranks_current_before_candidates() {
        let dir = tempfile::tempdir().unwrap();
        let source = dir.path().join("spec.pdf");
        std::fs::write(&source, b"pdf").unwrap();
        let hash = sha256_file(&source).unwrap();
        std::fs::create_dir(dir.path().join("out")).unwrap();
        std::fs::write(dir.path().join("out/a.md"), "- Source: other/spec.pdf\n").unwrap();
        std::fs::write(
            dir.path().join("out/b.md"),
            format!("- Source: x\n- Source SHA-256: {hash}\n"),
        )
        .unwrap();
        let result = locate(&Options {
            roots: vec![dir.path().join("out")],
            source: Some(source),
            source_sha256: None,
            limit: 50,
            max_files: 100,
        })
        .unwrap();
        let rows = result["candidates"].as_array().unwrap();
        assert_eq!(rows[0]["status"], "current");
        assert_eq!(rows[1]["status"], "candidate");
        assert_eq!(result["scanned_markdown_files"], 2);
    }
}
