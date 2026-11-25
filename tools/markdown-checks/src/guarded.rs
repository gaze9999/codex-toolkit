//! Guarded Markdown section replacement and marked history appends for one local target.
use crate::text::{compact, sha256};
use regex::Regex;
use serde_json::{json, Map, Value};
use std::fs;
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};

pub const DEFAULT_NAMESPACE: &str = "project-task";

/// One ATX heading outside fenced code: level, title and byte offset of its line.
#[derive(Debug, Clone, PartialEq)]
pub struct Heading {
    pub level: usize,
    pub title: String,
    pub offset: usize,
}

impl Heading {
    pub fn label(&self) -> String {
        format!("{} {}", "#".repeat(self.level), self.title)
    }
}

/// Python `str.splitlines(keepends=True)`.
fn lines_with_ends(text: &str) -> Vec<&str> {
    let mut lines = Vec::new();
    let mut start = 0;
    let mut chars = text.char_indices().peekable();
    while let Some((index, ch)) = chars.next() {
        if crate::text::is_break(ch) {
            let mut end = index + ch.len_utf8();
            if ch == '\r' {
                if let Some((_, '\n')) = chars.peek().copied() {
                    chars.next();
                    end += 1;
                }
            }
            lines.push(&text[start..end]);
            start = end;
        }
    }
    if start < text.len() {
        lines.push(&text[start..]);
    }
    lines
}

pub fn headings(text: &str) -> Vec<Heading> {
    let fence_re = Regex::new(r"^ {0,3}(`{3,}|~{3,})(.*)$").expect("valid regex");
    let heading_re = Regex::new(r"^(#{1,6})[ \t]+(.+?)[ \t]*$").expect("valid regex");
    let closing = Regex::new(r"[ \t]+#+$").expect("valid regex");
    let (mut result, mut offset, mut fence) = (Vec::new(), 0, None::<(char, usize)>);
    for line in lines_with_ends(text) {
        let body = line.trim_end_matches(['\r', '\n']);
        if let Some(found) = fence_re.captures(body) {
            let run = &found[1];
            let mark = run.chars().next().unwrap_or('`');
            match fence {
                None => fence = Some((mark, run.len())),
                Some((open, size))
                    if mark == open && run.len() >= size && found[2].trim().is_empty() =>
                {
                    fence = None
                }
                _ => {}
            }
        } else if fence.is_none() {
            if let Some(found) = heading_re.captures(body) {
                result.push(Heading {
                    level: found[1].len(),
                    title: closing.replace(&found[2], "").into_owned(),
                    offset,
                });
            }
        }
        offset += line.len();
    }
    result
}

/// Byte range of the section whose heading line equals `heading` exactly once.
pub fn section(text: &str, heading: &str) -> Result<(usize, usize), String> {
    let found = headings(text);
    let matches: Vec<usize> = (0..found.len())
        .filter(|index| found[*index].label() == heading)
        .collect();
    let [index] = matches.as_slice() else {
        return Err("Section heading must match exactly once; inspect headings first".into());
    };
    let level = found[*index].level;
    let end = found[index + 1..]
        .iter()
        .find(|item| item.level <= level)
        .map_or(text.len(), |item| item.offset);
    Ok((found[*index].offset, end))
}

pub struct Target {
    pub raw: Vec<u8>,
    pub text: String,
    pub bom: bool,
}

pub fn read_target(path: &Path) -> Result<Target, String> {
    let raw = fs::read(path).map_err(|error| format!("{}: {error}", path.display()))?;
    let bom = raw.starts_with(b"\xEF\xBB\xBF");
    let body = if bom { &raw[3..] } else { &raw[..] };
    let text = std::str::from_utf8(body)
        .map_err(|_| format!("{}: target is not valid UTF-8", path.display()))?
        .to_string();
    Ok(Target { raw, text, bom })
}

