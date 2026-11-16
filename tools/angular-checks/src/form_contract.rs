//! Form contract check: declared controls against TypeScript form definitions and template bindings.
use crate::output::{column, Rendered};
use regex::Regex;
use serde_json::{json, Value};
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;
use std::sync::LazyLock;

static CONTROL: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(concat!(
        r#"(?m)(?:^|[,{]\s*)(?:([A-Za-z_$][\w$]*)|'([^'"]+)'|"([^'"]+)")\s*:\s*"#,
        r"(?:new\s+(?:Untyped)?FormControl(?:\s*<[^>]+>)?|(?:this\.)?[\w$.]+\.control|\[)"
    ))
    .expect("valid pattern")
});
static TEMPLATE_CONTROL: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"\bformControlName\s*=\s*(?:'([^'"]+)'|"([^'"]+)")"#).expect("valid pattern")
});

fn captured(pattern: &Regex, text: &str) -> BTreeSet<String> {
    pattern
        .captures_iter(text)
        .filter_map(|caps| caps.iter().skip(1).flatten().next())
        .map(|found| found.as_str().to_owned())
        .collect()
}

/// Runs the check. The exit code is 1 with findings and 0 without.
pub fn run(root: &Path, contract_path: &Path) -> Result<(Rendered, i32), String> {
    let contract_path =
        fs::canonicalize(contract_path).map_err(|e| format!("{}: {e}", contract_path.display()))?;
    let raw = fs::read_to_string(&contract_path).map_err(|e| e.to_string())?;
    let contract: Value =
        serde_json::from_str(raw.trim_start_matches('\u{feff}')).map_err(|e| e.to_string())?;
    let components = contract["components"]
        .as_array()
        .filter(|_| contract.is_object())
        .ok_or("Contract must be an object with a components array")?;
    let mut findings = Vec::new();
    let mut add = |kind: &str, component: &str, control: &str| {
        findings.push(json!({"kind":kind,"component":component,"control":control}))
    };
    for entry in components {
        let source_name = entry["source"]
            .as_str()
            .ok_or("Each component needs a source path")?;
        let template_name = match &entry["template"] {
            Value::Null => None,
            Value::String(name) if name.is_empty() => None,
            Value::String(name) => Some(name.as_str()),
            _ => return Err(format!("template must be a string: {source_name}")),
        };
        let expected: Vec<&str> = match &entry["controls"] {
            Value::Null => Vec::new(),
            Value::Array(items) if items.iter().all(Value::is_string) => {
                items.iter().filter_map(Value::as_str).collect()
            }
            _ => return Err(format!("controls must be a string array: {source_name}")),
        };
        let source = root.join(source_name);
        if !source.is_file() {
            add("missing-source", source_name, "");
            continue;
        }
        let source_controls = captured(
            &CONTROL,
            &fs::read_to_string(&source).map_err(|e| format!("{source_name}: {e}"))?,
        );
        let template = template_name.map(|name| root.join(name));
        let template_exists = template.as_ref().is_some_and(|path| path.is_file());
        if let (Some(name), false) = (template_name, template_exists) {
            add("missing-template", name, "");
        }
        let template_controls = match (&template, template_exists) {
            (Some(path), true) => captured(
                &TEMPLATE_CONTROL,
                &fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?,
            ),
            _ => BTreeSet::new(),
        };
        for control in expected {
            if !source_controls.contains(control) {
                add("missing-source-control", source_name, control);
            }
            if template_exists && !template_controls.contains(control) {
                add("missing-template-control", source_name, control);
            }
        }
        for control in template_controls.difference(&source_controls) {
            add("template-control-without-source", source_name, control);
        }
    }
    let field = |item: &Value, key: &str| item[key].as_str().unwrap_or("").to_owned();
    let text = if findings.is_empty() {
        "OK\n".to_owned()
    } else {
        findings
            .iter()
            .map(|item| {
                format!(
                    "{}: {} {}\n",
                    field(item, "kind"),
                    field(item, "component"),
                    field(item, "control")
                )
            })
            .collect()
    };
    const KINDS: [(&str, &str); 5] = [
        ("missing-source", "找不到原始檔"),
        ("missing-template", "找不到範本"),
        ("missing-source-control", "原始檔缺少控制項"),
        ("missing-template-control", "範本缺少控制項"),
        ("template-control-without-source", "範本有、原始檔沒有"),
    ];
    let label = |kind: &str| {
        KINDS
            .iter()
            .find(|(key, _)| *key == kind)
            .map_or(kind.to_owned(), |(_, label)| (*label).to_owned())
    };
    let rows: Vec<Value> = findings
        .iter()
        .map(|item| json!({"label":label(&field(item, "kind")),"kind":item["kind"],"component":item["component"],"control":item["control"]}))
        .collect();
    let stats: Vec<Value> = KINDS
        .iter()
        .map(|(kind, label)| {
            let value = findings.iter().filter(|item| item["kind"] == *kind).count();
            json!({"label":label,"value":value,"tone":if value == 0 {"neutral"} else {"error"},"bar":true})
        })
        .collect();
    let page = json!({
        "schema":report_html::SCHEMA,"title":"Angular 表單欄位規格檢查",
        "tags":[if findings.is_empty() {json!({"label":"符合規格","tone":"success"})} else {json!({"label":format!("{} 筆不符", findings.len()),"tone":"error"})}],
        "info":[["根目錄", root.to_string_lossy()],["欄位規格", contract_path.to_string_lossy()],["檢查元件數", components.len()]],
        "headings":{"stats":"不符項目"},"stats":stats,
        "sections":[{"label":"不符項目","empty":"原始檔與範本都符合欄位規格","rows":rows,"columns":[
            column("label","種類","text"),column("kind","代碼","code"),column("component","元件","code"),column("control","控制項","code")]}]
    });
    let code = if findings.is_empty() { 0 } else { 1 };
    Ok((
        Rendered {
            json: json!({"contract":contract_path.to_string_lossy(),"checked_components":components.len(),"findings":findings}),
            text,
            notes: Vec::new(),
            page,
        },
        code,
    ))
}
