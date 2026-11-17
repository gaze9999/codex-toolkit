//! Results as `report-html/v1` page data for Markdown and HTML.
use report_html::output::column;
use serde_json::{json, Value};
use std::collections::BTreeMap;

fn list(value: &Value) -> &[Value] {
    value.as_array().map_or(&[], Vec::as_slice)
}
fn text(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::String(text) => text.clone(),
        other => other.to_string(),
    }
}
const VALIDITY: [(&str, &str, &str); 4] = [
    ("current", "仍然有效", "success"),
    ("partial", "部分有效", "warning"),
    ("outdated", "已過期", "error"),
    ("unverified", "無法確認", "neutral"),
];
fn validity(value: &Value) -> String {
    let status = value["status"].as_str().unwrap_or("");
    let label = VALIDITY
        .iter()
        .find(|(key, _, _)| *key == status)
        .map_or(status, |(_, label, _)| label);
    let reasons: Vec<String> = list(&value["reasons"]).iter().map(text).collect();
    if reasons.is_empty() {
        label.to_owned()
    } else {
        format!("{label}\n{}", reasons.join("\n"))
    }
}

/// The evidence index as a page: runs, their results and unreadable runs.
pub fn evidence(index: &Value, assessed: bool) -> Value {
    let runs = list(&index["runs"]);
    let mut statuses = BTreeMap::<String, usize>::new();
    let mut verdicts = BTreeMap::<String, usize>::new();
    let (mut run_rows, mut result_rows) = (Vec::new(), Vec::new());
    for run in runs {
        let results = list(&run["results"]);
        run_rows.push(
            json!({"run":run["run"],"started":text(&run["started"]),"results":results.len(),
            "unverified":list(&run["unverified"]).iter().map(text).collect::<Vec<_>>().join("\n"),
            "validity":validity(&run["validity"]),"path":run["path"]}),
        );
        for row in results {
            *statuses.entry(text(&row["status"])).or_default() += 1;
            if assessed {
                *verdicts
                    .entry(text(&row["validity"]["status"]))
                    .or_default() += 1;
            }
            result_rows.push(json!({"run":run["run"],"name":text(&row["name"]),"status":text(&row["status"]),
                "reason":text(&row["reason"]),"command":text(&row["command"]),"log":text(&row["log"]),
                "validity":validity(&row["validity"])}));
        }
    }
    let tone = |status: &str| match status.to_lowercase().as_str() {
        "pass" | "passed" | "ok" | "success" => "success",
        "fail" | "failed" | "error" => "error",
        "warn" | "warning" | "blocked" | "manual" => "warning",
        _ => "neutral",
    };
    let mut stats: Vec<Value> = statuses
        .iter()
        .map(|(status, count)| {
            json!({"label":if status.is_empty() {"(未標示)"} else {status},"value":count,"tone":tone(status),"bar":true})
        })
        .collect();
    for (key, label, tone) in VALIDITY {
        if let Some(count) = verdicts.get(key) {
            stats.push(json!({"label":format!("佐證: {label}"),"value":count,"tone":tone}));
        }
    }
    let errors = list(&index["errors"]);
    let mut run_columns = vec![
        column("run", "執行", "code"),
        column("started", "開始時間", "text"),
        column("results", "結果數", "number"),
        column("unverified", "未驗證項目", "text"),
    ];
    let mut result_columns = vec![
        column("run", "執行", "code"),
        column("name", "項目", "text"),
        column("status", "狀態", "text"),
        column("reason", "原因", "text"),
        column("command", "指令", "code"),
        column("log", "記錄檔", "code"),
    ];
    if assessed {
        run_columns.push(column("validity", "對目前基準", "text"));
        result_columns.push(column("validity", "對目前基準", "text"));
    }
    run_columns.push(column("path", "檔案", "code"));
    json!({
        "schema":report_html::SCHEMA,"title":"驗證證據彙總",
        "tags":[
            {"label":format!("{} 次執行", runs.len()),"tone":"category"},
            if errors.is_empty() {json!({"label":"全部可讀取","tone":"success"})} else {json!({"label":format!("{} 次執行無法讀取", errors.len()),"tone":"error"})}
        ],
        "info":[
            ["證據根目錄", index["root"]],
            ["結果筆數", result_rows.len()],
            ["目前基準", if assessed {"已提供, 每筆結果附上有效性判定"} else {"未提供, 只彙總已記錄的結果"}]
        ],
        "note":"只讀取既有的 results.json, 沒有重新執行任何指令, 狀態為各次執行當時的記錄",
        "headings":{"stats":"已記錄的結果"},
        "stats":stats,
        "sections":[
            {"label":"結果","empty":"沒有已記錄的結果","rows":result_rows,"columns":result_columns},
            {"label":"執行","empty":"沒有 run-* 執行資料夾","rows":run_rows,"columns":run_columns},
            {"label":"無法讀取","empty":"每次執行都可讀取","rows":errors,"columns":[
                column("run","執行","code"),column("error","錯誤","text"),column("path","檔案","code")]}
        ]
    })
}

