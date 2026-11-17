//! Stable candidate IDs and the merge of semantic evidence (`code-health-evidence/1`).
//! A language server or reviewer checks candidates by ID; the scan stays syntax-level and
//! records each result beside the candidate without changing the candidate lists.
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

pub const SCHEMA: &str = "code-health-evidence/1";
pub const SOURCE_SCHEMA: &str = "code-health-evidence/2";

pub fn source_path(path: &Path) -> String {
    let name = path.to_string_lossy();
    if cfg!(windows) {
        name.replace('\\', "/")
    } else {
        name.into_owned()
    }
}

pub fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
/// Evidence states: the candidate holds (no consumer found), is refuted (a consumer exists),
/// or the provider could not answer.
pub const STATUSES: [&str; 5] = ["confirmed", "refuted", "unsupported", "timeout", "error"];
const ITEM_LIMIT: usize = 5000;
const LOCATION_LIMIT: usize = 50;
const TEXT_LIMIT: usize = 2000;

fn text(value: &Value) -> &str {
    value.as_str().unwrap_or("")
}

/// Assigns readable IDs that survive edits elsewhere in the file: kind, path and symbol, with a
/// numeric suffix only when the same key repeats.
pub fn assign_ids(report: &mut Value) {
    let mut seen = BTreeMap::<String, usize>::new();
    let mut unique = |base: String| {
        let count = seen.entry(base.clone()).or_insert(0);
        *count += 1;
        if *count == 1 {
            base
        } else {
            format!("{base}~{count}")
        }
    };
    if let Some(rows) = report["unused"].as_array_mut() {
        for row in rows {
            let path = text(&row["path"]);
            let base = match text(&row["kind"]) {
                "file" => format!("file:{path}"),
                "member" => format!(
                    "member:{path}#{}.{}",
                    text(&row["class"]),
                    text(&row["name"])
                ),
                kind => format!("{kind}:{path}#{}", text(&row["name"])),
            };
            row["id"] = json!(unique(base));
        }
    }
    if let Some(rows) = report["needs_review"].as_array_mut() {
        for row in rows {
            let path = text(&row["path"]);
            let symbol = text(&row["symbol"]);
            let base = if !symbol.is_empty() {
                format!("review:{path}#{symbol}")
            } else if let Some(line) = row["line"].as_u64() {
                format!("review:{path}@{line}")
            } else if path.is_empty() {
                // A note about the whole scan, such as unresolved entry points
                "review:scan".to_owned()
            } else {
                format!("review:{path}")
            };
            row["id"] = json!(unique(base));
        }
    }
}

fn bounded_text(item: &Value, key: &str) -> Result<Option<String>, String> {
    match &item[key] {
        Value::Null => Ok(None),
        Value::String(value) if value.chars().count() <= TEXT_LIMIT => Ok(Some(value.clone())),
        _ => Err(format!(
            "Evidence {key} must be a string of at most {TEXT_LIMIT} characters"
        )),
    }
}

/// Validates one evidence item and keeps only the documented fields.
fn clean(item: &Value) -> Result<(String, Value), String> {
    let id = item["id"]
        .as_str()
        .filter(|id| !id.is_empty())
        .ok_or("Each evidence item needs an id")?;
    let status = text(&item["status"]);
    if !STATUSES.contains(&status) {
        return Err(format!(
            "Evidence {id} status must be one of {}",
            STATUSES.join(", ")
        ));
    }
    let mut kept = Map::new();
    kept.insert("status".into(), json!(status));
    for key in ["provider", "provider_version", "coverage", "note"] {
        if let Some(value) = bounded_text(item, key)? {
            kept.insert(key.into(), json!(value));
        }
    }
    match &item["references"] {
        Value::Null => {}
        value => {
            let count = value
                .as_u64()
                .ok_or_else(|| format!("Evidence {id} references must be a whole number"))?;
            kept.insert("references".into(), json!(count));
        }
    }
    if let Some(locations) = item.get("locations") {
        let rows = locations
            .as_array()
            .filter(|rows| rows.len() <= LOCATION_LIMIT)
            .ok_or_else(|| {
                format!("Evidence {id} locations must be a list of at most {LOCATION_LIMIT}")
            })?;
        let mut cleaned = Vec::new();
        for row in rows {
            let path = row["path"]
                .as_str()
                .filter(|path| !path.is_empty() && path.chars().count() <= TEXT_LIMIT)
                .ok_or_else(|| format!("Evidence {id} locations need a path"))?;
            let line = row["line"]
                .as_u64()
                .filter(|line| *line > 0)
                .ok_or_else(|| format!("Evidence {id} locations need a line from 1"))?;
            cleaned.push(json!({"path":path,"line":line}));
        }
        kept.insert("locations".into(), json!(cleaned));
    }
    Ok((id.to_owned(), Value::Object(kept)))
}

