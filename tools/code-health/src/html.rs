//! The scan report as `report-html/1` data; the shared report-html crate renders the page.
use report_html::Style;
use serde_json::{json, Value};

fn text(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::String(s) => s.clone(),
        other => other.to_string(),
    }
}

/// Section key, tab label, empty text, stat tone when rows exist and columns as (key, label, kind).
type Section = (
    &'static str,
    &'static str,
    &'static str,
    &'static str,
    &'static [(&'static str, &'static str, &'static str)],
);
const SECTIONS: [Section; 5] = [
    (
        "unused",
        "未使用",
        "沒有未使用的檔案、匯出或成員候選",
        "warning",
        &[
            ("id", "ID", "code"),
            ("kind", "種類", "text"),
            ("path", "檔案", "code"),
            ("line", "行", "number"),
            ("name", "名稱", "code"),
            ("evidence", "證據", "text"),
        ],
    ),
    (
        "duplicates",
        "重複片段",
        "沒有達到門檻的重複片段",
        "error",
        &[
            ("left", "左側", "code"),
            ("right", "右側", "code"),
            ("tokens", "Token 數", "number"),
        ],
    ),
    (
        "complexity",
        "函式分支與行數",
        "沒有可辨識的函式",
        "category",
        &[
            ("path", "檔案", "code"),
            ("name", "函式", "code"),
            ("start_line", "起始行", "number"),
            ("lines", "行數", "number"),
            ("branches", "分支數", "number"),
        ],
    ),
    (
        "needs_review",
        "需人工確認",
        "沒有需要人工確認的項目",
        "warning",
        &[
            ("id", "ID", "code"),
            ("path", "檔案", "code"),
            ("line", "行", "number"),
            ("symbol", "符號", "code"),
            ("reason", "原因", "text"),
        ],
    ),
    (
        "retained",
        "保留範圍",
        "沒有指定保留的檔案或範圍",
        "neutral",
        &[
            ("path", "檔案", "code"),
            ("scope", "範圍", "text"),
            ("start_line", "起始行", "number"),
            ("end_line", "結束行", "number"),
            ("reason", "原因", "text"),
        ],
    ),
];

/// Evidence states as shown in the report: label and stat tone.
const SEMANTIC: [(&str, &str, &str); 6] = [
    ("confirmed", "確認無使用端", "warning"),
    ("refuted", "找到使用端", "success"),
    ("unsupported", "不支援", "neutral"),
    ("timeout", "逾時", "neutral"),
    ("error", "錯誤", "error"),
    ("unchecked", "未確認", "neutral"),
];

fn semantic_label(row: &Value) -> String {
    let found = &row["semantic"];
    let status = found["status"].as_str().unwrap_or("unchecked");
    let label = SEMANTIC
        .iter()
        .find(|(key, _, _)| *key == status)
        .map_or(status, |(_, label, _)| label);
    let mut details = Vec::new();
    if let Some(count) = found["references"].as_u64() {
        details.push(format!("{count} 處"));
    }
    if let Some(provider) = found["provider"].as_str() {
        details.push(provider.to_owned());
    }
    let mut text = if details.is_empty() {
        label.to_owned()
    } else {
        format!("{label} ({})", details.join(", "))
    };
    if let Some(note) = found["note"].as_str() {
        text.push('\n');
        text.push_str(note);
    }
    text
}