/// New file bytes for a section replacement (`heading`) or a marked append (`entry_id`).
pub fn prepare(
    target: &Target,
    content: &str,
    heading: Option<&str>,
    entry_id: Option<&str>,
    namespace: &str,
) -> Result<Vec<u8>, String> {
    let text = &target.text;
    let nl = if text.contains("\r\n") { "\r\n" } else { "\n" };
    let content = format!(
        "{}\n",
        content.replace("\r\n", "\n").replace('\r', "\n").trim()
    );
    if content.trim().is_empty() {
        return Err("Empty content is not allowed".into());
    }
    let output = if let Some(heading) = heading {
        let (start, end) = section(text, heading)?;
        let found = headings(&content);
        let first = found
            .first()
            .filter(|item| item.offset == 0 && item.label() == heading);
        let Some(first) = first else {
            return Err("Replacement must start with the exact section heading".into());
        };
        if found[1..].iter().any(|item| item.level <= first.level) {
            return Err("Replacement must contain only the selected section".into());
        }
        let tail = if end < text.len() { nl } else { "" };
        format!(
            "{}{}{}{}",
            &text[..start],
            content.replace('\n', nl),
            tail,
            &text[end..]
        )
    } else {
        let entry_id = entry_id.unwrap_or("");
        let valid = Regex::new(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$").expect("valid regex");
        if !valid.is_match(entry_id) {
            return Err(
                "entry-id must be 1-101 ASCII letters/digits/dots/dashes/underscores".into(),
            );
        }
        if Regex::new(r"<!-- /?[A-Za-z0-9._-]+:")
            .expect("valid regex")
            .is_match(&content)
        {
            return Err("Content must not supply task markers".into());
        }
        let existing_re = Regex::new(&format!(
            r"<!-- ([A-Za-z0-9._-]+):{} -->",
            regex::escape(entry_id)
        ))
        .expect("valid regex");
        let existing: Vec<String> = existing_re
            .captures_iter(text)
            .map(|found| found[1].to_string())
            .collect();
        if existing.len() > 1 {
            return Err("entry-id occurs more than once; inspect history".into());
        }
        // Existing records keep their original namespace when the setting changes.
        let namespace = existing.first().map_or(namespace, String::as_str);
        let marker = format!("<!-- {namespace}:{entry_id} -->");
        let close = format!("<!-- /{namespace}:{entry_id} -->");
        let block = format!("{marker}{nl}{}{close}{nl}", content.replace('\n', nl));
        if text.contains(&marker) {
            if text.matches(&marker).count() == 1
                && text.matches(&close).count() == 1
                && text.contains(&block)
            {
                return Ok(target.raw.clone());
            }
            return Err(
                "entry-id already exists with different content; do not duplicate it".into(),
            );
        }
        let double = format!("{nl}{nl}");
        let gap = if text.is_empty() || text.ends_with(&double) {
            String::new()
        } else if text.ends_with(nl) {
            nl.to_string()
        } else {
            double
        };
        format!("{text}{gap}{block}")
    };
    let mut bytes = if target.bom {
        b"\xEF\xBB\xBF".to_vec()
    } else {
        Vec::new()
    };
    bytes.extend_from_slice(output.as_bytes());
    Ok(bytes)
}

fn sibling(path: &Path, label: &str) -> Result<(PathBuf, fs::File), String> {
    let parent = path.parent().unwrap_or(Path::new("."));
    let name = path.file_name().unwrap_or_default().to_string_lossy();
    (0..100u32)
        .map(|attempt| parent.join(format!(".{name}.{label}-{}-{attempt}", std::process::id())))
        .find_map(|candidate| {
            fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&candidate)
                .ok()
                .map(|file| (candidate, file))
        })
        .ok_or("Could not create a temporary file beside the target".into())
}

/// Explicit fallback for cloud placeholders: backup, guarded non-atomic write, readback.
fn write_in_place(path: &Path, before: &[u8], after: &[u8]) -> Result<(), String> {
    let (backup, mut file) = sibling(path, "backup")?;
    file.write_all(before)
        .and_then(|()| file.sync_all())
        .map_err(|error| error.to_string())?;
    let result = (|| -> Result<(), String> {
        let mut handle = fs::OpenOptions::new()
            .read(true)
            .write(true)
            .open(path)
            .map_err(|error| error.to_string())?;
        let mut current = Vec::new();
        handle
            .read_to_end(&mut current)
            .map_err(|error| error.to_string())?;
        if current != before {
            return Err("Target changed; re-inspect and merge".into());
        }
        handle
            .seek(SeekFrom::Start(0))
            .and_then(|_| handle.write_all(after))
            .and_then(|()| handle.set_len(after.len() as u64))
            .and_then(|()| handle.sync_all())
            .map_err(|error| error.to_string())?;
        if fs::read(path).map_err(|error| error.to_string())? != after {
            return Err("Post-write mismatch".into());
        }
        Ok(())
    })();
    match result {
        Ok(()) => {
            let _ = fs::remove_file(&backup);
            Ok(())
        }
        Err(error) => Err(format!(
            "In-place write unverified; inspect target before retry. Backup: {}; {error}",
            backup.display()
        )),
    }
}

