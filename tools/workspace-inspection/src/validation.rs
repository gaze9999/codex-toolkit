//! Read and normalize validation evidence without replaying commands.
use serde_json::{json, Map, Value};
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

fn hex(value: &Value, min: usize, max: usize) -> bool {
    value.as_str().is_some_and(|text| {
        (min..=max).contains(&text.len()) && text.chars().all(|ch| ch.is_ascii_hexdigit())
    })
}

fn validate(value: &Map<String, Value>) -> Result<(), String> {
    for key in ["source_diff_sha256", "artifact_sha256"] {
        if value.get(key).is_some_and(|found| !hex(found, 64, 64)) {
            return Err(format!("invalid {key}"));
        }
    }
    if value
        .get("source_revision")
        .is_some_and(|found| !hex(found, 7, 64))
    {
        return Err("invalid source_revision".into());
    }
    if let Some(hashes) = value.get("source_files") {
        let valid = hashes.as_object().is_some_and(|hashes| {
            hashes
                .iter()
                .all(|(path, sha)| !path.is_empty() && hex(sha, 64, 64))
        });
        if !valid {
            return Err("invalid source_files".into());
        }
    }
    for key in ["affected_paths", "covered_paths"] {
        if let Some(found) = value.get(key) {
            let valid = found.as_array().is_some_and(|paths| {
                paths
                    .iter()
                    .all(|path| path.as_str().is_some_and(|path| !path.is_empty()))
            });
            if !valid {
                return Err(format!("invalid {key}"));
            }
        }
    }
    Ok(())
}

fn lower(value: &Value) -> String {
    value.as_str().unwrap_or("").to_lowercase()
}

fn verdict(status: &str, reasons: Vec<String>, uncovered: Vec<String>) -> Value {
    json!({"status":status,"scope":"supplied_source_and_artifact_provenance","reasons":reasons,"uncovered_paths":uncovered})
}

/// Compares explicitly supplied provenance; never reads files or replays commands.
pub fn assess_evidence(recorded: &Value, current: &Value) -> Result<Value, String> {
    let current = current
        .as_object()
        .ok_or("current baseline must be an object")?;
    validate(current)?;
    let Some(recorded) = recorded.as_object() else {
        return Ok(verdict(
            "unverified",
            vec!["recorded_baseline_missing_or_unstructured".into()],
            Vec::new(),
        ));
    };
    if validate(recorded).is_err() {
        return Ok(verdict(
            "unverified",
            vec!["recorded_baseline_malformed".into()],
            Vec::new(),
        ));
    }
    let empty = Map::new();
    let files = |value: &'_ Map<String, Value>| -> Map<String, Value> {
        value
            .get("source_files")
            .and_then(Value::as_object)
            .unwrap_or(&empty)
            .clone()
    };
    let (recorded_files, current_files) = (files(recorded), files(current));
    let mut reasons = Vec::new();
    let (mut changed, mut missing, mut matched) = (false, false, false);
    for (path, expected) in &recorded_files {
        match current_files.get(path) {
            None => {
                missing = true;
                reasons.push(format!("source_file_hash_missing:{path}"));
            }
            Some(actual) if lower(actual) != lower(expected) => {
                changed = true;
                reasons.push(format!("source_file_changed:{path}"));
            }
            Some(_) => matched = true,
        }
    }
    let mut identity = true;
    for key in ["source_revision", "source_diff_sha256"] {
        match (recorded.get(key), current.get(key)) {
            (Some(left), Some(right)) => {
                if lower(left) != lower(right) {
                    identity = false;
                    reasons.push(format!("{key}_changed"));
                }
            }
            _ => identity = false,
        }
    }
    if identity {
        matched = true;
    } else if recorded_files.is_empty() {
        matched = false;
        reasons.push("current_source_identity_not_established".into());
        changed = reasons.iter().any(|reason| {
            reason == "source_revision_changed" || reason == "source_diff_sha256_changed"
        });
    }
    if let Some(expected) = recorded.get("artifact_sha256") {
        match current.get("artifact_sha256") {
            None => {
                missing = true;
                reasons.push("artifact_hash_missing".into());
            }
            Some(actual) if lower(actual) != lower(expected) => {
                changed = true;
                reasons.push("artifact_changed".into());
            }
            Some(_) => {}
        }
    }
    let paths = |value: Option<&Value>| -> Option<BTreeSet<String>> {
        Some(
            value?
                .as_array()?
                .iter()
                .filter_map(Value::as_str)
                .map(str::to_owned)
                .collect(),
        )
    };
    let affected = paths(current.get("affected_paths"));
    let covered = paths(recorded.get("covered_paths"));
    let coverage_known = affected.is_some() && covered.is_some();
    let affected = affected.unwrap_or_default();
    let covered = covered.unwrap_or_default();
    let uncovered: Vec<String> = affected.difference(&covered).cloned().collect();
    if !coverage_known {
        reasons.push("affected_path_coverage_unknown".into());
    } else if !uncovered.is_empty() {
        reasons.push("affected_paths_not_covered".into());
    }
    if coverage_known
        && !identity
        && affected
            .iter()
            .any(|path| !recorded_files.contains_key(path))
    {
        missing = true;
        reasons.push("affected_source_hashes_missing".into());
    }
    let status = if changed {
        "outdated"
    } else if !matched {
        "unverified"
    } else if missing || !coverage_known || !uncovered.is_empty() {
        "partial"
    } else {
        "current"
    };
    Ok(verdict(status, reasons, uncovered))
}

