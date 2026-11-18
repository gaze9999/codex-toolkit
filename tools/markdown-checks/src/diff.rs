//! Compare Markdown headings, list items and table rows without remote reads or writes.
use crate::text::{pretty, sha256, split_lines};
use regex::Regex;
use serde_json::{json, Map, Value};
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

const KINDS: [&str; 3] = ["headings", "list_items", "table_rows"];

pub fn tokens(text: &str) -> [Vec<String>; 3] {
    let fence_re = Regex::new(r"^ {0,3}(`{3,}|~{3,})(.*)$").unwrap();
    let heading = Regex::new(r"^#{1,6} ").unwrap();
    let list = Regex::new(r"^(?:[-*+] |\d+[.)] )").unwrap();
    let rule = Regex::new(r"^\|[ :|-]+\|$").unwrap();
    let spaces = Regex::new(r"\s+").unwrap();
    let mut result: [Vec<String>; 3] = Default::default();
    let mut fence: Option<(char, usize)> = None;
    for raw in split_lines(text.trim_start_matches('\u{feff}')) {
        if let Some(captures) = fence_re.captures(raw) {
            let run = &captures[1];
            let tail = &captures[2];
            let mark = run.chars().next().unwrap();
            match fence {
                None => fence = Some((mark, run.len())),
                Some((open, size))
                    if mark == open && run.len() >= size && tail.trim().is_empty() =>
                {
                    fence = None
                }
                _ => {}
            }
            continue;
        }
        if fence.is_some() {
            continue;
        }
        let line = spaces.replace_all(raw.trim(), " ").into_owned();
        if heading.is_match(&line) {
            result[0].push(line);
        } else if list.is_match(&line) {
            result[1].push(line);
        } else if line.starts_with('|') && line.ends_with('|') && !rule.is_match(&line) {
            result[2].push(line);
        }
    }
    result
}

fn counts(items: &[String]) -> BTreeMap<&str, usize> {
    let mut map = BTreeMap::new();
    for item in items {
        *map.entry(item.as_str()).or_insert(0) += 1;
    }
    map
}

/// Items that occur more often in `left` than in `right`, repeated by the surplus and sorted.
fn only(left: &BTreeMap<&str, usize>, right: &BTreeMap<&str, usize>) -> Vec<String> {
    let mut out = Vec::new();
    for (item, count) in left {
        let extra = count.saturating_sub(*right.get(item).unwrap_or(&0));
        out.extend(std::iter::repeat_n(item.to_string(), extra));
    }
    out
}

pub fn run(left: &Path, right: &Path) -> Result<String, String> {
    if !left.is_file() || !right.is_file() {
        return Err("Both inputs must be existing Markdown files".into());
    }
    let read = |path: &Path| -> Result<(Vec<u8>, String), String> {
        let bytes = fs::read(path).map_err(|error| error.to_string())?;
        let text = String::from_utf8(bytes.clone()).map_err(|error| error.to_string())?;
        Ok((bytes, text))
    };
    let ((left_bytes, left_text), (right_bytes, right_text)) = (read(left)?, read(right)?);
    let (left_tokens, right_tokens) = (tokens(&left_text), tokens(&right_text));
    let mut changes = Map::new();
    for (index, kind) in KINDS.iter().enumerate() {
        let (l, r) = (counts(&left_tokens[index]), counts(&right_tokens[index]));
        changes.insert(
            kind.to_string(),
            json!({
                "only_left": only(&l, &r), "only_right": only(&r, &l),
                "order_changed": l == r && left_tokens[index] != right_tokens[index],
            }),
        );
    }
    let report = json!({
        "left": left.to_string_lossy(), "right": right.to_string_lossy(),
        "left_sha256": sha256(&left_bytes), "right_sha256": sha256(&right_bytes), "changes": Value::Object(changes),
    });
    Ok(pretty(&report))
}
