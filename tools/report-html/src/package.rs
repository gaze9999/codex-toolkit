//! Appearance package checks shared by the library and the build script.
//! A package is a folder with `manifest.json` (`format` "static", `entry.styles`, `classes` and
//! `assets.<entry>.sha256`) and the style file it names.
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::Path;

/// Every Workbench UI static class the rendered page uses; a package must provide each one.
pub const REQUIRED_CLASSES: [&str; 14] = [
    "wb-workbench",
    "wb-page",
    "wb-page-content",
    "wb-card",
    "wb-card-head",
    "wb-card-body",
    "wb-table-wrap",
    "wb-table",
    "wb-tag",
    "wb-status-bar",
    "wb-legend",
    "wb-legend-dot",
    "wb-filter",
    "wb-muted",
];
const STYLE_LIMIT: u64 = 2 * 1024 * 1024;

pub struct Package {
    pub css: String,
    pub version: String,
    pub sha256: String,
}

fn read(dir: &Path, name: &str) -> Result<String, String> {
    let path = dir.join(name);
    let size = fs::metadata(&path)
        .map_err(|e| format!("Cannot read {}: {e}", path.display()))?
        .len();
    if size > STYLE_LIMIT {
        return Err(format!("{} exceeds 2 MiB", path.display()));
    }
    fs::read_to_string(&path).map_err(|e| format!("Cannot read {}: {e}", path.display()))
}

pub fn sha256(text: &str) -> String {
    Sha256::digest(text.as_bytes())
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

/// A class is provided when the manifest lists it, or lists a prefix ending in `-` that it starts with.
pub fn missing_classes(manifest: &Value) -> Vec<&'static str> {
    let listed: Vec<&str> = manifest["classes"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect();
    REQUIRED_CLASSES
        .into_iter()
        .filter(|class| {
            !listed
                .iter()
                .any(|item| item == class || (item.ends_with('-') && class.starts_with(item)))
        })
        .collect()
}

pub fn load(dir: &Path) -> Result<Package, String> {
    let manifest: Value = serde_json::from_str(&read(dir, "manifest.json")?)
        .map_err(|e| format!("Invalid appearance manifest: {e}"))?;
    let entry = manifest["entry"]["styles"].as_str().unwrap_or("");
    if manifest["format"] != "static"
        || entry.is_empty()
        || entry.contains(['/', '\\'])
        || entry.starts_with('.')
    {
        return Err("Appearance package needs format \"static\" and entry.styles naming a file in the same folder".into());
    }
    let missing = missing_classes(&manifest);
    if !missing.is_empty() {
        return Err(format!(
            "Appearance package does not provide classes the report uses: {}",
            missing.join(", ")
        ));
    }
    let css = read(dir, entry)?;
    let expected = manifest["assets"][entry]["sha256"].as_str().unwrap_or("");
    let actual = sha256(&css);
    if expected.is_empty() {
        return Err(format!("Appearance manifest needs assets.{entry}.sha256"));
    }
    if !expected.eq_ignore_ascii_case(&actual) {
        return Err(format!(
            "{entry} SHA-256 {actual} differs from the manifest value {expected}"
        ));
    }
    if css.to_ascii_lowercase().contains("</style") {
        return Err("Appearance styles contain markup that would end the style element".into());
    }
    Ok(Package {
        css,
        version: manifest["version"]
            .as_str()
            .unwrap_or("(未標示版本)")
            .to_owned(),
        sha256: actual,
    })
}