/// One `results.json` with the fields the index reports.
pub fn read_run(path: &Path) -> Result<Value, String> {
    let text = fs::read_to_string(path).map_err(|e| e.to_string())?;
    let data: Value =
        serde_json::from_str(text.trim_start_matches('\u{feff}')).map_err(|e| e.to_string())?;
    let data = data.as_object().ok_or("top-level JSON must be an object")?;
    let results = match data.get("results") {
        None => &Vec::new(),
        Some(Value::Array(rows)) => rows,
        Some(_) => return Err("results must be an array".into()),
    };
    let mut normalized = Vec::new();
    for (index, row) in results.iter().enumerate() {
        let row = row
            .as_object()
            .ok_or_else(|| format!("results[{index}] must be an object"))?;
        let mut kept = Map::new();
        for key in [
            "name", "status", "reason", "command", "log", "source", "baseline",
        ] {
            kept.insert(key.into(), row.get(key).cloned().unwrap_or(Value::Null));
        }
        normalized.push(Value::Object(kept));
    }
    let field = |key: &str| data.get(key).cloned().unwrap_or(Value::Null);
    let run = path
        .parent()
        .and_then(Path::file_name)
        .map(|name| name.to_string_lossy().into_owned())
        .unwrap_or_default();
    let resolved = fs::canonicalize(path).unwrap_or_else(|_| path.to_path_buf());
    let mut result = Map::new();
    result.insert("run".into(), json!(run));
    result.insert("path".into(), json!(resolved.to_string_lossy()));
    result.insert("started".into(), field("started"));
    result.insert("source".into(), field("source"));
    result.insert("baseline".into(), field("baseline"));
    result.insert("results".into(), json!(normalized));
    result.insert(
        "unverified".into(),
        data.get("unverified").cloned().unwrap_or(json!([])),
    );
    Ok(Value::Object(result))
}

/// Indexes `run-*/results.json` below `root`, newest name first. With `current`, each run and
/// result also carries a validity verdict against that baseline.
pub fn index_evidence(root: &Path, limit: i64, current: Option<&Value>) -> Result<Value, String> {
    if let Some(current) = current {
        assess_evidence(&Value::Null, current)?;
    }
    let root = fs::canonicalize(root).map_err(|e| format!("{}: {e}", root.display()))?;
    if !root.is_dir() {
        return Err(format!(
            "validation root is not a directory: {}",
            root.display()
        ));
    }
    if !(1..=1000).contains(&limit) {
        return Err("limit must be between 1 and 1000".into());
    }
    let mut paths: Vec<_> = fs::read_dir(&root)
        .map_err(|e| e.to_string())?
        .flatten()
        .filter(|entry| entry.file_name().to_string_lossy().starts_with("run-"))
        .map(|entry| entry.path().join("results.json"))
        .filter(|path| path.exists())
        .collect();
    paths.sort();
    paths.reverse();
    let (mut runs, mut errors) = (Vec::new(), Vec::new());
    for path in paths.into_iter().take(limit as usize) {
        let attempt = read_run(&path).and_then(|mut run| {
            if let Some(current) = current {
                let baseline = run["baseline"].clone();
                run["validity"] = assess_evidence(&baseline, current)?;
                for row in run["results"].as_array_mut().into_iter().flatten() {
                    let own = if row["baseline"].is_null() {
                        baseline.clone()
                    } else {
                        row["baseline"].clone()
                    };
                    row["validity"] = assess_evidence(&own, current)?;
                }
            }
            Ok(run)
        });
        match attempt {
            Ok(run) => runs.push(run),
            Err(error) => {
                let run = path
                    .parent()
                    .and_then(Path::file_name)
                    .map(|name| name.to_string_lossy().into_owned())
                    .unwrap_or_default();
                errors.push(json!({"run":run,"path":path.to_string_lossy(),"error":error}));
            }
        }
    }
    Ok(json!({"root":root.to_string_lossy(),"runs":runs,"errors":errors}))
}
