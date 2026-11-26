//! Change impact: staged, unstaged and untracked files with nearby public-contract markers.
use crate::fsutil::{git_changed, read_lossy, suffix};
use crate::output::{column, Rendered};
use serde_json::{json, Value};
use std::path::Path;

const MARKERS: [&str; 6] = [
    "selector:",
    "@Input",
    "@Output",
    "CustomEvent",
    "createCustomElement",
    "component-mapping",
];
const SOURCE_EXTENSIONS: [&str; 12] = [
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".html", ".scss", ".sass", ".less", ".css",
    ".json",
];

pub fn run(root: &Path) -> Result<(Rendered, i32), String> {
    let mut rows = Vec::new();
    for name in git_changed(root, false)? {
        let path = root.join(&name);
        let markers: Vec<&str> =
            if SOURCE_EXTENSIONS.contains(&suffix(&path).as_str()) && path.is_file() {
                let text = read_lossy(&path).map_err(|e| format!("{name}: {e}"))?;
                MARKERS
                    .into_iter()
                    .filter(|marker| text.contains(marker))
                    .collect()
            } else {
                Vec::new()
            };
        rows.push(json!({"path":name,"exists":path.exists(),"public_contract_markers":markers}));
    }
    let marked = rows
        .iter()
        .filter(|row| {
            !row["public_contract_markers"]
                .as_array()
                .unwrap()
                .is_empty()
        })
        .count();
    let removed = rows.iter().filter(|row| row["exists"] == false).count();
    let table: Vec<Value> = rows
        .iter()
        .map(|row| {
            let markers: Vec<&str> = row["public_contract_markers"]
                .as_array()
                .unwrap()
                .iter()
                .filter_map(Value::as_str)
                .collect();
            json!({"path":row["path"],"exists":if row["exists"] == true {"存在"} else {"已移除"},"markers":markers.join(", ")})
        })
        .collect();
    let page = json!({
        "schema":report_html::SCHEMA,"title":"Git 變更影響報告",
        "tags":[{"label":format!("{} 個變更檔案", rows.len()),"tone":"category"}],
        "meta":crate::output::page_meta(root, Some("已暫存、未暫存與未追蹤的檔案"), &[]),
        "note":"標記是文字比對的候選, 代表檔案內出現公開介面相關的寫法, 需要核對實際變更內容",
        "headings":{"stats":"變更檔案"},
        "stats":[
            {"label":"變更檔案","value":rows.len(),"tone":"category"},
            {"label":"含公開介面標記","value":marked,"tone":if marked == 0 {"neutral"} else {"warning"}},
            {"label":"已移除","value":removed}
        ],
        "sections":[{"label":"變更檔案","empty":"沒有變更","rows":table,"columns":[
            column("path","路徑","code"),column("exists","狀態","text"),column("markers","公開介面標記","code")]}]
    });
    let result = json!({"root":root.to_string_lossy(),"changed_files":rows});
    Ok((
        Rendered {
            summary: vec![format!(
                "change impact: {} changed files, {marked} with public-contract markers, {removed} removed",
                table.len()
            )],
            json: result,
            notes: Vec::new(),
            page,
            markdown: None,
        },
        0,
    ))
}