/// Optimistic guard, atomic single-file replacement with the original permissions, exact readback.
pub fn write_guarded(
    path: &Path,
    before: &[u8],
    after: &[u8],
    in_place: bool,
) -> Result<(), String> {
    if in_place {
        return write_in_place(path, before, after);
    }
    let permissions = fs::metadata(path)
        .map_err(|error| error.to_string())?
        .permissions();
    let (temporary, mut file) = sibling(path, "tmp")?;
    let result = (|| -> Result<(), String> {
        file.write_all(after)
            .and_then(|()| file.sync_all())
            .and_then(|()| fs::set_permissions(&temporary, permissions))
            .map_err(|error| error.to_string())?;
        if fs::read(path).map_err(|error| error.to_string())? != before {
            return Err("Target changed during preparation; re-inspect and merge".into());
        }
        fs::rename(&temporary, path).map_err(|error| error.to_string())?;
        if fs::read(path).map_err(|error| error.to_string())? != after {
            return Err(
                "Post-write mismatch: write may have occurred; inspect before retry".into(),
            );
        }
        Ok(())
    })();
    if temporary.exists() {
        let _ = fs::remove_file(&temporary);
    }
    result
}

/// Namespace from the option, `TOOL_HISTORY_NAMESPACE` (process, then env file) or the default.
pub fn namespace(
    option: Option<&str>,
    env_file: Option<&Path>,
    warnings: &mut Vec<String>,
) -> String {
    let from_file = env_file.and_then(|path| {
        let Ok(text) = fs::read_to_string(path) else {
            warnings.push(format!("environment file not found: {}", path.display()));
            return None;
        };
        text.lines().find_map(|line| {
            let (key, value) = line.trim().split_once('=')?;
            (key.trim() == "TOOL_HISTORY_NAMESPACE").then(|| {
                let value = value.trim();
                value
                    .strip_prefix(['"', '\''])
                    .and_then(|inner| inner.strip_suffix(['"', '\'']))
                    .unwrap_or(value)
                    .to_string()
            })
        })
    });
    let process = std::env::var("TOOL_HISTORY_NAMESPACE")
        .ok()
        .filter(|value| !value.trim().is_empty());
    let value = option
        .map(str::to_string)
        .or(process)
        .or(from_file)
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| DEFAULT_NAMESPACE.into());
    if Regex::new(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
        .expect("valid regex")
        .is_match(&value)
    {
        value
    } else {
        warnings.push(format!(
            "invalid TOOL_HISTORY_NAMESPACE={value:?}; using {DEFAULT_NAMESPACE}"
        ));
        DEFAULT_NAMESPACE.into()
    }
}

pub enum Command {
    Inspect {
        section: Option<String>,
        out: Option<PathBuf>,
    },
    Replace {
        section: String,
    },
    Append {
        entry_id: String,
    },
}

pub struct Request {
    pub target_file: PathBuf,
    pub target: String,
    pub namespace: String,
    pub command: Command,
    pub content: Option<PathBuf>,
    pub expect: Option<String>,
    pub write: bool,
    pub in_place: bool,
}

fn absolute(path: &Path) -> PathBuf {
    let expanded = match path.strip_prefix("~") {
        Ok(rest) => std::env::var_os("HOME")
            .map(|home| PathBuf::from(home).join(rest))
            .unwrap_or_else(|| path.to_path_buf()),
        Err(_) => path.to_path_buf(),
    };
    fs::canonicalize(&expanded).unwrap_or(expanded)
}