/// Attaches evidence to candidates with matching IDs and summarizes the result under `semantic`.
pub fn merge(report: &mut Value, evidence: &Value) -> Result<(), String> {
    let schema = text(&evidence["schema"]);
    if ![SCHEMA, SOURCE_SCHEMA].contains(&schema) {
        return Err(format!(
            "Expected evidence schema {SCHEMA} or {SOURCE_SCHEMA}"
        ));
    }
    let source_bound = schema == SOURCE_SCHEMA;
    if source_bound
        && (!evidence["root"].is_string()
            || !evidence["source_files"].is_object()
            || evidence["source_files"] != report["source_files"])
    {
        return Err(
            "Evidence sources differ from the current scan; regenerate the evidence".into(),
        );
    }
    if let Some(root) = evidence["root"].as_str() {
        let same = Path::new(root)
            .canonicalize()
            .is_ok_and(|root| root == Path::new(text(&report["root"])));
        if !same {
            return Err("Evidence root differs from the scan root".into());
        }
    }
    let items = evidence["items"]
        .as_array()
        .filter(|items| items.len() <= ITEM_LIMIT)
        .ok_or_else(|| format!("Evidence items must be a list of at most {ITEM_LIMIT}"))?;
    let mut by_id = BTreeMap::new();
    for item in items {
        let (id, mut kept) = clean(item)?;
        if source_bound
            && matches!(text(&kept["status"]), "confirmed" | "refuted")
            && !item["position"].is_object()
        {
            return Err(format!("Evidence {id} is missing its source position"));
        }
        if source_bound && item.get("position").is_some() {
            kept["position"] = item["position"].clone();
        }
        if by_id.insert(id.clone(), kept).is_some() {
            return Err(format!("Evidence {id} appears more than once"));
        }
    }
    let mut counts: BTreeMap<&str, usize> = STATUSES.iter().map(|status| (*status, 0)).collect();
    counts.insert("unchecked", 0);
    let mut matched = BTreeSet::new();
    for section in ["unused", "needs_review"] {
        for row in report[section].as_array_mut().into_iter().flatten() {
            let id = text(&row["id"]).to_owned();
            match by_id.get(&id) {
                Some(found) => {
                    if let Some(position) = found.get("position") {
                        if position
                            != &json!({"path":row["path"],"line":row["line"],"column":row["column"]})
                        {
                            return Err(format!(
                                "Evidence {id} refers to a different source position"
                            ));
                        }
                    }
                    *counts.get_mut(text(&found["status"])).unwrap() += 1;
                    row["semantic"] = found.clone();
                    matched.insert(id);
                }
                None => *counts.get_mut("unchecked").unwrap() += 1,
            }
        }
    }
    // Unmatched IDs usually mean the evidence came from another scan or the code changed since
    let unmatched: Vec<&String> = by_id.keys().filter(|id| !matched.contains(*id)).collect();
    report["semantic"] = json!({"schema":schema,"counts":counts,"unmatched":unmatched,"freshness":
            if !source_bound { "unverified" }
            else if report["partial"] == true || !unmatched.is_empty() { "partial" }
            else { "matched_scan_sources" }});
    Ok(())
}
