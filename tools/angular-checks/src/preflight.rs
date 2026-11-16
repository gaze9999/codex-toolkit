//! Generator preflight: existing uses of a proposed identifier or selector across a tree.
use crate::fsutil::{read_lossy, relative, suffix, walk};
use crate::output::{column, Rendered};
use serde_json::{json, Map};
use std::path::Path;

const SKIP: [&str; 6] = [
    "node_modules",
    "dist",
    ".git",
    ".nx",
    ".angular",
    "coverage",
];
const TEXT_EXTENSIONS: [&str; 28] = [
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".html",
    ".scss",
    ".sass",
    ".less",
    ".css",
    ".json",
    ".xml",
    ".properties",
    ".md",
    ".markdown",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".gradle",
    ".java",
    ".kt",
    ".kts",
    ".graphql",
    ".gql",
    ".vue",
    ".svelte",
];

fn occurrences(root: &Path, value: &str, warnings: &mut Vec<String>) -> Vec<String> {
    let needle = value.to_lowercase();
    let mut matches = Vec::new();
    for path in walk(root, &SKIP) {
        let extension = suffix(&path);
        if !TEXT_EXTENSIONS.contains(&extension.as_str()) {
            continue;
        }
        match read_lossy(&path) {
            Ok(text) if text.to_lowercase().contains(&needle) => {
                matches.push(relative(&path, root))
            }
            Ok(_) => {}
            Err(error) => {
                let warning = format!("{}: {error}", relative(&path, root));
                if !warnings.contains(&warning) {
                    warnings.push(warning);
                }
            }
        }
    }
    matches
}

/// Runs the preflight. The exit code is 1 with collisions unless `allow_existing` is set.
pub fn run(
    root: &Path,
    identifier: &str,
    selector: Option<&str>,
    allow_existing: bool,
) -> Result<(Rendered, i32), String> {
    if !root.is_dir() {
        return Err(format!("Generator root does not exist: {}", root.display()));
    }
    let identifier = identifier.trim();
    if identifier.is_empty() {
        return Err("--identifier must not be empty".into());
    }
    let selector = match selector.map(str::trim) {
        Some("") => return Err("--selector must not be empty".into()),
        other => other,
    };
    let mut warnings = Vec::new();
    let mut collisions = Map::new();
    let mut rows = Vec::new();
    for (name, label, value) in [
        ("identifier", "Identifier", Some(identifier)),
        ("selector", "Selector", selector),
    ] {
        let Some(value) = value else {
            continue;
        };
        let paths = occurrences(root, value, &mut warnings);
        rows.extend(
            paths
                .iter()
                .map(|path| json!({"kind":label,"value":value,"path":path})),
        );
        if !paths.is_empty() {
            collisions.insert(name.into(), json!(paths));
        }
    }
    let clear = collisions.is_empty();
    let result = json!({"root":root.to_string_lossy(),"proposed":{"identifier":identifier,"selector":selector},
        "collisions":collisions,"warnings":warnings});
    let count = |kind: &str| rows.iter().filter(|row| row["kind"] == kind).count();
    let page = json!({
        "schema":report_html::SCHEMA,"title":"Generator 產生前檢查",
        "tags":[if clear {json!({"label":"沒有衝突","tone":"success"})} else {json!({"label":"已有相同名稱","tone":"error"})}],
        "info":[["根目錄", root.to_string_lossy()],["Identifier", identifier],["Selector", selector.unwrap_or("—")],
            ["允許既有項目", if allow_existing {"是"} else {"否"}]],
        "headings":{"stats":"出現位置"},
        "stats":[
            {"label":"Identifier","value":count("Identifier"),"tone":if count("Identifier") == 0 {"neutral"} else {"error"},"bar":true},
            {"label":"Selector","value":count("Selector"),"tone":if count("Selector") == 0 {"neutral"} else {"warning"},"bar":true},
            {"label":"警告","value":warnings.len(),"tone":if warnings.is_empty() {"neutral"} else {"warning"}}
        ],
        "sections":[
            {"label":"出現位置","empty":"樹狀結構內沒有相同的 identifier 或 selector","rows":rows,"columns":[
                column("kind","項目","text"),column("value","值","code"),column("path","檔案","code")]},
            {"label":"警告","empty":"沒有警告","rows":result["warnings"].as_array().unwrap().iter().map(|w| json!({"text":w})).collect::<Vec<_>>(),
                "columns":[column("text","內容","text")]}
        ]
    });
    let text = serde_json::to_string_pretty(&result).map_err(|e| e.to_string())? + "\n";
    Ok((
        Rendered {
            json: result,
            text,
            notes: Vec::new(),
            page,
        },
        if clear || allow_existing { 0 } else { 1 },
    ))
}