fn execute(request: &Request) -> Result<Map<String, Value>, String> {
    let path = absolute(&request.target_file);
    let target = read_target(&path)?;
    let mut payload = Map::new();
    payload.insert("target".into(), request.target.clone().into());
    payload.insert("sha256".into(), sha256(&target.raw).into());
    if let Command::Inspect {
        section: wanted,
        out,
    } = &request.command
    {
        match (wanted, out) {
            (None, Some(_)) => return Err("--out requires --section".into()),
            (None, None) => {
                let labels: Vec<String> =
                    headings(&target.text).iter().map(Heading::label).collect();
                payload.insert("headings".into(), labels.into());
            }
            (Some(heading), out) => {
                let (start, end) = section(&target.text, heading)?;
                let selected = &target.text[start..end];
                match out {
                    Some(out) => {
                        let mut file = fs::OpenOptions::new()
                            .write(true)
                            .create_new(true)
                            .open(out)
                            .map_err(|error| format!("{}: {error}", out.display()))?;
                        file.write_all(selected.as_bytes())
                            .map_err(|error| error.to_string())?;
                        payload.insert("exported".into(), out.display().to_string().into());
                    }
                    None => {
                        payload.insert("content".into(), selected.into());
                    }
                }
            }
        }
        return Ok(payload);
    }
    let expect = request.expect.as_deref().unwrap_or("");
    if expect.to_lowercase() != sha256(&target.raw) {
        return Err("Stale SHA-256: re-inspect and merge before writing".into());
    }
    let content_path = request.content.as_deref().ok_or("--content is required")?;
    let content =
        fs::read(content_path).map_err(|error| format!("{}: {error}", content_path.display()))?;
    let content = content.strip_prefix(b"\xEF\xBB\xBF").unwrap_or(&content);
    let content = std::str::from_utf8(content).map_err(|_| "Content must be UTF-8".to_string())?;
    let (heading, entry) = match &request.command {
        Command::Replace { section } => (Some(section.as_str()), None),
        Command::Append { entry_id } => (None, Some(entry_id.as_str())),
        Command::Inspect { .. } => unreachable!(),
    };
    let after = prepare(&target, content, heading, entry, &request.namespace)?;
    let changed = after != target.raw;
    if request.write && changed {
        write_guarded(&path, &target.raw, &after, request.in_place)?;
    }
    let status = match (request.write && changed, changed) {
        (true, _) => "written",
        (false, false) => "unchanged",
        _ => "dry-run",
    };
    payload.insert("status".into(), status.into());
    payload.insert("next_sha256".into(), sha256(&after).into());
    payload.insert(
        "byte_delta".into(),
        (after.len() as i64 - target.raw.len() as i64).into(),
    );
    payload.insert("notion".into(), "not_performed".into());
    Ok(payload)
}

/// Single-line JSON and exit code: 0 success, 2 error.
pub fn run(request: &Request) -> (String, i32) {
    match execute(request) {
        Ok(payload) => (compact(&Value::Object(payload)), 0),
        Err(message) => (compact(&json!({"status": "error", "message": message})), 2),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn target(text: &str) -> Target {
        Target {
            raw: text.as_bytes().to_vec(),
            text: text.into(),
            bom: false,
        }
    }

    #[test]
    fn replaces_one_section_and_keeps_crlf() {
        let doc = target("# T\r\n## A\r\nold\r\n## B\r\nkeep\r\n");
        let out = prepare(&doc, "## A\nnew\n", Some("## A"), None, DEFAULT_NAMESPACE).unwrap();
        assert_eq!(
            String::from_utf8(out).unwrap(),
            "# T\r\n## A\r\nnew\r\n\r\n## B\r\nkeep\r\n"
        );
        assert!(prepare(&doc, "## B\nx", Some("## A"), None, DEFAULT_NAMESPACE).is_err());
        assert!(prepare(&doc, "## A\n## C\n", Some("## A"), None, DEFAULT_NAMESPACE).is_err());
    }

    #[test]
    fn appends_marked_entries_once() {
        let doc = target("# History\n");
        let out = prepare(&doc, "entry", None, Some("t-1"), "ns").unwrap();
        let text = String::from_utf8(out.clone()).unwrap();
        assert_eq!(
            text,
            "# History\n\n<!-- ns:t-1 -->\nentry\n<!-- /ns:t-1 -->\n"
        );
        let again = target(&text);
        assert_eq!(
            prepare(&again, "entry", None, Some("t-1"), "other").unwrap(),
            out
        );
        assert!(prepare(&again, "changed", None, Some("t-1"), "ns").is_err());
        assert!(prepare(&doc, "x", None, Some("-bad"), "ns").is_err());
    }

    #[test]
    fn ignores_headings_in_fences() {
        let found = headings("# A\n```\n# no\n```\n## B ##\n");
        let labels: Vec<String> = found.iter().map(Heading::label).collect();
        assert_eq!(labels, ["# A", "## B"]);
    }
}
