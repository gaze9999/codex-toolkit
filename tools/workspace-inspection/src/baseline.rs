//! Capture explicitly selected source files as validation provenance.
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::fs;
use std::io::Read;
use std::path::{Component, Path, PathBuf};

const MAX_SOURCES: usize = 500;
const MAX_AFFECTED: usize = 5000;
const MAX_FILE_BYTES: u64 = 64 * 1024 * 1024;
const MAX_TOTAL_BYTES: u64 = 512 * 1024 * 1024;

fn selected(root: &Path, relative: &str) -> Result<PathBuf, String> {
    let rel = Path::new(relative);
    if relative.is_empty()
        || rel.is_absolute()
        || rel.components().any(|c| !matches!(c, Component::Normal(_)))
    {
        return Err(
            "path must be a non-empty relative path without dot or parent components".into(),
        );
    }
    let path = root.join(rel);
    let metadata = fs::symlink_metadata(&path).map_err(|e| e.to_string())?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err("selected path must be a regular file, not a symlink".into());
    }
    let resolved = fs::canonicalize(&path).map_err(|e| e.to_string())?;
    if !resolved.starts_with(root) {
        return Err("path resolves outside root".into());
    }
    Ok(resolved)
}

fn capture_file(root: &Path, name: &str, remaining: &mut u64) -> Result<String, String> {
    let path = selected(root, name)?;
    let file = fs::File::open(&path).map_err(|e| e.to_string())?;
    let before = file.metadata().map_err(|e| e.to_string())?;
    let size = before.len();
    if size > MAX_FILE_BYTES {
        return Err("file exceeds 64 MiB limit".into());
    }
    if size > *remaining {
        return Err("capture exceeds 512 MiB total byte limit".into());
    }
    let mut reader = (&file).take(size);
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 64 * 1024];
    loop {
        let count = reader.read(&mut buffer).map_err(|e| e.to_string())?;
        if count == 0 {
            break;
        }
        *remaining -= count as u64;
        digest.update(&buffer[..count]);
    }
    let after = fs::metadata(path).map_err(|e| e.to_string())?;
    if reader.limit() != 0 || size != after.len() || before.modified().ok() != after.modified().ok()
    {
        return Err("file changed while being captured".into());
    }
    Ok(format!("{:x}", digest.finalize()))
}

/// Hashes selected paths under an explicit root. Partial failures are returned as diagnostics.
/// Capture alone does not establish live validity.
pub fn capture_baseline(
    root: &Path,
    sources: &[String],
    affected: &[String],
    artifact: Option<&str>,
) -> Result<Value, String> {
    if sources.len() > MAX_SOURCES {
        return Err(format!("sources exceed limit {MAX_SOURCES}"));
    }
    if affected.len() > MAX_AFFECTED {
        return Err(format!("affected paths exceed limit {MAX_AFFECTED}"));
    }
    let root = fs::canonicalize(root).map_err(|e| format!("{}: {e}", root.display()))?;
    if !root.is_dir() {
        return Err("root must be an existing directory".into());
    }
    let mut files = serde_json::Map::new();
    let mut errors = Vec::new();
    let mut remaining = MAX_TOTAL_BYTES;
    for name in sources {
        match capture_file(&root, name, &mut remaining) {
            Ok(digest) => {
                files.insert(name.clone(), json!(digest));
            }
            Err(error) => errors.push(json!({"path":name,"error":error})),
        }
    }
    let mut artifact_hash = None;
    if let Some(name) = artifact {
        match capture_file(&root, name, &mut remaining) {
            Ok(digest) => artifact_hash = Some(digest),
            Err(error) => errors.push(json!({"path":name,"kind":"artifact","error":error})),
        }
    }
    let covered: Vec<String> = files.keys().cloned().collect();
    let uncovered: Vec<String> = affected
        .iter()
        .filter(|p| !files.contains_key(p.as_str()))
        .cloned()
        .collect();
    let mut result = json!({"status":if errors.is_empty() && uncovered.is_empty() {"captured"} else {"partial"},
        "capture_kind":"workspace_inspection_baseline_v1", "scope":"selected_files_only", "root":root.to_string_lossy(), "source_files":files,
        "covered_paths":covered, "affected_paths":affected, "uncovered_paths":uncovered,
        "diagnostics":errors,
        "validity":"unverified_until_assessed_against_recorded_evidence"});
    if let Some(hash) = artifact_hash {
        result["artifact_sha256"] = json!(hash);
    }
    Ok(result)
}
