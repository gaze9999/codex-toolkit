//! The few lines a caller needs from a scan; the full result goes to the report files.
use serde_json::Value;
use std::collections::BTreeMap;

fn rows<'a>(report: &'a Value, key: &str) -> Option<&'a Vec<Value>> {
    report[key].as_array()
}
fn text(value: &Value) -> &str {
    value.as_str().unwrap_or("")
}

/// Names with the most rows, as `name (count)`.
fn top(rows: &[Value], key: &str, limit: usize) -> String {
    let mut counts = BTreeMap::<&str, usize>::new();
    for row in rows {
        *counts.entry(text(&row[key])).or_default() += 1;
    }
    let mut ranked: Vec<(&str, usize)> = counts.into_iter().collect();
    ranked.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(b.0)));
    ranked
        .iter()
        .take(limit)
        .map(|(name, count)| format!("{name} ({count})"))
        .collect::<Vec<_>>()
        .join(", ")
}

pub fn summary(report: &Value) -> Vec<String> {
    let mut lines = vec![format!(
        "code-health: {} files, coverage {}",
        report["files_scanned"],
        if report["partial"] == true {
            "partial"
        } else {
            "complete"
        }
    )];
    if let Some(unused) = rows(report, "unused") {
        let mut kinds = BTreeMap::<&str, usize>::new();
        for row in unused {
            *kinds.entry(text(&row["kind"])).or_default() += 1;
        }
        let detail: Vec<String> = kinds.iter().map(|(k, n)| format!("{k} {n}")).collect();
        lines.push(if unused.is_empty() {
            "unused 0".into()
        } else {
            format!(
                "unused {} ({}); most in {}",
                unused.len(),
                detail.join(", "),
                top(unused, "path", 3)
            )
        });
    }
    if let Some(groups) = rows(report, "duplicates") {
        let regions: usize = groups
            .iter()
            .map(|group| group["regions"].as_array().map_or(0, Vec::len))
            .sum();
        lines.push(format!(
            "duplicates {regions} regions in {} file pairs",
            groups.len()
        ));
    }
    if let Some(functions) = rows(report, "complexity") {
        // Rows arrive ordered by branch count, then length
        lines.push(match functions.first() {
            None => "complexity: no function found".into(),
            Some(first) => format!(
                "complexity: {} functions; most branches {} in {} {} ({} lines)",
                functions.len(),
                first["branches"],
                text(&first["path"]),
                text(&first["name"]),
                first["lines"]
            ),
        });
    }
    if let Some(review) = rows(report, "needs_review") {
        lines.push(format!("needs_review {}", review.len()));
    }
    if let Some(semantic) = report.get("semantic") {
        let count = |key: &str| semantic["counts"][key].as_u64().unwrap_or(0);
        lines.push(format!(
            "semantic: confirmed {}, refuted {}, unanswered {}, unchecked {}, unmatched evidence {}",
            count("confirmed"),
            count("refuted"),
            count("unsupported") + count("timeout") + count("error"),
            count("unchecked"),
            semantic["unmatched"].as_array().map_or(0, Vec::len)
        ));
    }
    lines
}