/// One row per duplicate region, so the table reads like the Markdown output.
fn rows(report: &Value, key: &str) -> Option<Vec<Value>> {
    let list = report[key].as_array()?;
    if key != "duplicates" {
        let semantic = report.get("semantic").is_some();
        return Some(
            list.iter()
                .map(|row| {
                    let mut row = row.clone();
                    if semantic {
                        row["semantic_label"] = json!(semantic_label(&row));
                    }
                    row
                })
                .collect(),
        );
    }
    let side = |group: &Value, region: &Value, name: &str| {
        format!(
            "{}:{}-{}",
            text(&group[name]),
            region[name]["start_line"],
            region[name]["end_line"]
        )
    };
    Some(
        list.iter()
            .flat_map(|group| {
                group["regions"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .map(move |region| {
                        json!({"left":side(group, region, "left"),"right":side(group, region, "right"),"tokens":region["tokens"]})
                    })
            })
            .collect(),
    )
}

/// Converts a scan report to `report-html/1` data.
pub fn report_data(report: &Value) -> Value {
    let partial = report["partial"] == true;
    let list = |key: &str| {
        report[key]
            .as_array()
            .into_iter()
            .flatten()
            .map(text)
            .collect::<Vec<_>>()
            .join(", ")
    };
    let entries = list("entry_points");
    let semantic = report.get("semantic");
    let (mut stats, mut sections) = (Vec::new(), Vec::new());
    for (key, label, empty, tone, columns) in SECTIONS {
        let Some(rows) = rows(report, key) else {
            continue;
        };
        stats.push(json!({"label":label,"value":rows.len(),"tone":if rows.is_empty() {"neutral"} else {tone},"bar":true}));
        let mut columns: Vec<Value> = columns
            .iter()
            .map(|(key, label, kind)| json!({"key":key,"label":label,"kind":kind}))
            .collect();
        if semantic.is_some() && ["unused", "needs_review"].contains(&key) {
            columns.push(json!({"key":"semantic_label","label":"語意確認","kind":"text"}));
        }
        sections.push(json!({"label":label,"empty":empty,"rows":rows,"columns":columns}));
    }
    let mut tags = vec![if partial {
        json!({"label":"涵蓋範圍不完整","tone":"warning"})
    } else {
        json!({"label":"涵蓋範圍完整","tone":"success"})
    }];
    if let Some(semantic) = semantic {
        let count = |key: &str| semantic["counts"][key].as_u64().unwrap_or(0);
        let total: u64 = SEMANTIC.iter().map(|(key, _, _)| count(key)).sum();
        let checked = total - count("unchecked");
        tags.push(json!({"label":format!("語意確認 {checked} / {total}"),"tone":"category"}));
        for (key, label, tone) in SEMANTIC {
            let value = count(key);
            if value > 0 || ["confirmed", "refuted", "unchecked"].contains(&key) {
                stats.push(json!({"label":format!("語意: {label}"),"value":value,"tone":if value == 0 {"neutral"} else {tone}}));
            }
        }
        let unmatched = semantic["unmatched"].as_array().map_or(0, Vec::len);
        if unmatched > 0 {
            tags.push(
                json!({"label":format!("{unmatched} 筆佐證找不到對應候選"),"tone":"warning"}),
            );
        }
    }
    json!({
        "schema":report_html::SCHEMA,"title":"Code health 報告","lang":"zh-Hant-TW",
        "tags":tags,
        "info":[
            ["掃描根目錄", text(&report["root"])],
            ["檢查項目", list("checks")],
            ["掃描檔案數", text(&report["files_scanned"])],
            ["涵蓋範圍", if partial {"部分 (達到大小、讀取或結果上限, 可縮小根目錄或檢查範圍)"} else {"完整"}],
            ["進入點", if entries.is_empty() {"未解析到進入點".to_owned()} else {entries}],
            ["工具版本", format!("code-health {}", env!("CARGO_PKG_VERSION"))]
        ],
        "note":if semantic.is_some() {"以下都是靜態分析的候選, 語意狀態來自提供者回報, 尚未驗證佐證是否對應目前程式碼, 提出移除或重構前需重新核對實際使用端"} else {"以下都是靜態分析的候選, 提出移除或重構前需核對實際使用端"},
        "stats":stats,"sections":sections
    })
}

/// Renders the scan report as one offline page.
pub fn html(report: &Value, style: &Style) -> Result<String, String> {
    report_html::render(&report_data(report), style)
}