/// A tree comparison as a page: missing, extra and changed files.
pub fn comparison(result: &Value) -> Value {
    let paths = |key: &str| -> Vec<Value> {
        list(&result[key])
            .iter()
            .map(|path| json!({"path":path}))
            .collect()
    };
    let short = |value: &Value| text(value).chars().take(12).collect::<String>();
    let changed: Vec<Value> = list(&result["changed"])
        .iter()
        .map(|row| {
            json!({"path":row["path"],"source_size":row["source"]["size"],"target_size":row["target"]["size"],
                "source_sha":short(&row["source"]["sha256"]),"target_sha":short(&row["target"]["sha256"])})
        })
        .collect();
    let errors: Vec<Value> = ["source", "target"]
        .iter()
        .flat_map(|side| {
            list(&result["errors"][*side]).iter().map(move |row| {
                json!({"side":if *side == "source" {"來源"} else {"目標"},"path":row["path"],"error":row["error"]})
            })
        })
        .collect();
    let stat = |label: &str, count: usize, tone: &str| json!({"label":label,"value":count,"tone":if count == 0 {"neutral"} else {tone},"bar":true});
    json!({
        "schema":report_html::SCHEMA,"title":"環境比對",
        "tags":[match result["status"].as_str() {
            Some("match") => json!({"label":"兩邊一致","tone":"success"}),
            Some("empty") => json!({"label":"沒有比對到任何檔案","tone":"warning"}),
            _ => json!({"label":"有差異","tone":"warning"}),
        }],
        "info":[
            ["來源", result["source"]],
            ["目標", result["target"]],
            ["檔案數", format!("來源 {} / 目標 {}", result["source_files"], result["target_files"])],
            ["排除項目", format!("來源 {} / 目標 {}", result["excluded"]["source"], result["excluded"]["target"])]
        ],
        "note":"以相對路徑、大小與 SHA-256 比對, 兩邊都只讀取, 不同步任何檔案",
        "headings":{"stats":"差異"},
        "stats":[
            stat("目標缺少", list(&result["missing_in_target"]).len(), "warning"),
            stat("目標多出", list(&result["extra_in_target"]).len(), "category"),
            stat("內容不同", changed.len(), "error"),
            stat("讀取錯誤", errors.len(), "error")
        ],
        "sections":[
            {"label":"目標缺少","empty":"來源的檔案在目標都找得到","rows":paths("missing_in_target"),"columns":[column("path","路徑","code")]},
            {"label":"目標多出","empty":"目標沒有來源以外的檔案","rows":paths("extra_in_target"),"columns":[column("path","路徑","code")]},
            {"label":"內容不同","empty":"共有的檔案內容相同","rows":changed,"columns":[
                column("path","路徑","code"),column("source_size","來源大小","number"),column("target_size","目標大小","number"),
                column("source_sha","來源 SHA-256","code"),column("target_sha","目標 SHA-256","code")]},
            {"label":"讀取錯誤","empty":"沒有讀取錯誤","rows":errors,"columns":[
                column("side","位置","text"),column("path","路徑","code"),column("error","錯誤","text")]}
        ]
    })
}

fn counted(counts: &BTreeMap<String, usize>) -> String {
    counts
        .iter()
        .map(|(name, count)| {
            format!(
                "{} {count}",
                if name.is_empty() { "(unlabeled)" } else { name }
            )
        })
        .collect::<Vec<_>>()
        .join(", ")
}

/// The few lines a caller needs from the evidence index.
pub fn evidence_summary(index: &Value, assessed: bool) -> Vec<String> {
    let runs = list(&index["runs"]);
    let mut lines = vec![format!(
        "validation evidence: {} runs read, {} unreadable",
        runs.len(),
        list(&index["errors"]).len()
    )];
    let statuses = |rows: &[Value]| {
        let mut counts = BTreeMap::<String, usize>::new();
        for row in rows {
            *counts.entry(text(&row["status"])).or_default() += 1;
        }
        counts
    };
    let all: Vec<Value> = runs
        .iter()
        .flat_map(|run| list(&run["results"]).iter().cloned())
        .collect();
    if !all.is_empty() {
        lines.push(format!("results: {}", counted(&statuses(&all))));
    }
    if let Some(latest) = runs.first() {
        lines.push(format!(
            "latest {}: {}{}",
            text(&latest["run"]),
            counted(&statuses(list(&latest["results"]))),
            if assessed {
                format!(", validity {}", text(&latest["validity"]["status"]))
            } else {
                String::new()
            }
        ));
    }
    if assessed {
        let mut verdicts = BTreeMap::<String, usize>::new();
        for row in &all {
            *verdicts
                .entry(text(&row["validity"]["status"]))
                .or_default() += 1;
        }
        lines.push(format!("validity of results: {}", counted(&verdicts)));
    } else {
        lines.push("validity not assessed: no current baseline given".into());
    }
    lines
}

/// The few lines a caller needs from a tree comparison.
pub fn comparison_summary(result: &Value) -> Vec<String> {
    let errors = list(&result["errors"]["source"]).len() + list(&result["errors"]["target"]).len();
    let mut lines = vec![
        format!(
            "environment compare: {}; source {} files, target {} files",
            text(&result["status"]),
            result["source_files"],
            result["target_files"]
        ),
        format!(
            "missing in target {}, extra in target {}, changed {}, read errors {errors}",
            list(&result["missing_in_target"]).len(),
            list(&result["extra_in_target"]).len(),
            list(&result["changed"]).len()
        ),
    ];
    // The folders holding the most differences show where to look first
    let mut folders = BTreeMap::<String, usize>::new();
    let paths = list(&result["missing_in_target"])
        .iter()
        .chain(list(&result["extra_in_target"]))
        .map(text)
        .chain(
            list(&result["changed"])
                .iter()
                .map(|row| text(&row["path"])),
        );
    for path in paths {
        let folder = path.rsplit_once('/').map_or(".", |(folder, _)| folder);
        *folders.entry(folder.to_owned()).or_default() += 1;
    }
    let mut ranked: Vec<(String, usize)> = folders.into_iter().collect();
    ranked.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
    if !ranked.is_empty() {
        lines.push(format!(
            "most differences in {}",
            ranked
                .iter()
                .take(3)
                .map(|(folder, count)| format!("{folder} ({count})"))
                .collect::<Vec<_>>()
                .join(", ")
        ));
    }
    lines
}
