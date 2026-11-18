//! Language-neutral structural checks on a reusable context brief.
use crate::text::{casefold, pretty, split_lines, suffix};
use regex::Regex;
use serde_json::json;
use std::fs;
use std::path::Path;

const SECRET_PATTERNS: [&str; 4] = [
    r"sk-[A-Za-z0-9_-]{20,}",
    r"ghp_[A-Za-z0-9_]{20,}",
    r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----",
    r#"(?i)\b(?:api[_-]?key|access[_-]?token|secret)\s*[:=]\s*['"]?[A-Za-z0-9_-]{16,}"#,
];
const TRACE: &str = r"(?im)https?://\S+|(?:[A-Za-z]:[\\/]|\.?\.?/)[^\s]+|^\s*(?:[-*]\s*)?(?:source|來源|出處|page|頁次|section|章節|row|列)\s*[:：]";

pub struct Check {
    pub status: &'static str,
    pub name: String,
    pub message: String,
}

fn check(status: &'static str, name: impl Into<String>, message: impl Into<String>) -> Check {
    Check {
        status,
        name: name.into(),
        message: message.into(),
    }
}

/// Headings outside fenced code as (line, level, title), plus whether every fence closed.
fn scan(text: &str) -> (Vec<(usize, usize, String)>, bool) {
    let fence_re = Regex::new(r"^\s*(`{3,}|~{3,})").unwrap();
    let heading_re = Regex::new(r"^(#{1,6})\s+(.+?)\s*#*\s*$").unwrap();
    let (mut headings, mut fence) = (Vec::new(), None::<(char, usize)>);
    for (index, line) in split_lines(text).into_iter().enumerate() {
        if let Some(found) = fence_re.captures(line) {
            let token = &found[1];
            let mark = token.chars().next().unwrap();
            let rest = &line[found.get(0).unwrap().end()..];
            match fence {
                None => fence = Some((mark, token.len())),
                Some((open, size))
                    if mark == open && token.len() >= size && rest.trim().is_empty() =>
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
        if let Some(found) = heading_re.captures(line) {
            headings.push((index + 1, found[1].len(), found[2].trim().to_string()));
        }
    }
    (headings, fence.is_none())
}

fn structure(headings: &[(usize, usize, String)]) -> Vec<Check> {
    if headings.is_empty() {
        return vec![check("FAIL", "headings", "no Markdown headings found")];
    }
    let mut checks = vec![check(
        "PASS",
        "headings",
        format!("found {} headings", headings.len()),
    )];
    checks.push(match headings[0].1 {
        1 => check("PASS", "title", "first heading is H1"),
        level => check(
            "WARN",
            "title",
            format!("first heading is H{level}, not H1"),
        ),
    });
    let jumps: Vec<String> = headings
        .windows(2)
        .filter(|pair| pair[1].1 > pair[0].1 + 1)
        .map(|pair| format!("line {}: H{} to H{}", pair[1].0, pair[0].1, pair[1].1))
        .collect();
    checks.push(if jumps.is_empty() {
        check("PASS", "heading_hierarchy", "no skipped heading levels")
    } else {
        check(
            "WARN",
            "heading_hierarchy",
            jumps.iter().take(5).cloned().collect::<Vec<_>>().join("; "),
        )
    });
    checks
}

pub fn validate(path: &Path, required: &[String], strict: bool) -> Result<Vec<Check>, String> {
    if !path.is_file() {
        return Ok(vec![check(
            "FAIL",
            "file",
            format!("file not found: {}", path.display()),
        )]);
    }
    let mut checks = Vec::new();
    if ![".md", ".markdown", ".txt"].contains(&suffix(&path.to_string_lossy()).as_str()) {
        checks.push(check("WARN", "extension", "expected a Markdown-like file"));
    }
    let bytes = fs::read(path).map_err(|error| error.to_string())?;
    let text = String::from_utf8(bytes).map_err(|error| error.to_string())?;
    if text.trim().is_empty() {
        return Ok(vec![check("FAIL", "content", "file is empty")]);
    }
    let (headings, balanced) = scan(&text);
    checks.extend(structure(&headings));
    checks.push(if balanced {
        check("PASS", "code_fences", "fenced code blocks are balanced")
    } else {
        check("FAIL", "code_fences", "fenced code block is not closed")
    });
    let folded: Vec<String> = headings
        .iter()
        .map(|heading| casefold(&heading.2))
        .collect();
    for expected in required {
        let name = format!("required_heading:{expected}");
        let wanted = casefold(expected);
        checks.push(if folded.iter().any(|title| title.contains(&wanted)) {
            check("PASS", name, "heading found")
        } else {
            check("FAIL", name, "heading not found")
        });
    }
    checks.push(if Regex::new(TRACE).unwrap().is_match(&text) {
        check(
            "PASS",
            "source_traceability",
            "source location marker found",
        )
    } else {
        check(
            "WARN",
            "source_traceability",
            "no URL, path, page, section, row, or source marker found",
        )
    });
    let secret = SECRET_PATTERNS
        .iter()
        .any(|pattern| Regex::new(pattern).unwrap().is_match(&text));
    checks.push(if secret {
        check(
            "FAIL",
            "secrets",
            "possible secret or credential pattern found",
        )
    } else {
        check("PASS", "secrets", "no common secret patterns found")
    });
    if strict {
        for item in &mut checks {
            if item.status == "WARN" {
                item.status = "FAIL";
            }
        }
    }
    Ok(checks)
}

/// Rendered output and exit code: 1 when any check fails.
pub fn report(checks: &[Check], as_json: bool) -> (String, i32) {
    let any = |status: &str| checks.iter().any(|item| item.status == status);
    let state = if any("FAIL") {
        "fail"
    } else if any("WARN") {
        "warn"
    } else {
        "pass"
    };
    let code = i32::from(any("FAIL"));
    if as_json {
        let rows: Vec<_> = checks
            .iter()
            .map(
                |item| json!({ "status": item.status, "name": item.name, "message": item.message }),
            )
            .collect();
        return (pretty(&json!({ "status": state, "checks": rows })), code);
    }
    let mut lines: Vec<String> = checks
        .iter()
        .map(|item| format!("{} {}: {}", item.status, item.name, item.message))
        .collect();
    lines.push(format!("SUMMARY: {}", state.to_uppercase()));
    (lines.join("\n"), code)
}
