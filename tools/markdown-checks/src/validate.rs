//! Bounded ATX heading and code-fence checks; not a complete Markdown parser.
use crate::text::{split_lines, suffix};
use regex::Regex;
use serde_json::{json, Value};
use std::path::Path;

pub struct Report {
    pub checks: Vec<(String, String, String)>,
    pub failures: usize,
    pub warnings: usize,
}

impl Report {
    pub fn to_json(&self) -> Value {
        let checks: Vec<Value> = self
            .checks
            .iter()
            .map(|(status, check, detail)| json!({"status": status, "check": check, "detail": detail}))
            .collect();
        json!({"checks": checks, "failures": self.failures, "warnings": self.warnings})
    }
}

/// Opening or closing fence run after optional whitespace.
fn fence_run(line: &str) -> Option<(char, usize, usize)> {
    let body = line.trim_start();
    let first = body.chars().next().filter(|c| *c == '`' || *c == '~')?;
    let run = body.chars().take_while(|c| *c == first).count();
    (run >= 3).then(|| (first, run, line.len() - body.len() + run))
}

pub fn analyze(text: &str) -> Report {
    let heading = Regex::new(r"^(#{1,6})\s+(.+?)\s*$").expect("valid regex");
    let version = Regex::new(r"(?i)文件版本\s*[:：]\s*v\d+\b").expect("valid regex");
    let mut report = Report {
        checks: Vec::new(),
        failures: 0,
        warnings: 0,
    };
    let mut add = |status: &str, check: &str, detail: String| {
        report.checks.push((status.into(), check.into(), detail));
    };
    let lines = split_lines(text);
    let mut headings: Vec<(usize, usize, String)> = Vec::new();
    let mut fence: Option<(char, usize)> = None;
    for (index, line) in lines.iter().enumerate() {
        if let Some((mark, run, end)) = fence_run(line) {
            match fence {
                None => fence = Some((mark, run)),
                Some((open, size))
                    if mark == open && run >= size && line[end..].trim().is_empty() =>
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
        if let Some(found) = heading.captures(line) {
            headings.push((index + 1, found[1].len(), found[2].to_string()));
        }
    }
    let (mut failures, mut warnings) = (0, 0);
    if headings.is_empty() {
        warnings += 1;
        add("WARN", "headings", "no ATX headings detected".into());
    } else {
        add(
            "PASS",
            "headings",
            format!("found {} headings", headings.len()),
        );
    }
    let mut jumps = Vec::new();
    let mut previous: Option<usize> = None;
    for (line, level, title) in &headings {
        if let Some(before) = previous {
            if *level > before + 1 {
                jumps.push(format!("line {line}: H{before} -> H{level} ({title})"));
            }
        }
        previous = Some(*level);
    }
    if jumps.is_empty() {
        add(
            "PASS",
            "heading-hierarchy",
            "no skipped heading levels detected".into(),
        );
    } else {
        failures += 1;
        add(
            "FAIL",
            "heading-hierarchy",
            jumps[..jumps.len().min(5)].join("; "),
        );
    }
    if fence.is_some() {
        failures += 1;
        add("FAIL", "code-fences", "unclosed fenced code block".into());
    } else {
        add(
            "PASS",
            "code-fences",
            "fenced code blocks are balanced".into(),
        );
    }
    let trailing: Vec<String> = lines
        .iter()
        .enumerate()
        .filter(|(_, line)| {
            let spaces = line.len() - line.trim_end_matches(' ').len();
            line.ends_with('\t') || (spaces != 0 && spaces != 2)
        })
        .map(|(index, _)| (index + 1).to_string())
        .collect();
    if trailing.is_empty() {
        add("PASS", "trailing-whitespace", "none detected".into());
    } else {
        warnings += 1;
        add(
            "WARN",
            "trailing-whitespace",
            format!("lines: {}", trailing[..trailing.len().min(10)].join(", ")),
        );
    }
    if version.is_match(text) {
        add(
            "PASS",
            "document-version",
            "vX document version detected".into(),
        );
    } else {
        add(
            "INFO",
            "document-version",
            "no vX document version detected; acceptable unless the requested workflow requires one"
                .into(),
        );
    }
    report.failures = failures;
    report.warnings = warnings;
    report
}

/// ASCII output with `\xNN`, `\uNNNN` or `\UNNNNNNNN` escapes for other characters.
fn ascii(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for ch in text.chars() {
        let code = ch as u32;
        match code {
            0..=0x7f => out.push(ch),
            0x80..=0xff => out.push_str(&format!("\\x{code:02x}")),
            0x100..=0xffff => out.push_str(&format!("\\u{code:04x}")),
            _ => out.push_str(&format!("\\U{code:08x}")),
        }
    }
    out
}

/// Rendered report and exit code: 0 clean, 1 structural failure, 2 unreadable input.
pub fn run(path: &Path, as_json: bool) -> (String, i32) {
    let fail = |detail: &str| {
        if as_json {
            (json!({"status": "error", "message": detail}).to_string(), 2)
        } else {
            (format!("FAIL: {detail}"), 2)
        }
    };
    if !path.is_file() {
        return fail("file - file does not exist");
    }
    if !matches!(
        suffix(&path.to_string_lossy()).as_str(),
        ".md" | ".markdown"
    ) {
        return fail("extension - expected .md or .markdown");
    }
    let Ok(text) = std::fs::read(path)
        .ok()
        .and_then(|bytes| String::from_utf8(bytes).ok())
        .ok_or(())
    else {
        return fail("file - unable to read UTF-8 file");
    };
    // Text mode reading turns CRLF and lone CR into LF before line checks.
    let text = text.replace("\r\n", "\n").replace('\r', "\n");
    let report = analyze(&text);
    let code = i32::from(report.failures > 0);
    if as_json {
        return (crate::text::pretty(&report.to_json()), code);
    }
    let mut lines: Vec<String> = report
        .checks
        .iter()
        .map(|(status, check, detail)| ascii(&format!("{status}: {check} - {detail}")))
        .collect();
    lines.push(format!(
        "SUMMARY: failures={} warnings={}",
        report.failures, report.warnings
    ));
    (lines.join("\n"), code)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reports_jumps_fences_and_spacing() {
        let report = analyze("# A\n### C\n```\nopen  \n");
        assert_eq!(report.failures, 2);
        assert_eq!(report.checks[1].2, "line 2: H1 -> H3 (C)");
        let report = analyze("# A\n## B  \ntext \n文件版本: v2\n");
        assert_eq!((report.failures, report.warnings), (0, 1));
        assert_eq!(report.checks[3].2, "lines: 3");
        assert_eq!(report.checks[4].0, "PASS");
    }

    #[test]
    fn escapes_non_ascii() {
        assert_eq!(ascii("a é 中 😀"), "a \\xe9 \\u4e2d \\U0001f600");
    }
}
