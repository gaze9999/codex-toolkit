//! Common report facts (`meta`): a fixed set of fields every tool fills the same way, rendered first in
//! the info table in a fixed order. Tools collect them mechanically with [`collect`] or map facts they
//! already hold; a field nobody can collect stays absent, shows as not provided and is listed by
//! [`missing`], so an agent supplies only those, marked `{"value": ..., "by": "ai"}`.
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

/// Field keys and their labels, in display order.
pub const FIELDS: [(&str, &str); 7] = [
    ("tool", "工具"),
    ("format", "報告格式"),
    ("target", "檢查對象"),
    ("revision", "來源修訂"),
    ("generated", "產生時間"),
    ("environment", "執行環境"),
    ("inputs", "輸入檔案"),
];
/// Shown for a field the data leaves out.
pub const NOT_PROVIDED: &str = "未提供";
/// Suffix for a field an agent supplied instead of a tool.
pub const SUPPLIED: &str = " (AI 補充)";

/// One display row: label, text, and whether the value is absent.
pub struct Row {
    pub label: &'static str,
    pub text: String,
    pub missing: bool,
}

fn field_text(value: &Value, key: &str) -> Result<Option<String>, String> {
    let lines = |value: &Value| -> Result<String, String> {
        match value {
            Value::String(text) => Ok(text.clone()),
            Value::Number(number) => Ok(number.to_string()),
            Value::Array(list) => list
                .iter()
                .map(|item| match item {
                    Value::String(text) => Ok(text.clone()),
                    Value::Number(number) => Ok(number.to_string()),
                    _ => Err(format!("meta.{key} list items must be text")),
                })
                .collect::<Result<Vec<_>, _>>()
                .map(|items| items.join("\n")),
            _ => Err(format!(
                "meta.{key} must be text, a number or a list of text"
            )),
        }
    };
    let text = match value {
        Value::Null => return Ok(None),
        Value::Object(supplied) => {
            if supplied.get("by").and_then(Value::as_str) != Some("ai") {
                return Err(format!(
                    "meta.{key} as an object needs \"by\": \"ai\" and a \"value\""
                ));
            }
            lines(&supplied["value"])? + SUPPLIED
        }
        other => lines(other)?,
    };
    Ok((!text.trim().is_empty()).then_some(text))
}

/// The rows of `report["meta"]` in field order; an empty list when the report has no `meta`.
pub fn rows(report: &Value) -> Result<Vec<Row>, String> {
    let meta = match &report["meta"] {
        Value::Null => return Ok(Vec::new()),
        Value::Object(meta) => meta,
        _ => return Err("meta must be an object".into()),
    };
    if let Some(unknown) = meta
        .keys()
        .find(|key| !FIELDS.iter().any(|(k, _)| k == key))
    {
        let known: Vec<&str> = FIELDS.iter().map(|(k, _)| *k).collect();
        return Err(format!(
            "Unknown meta field {unknown:?}; use {}",
            known.join(", ")
        ));
    }
    FIELDS
        .iter()
        .map(|(key, label)| {
            Ok(
                match field_text(&meta.get(*key).cloned().unwrap_or(Value::Null), key)? {
                    Some(text) => Row {
                        label,
                        text,
                        missing: false,
                    },
                    None => Row {
                        label,
                        text: NOT_PROVIDED.into(),
                        missing: true,
                    },
                },
            )
        })
        .collect()
}

/// Field keys a report with `meta` leaves without a value.
pub fn missing(report: &Value) -> Result<Vec<&'static str>, String> {
    Ok(rows(report)?
        .into_iter()
        .zip(FIELDS)
        .filter(|(row, _)| row.missing)
        .map(|(_, (key, _))| key)
        .collect())
}

/// Facts a tool hands to [`collect`]; everything else is read from the target and the system.
#[derive(Default)]
pub struct Facts<'a> {
    pub tool: &'a str,
    pub version: &'a str,
    pub format: &'a str,
    /// Checked folder or file; its Git revision is read when it is inside a checkout.
    pub target: Option<&'a Path>,
    /// Narrower scope inside the target, such as selected paths or a comparison range.
    pub scope: Option<&'a str>,
    /// Runtime the tool ran on, such as `Node v24.22.3`.
    pub runtime: Option<&'a str>,
    pub inputs: &'a [PathBuf],
    /// When the check ran, as Unix seconds; the current time when absent.
    pub at: Option<i64>,
}

fn run(program: &str, args: &[&str], dir: Option<&Path>) -> Option<String> {
    let mut command = Command::new(program);
    command.args(args);
    if let Some(dir) = dir {
        command.current_dir(dir);
    }
    let output = command.output().ok()?;
    output.status.success().then(|| {
        String::from_utf8_lossy(&output.stdout)
            .trim_end()
            .to_owned()
    })
}

/// Local time on the 24-hour clock with its UTC offset, such as `2026-11-26 17:00:00 UTC+08:00`.
/// Read from the system clock tools; zone abbreviations are left out because they are ambiguous.
pub fn local_time() -> Option<String> {
    local_time_at(None)
}

/// [`local_time`] for a given moment in Unix seconds, or now.
pub fn local_time_at(at: Option<i64>) -> Option<String> {
    let text = if cfg!(windows) {
        let moment = at.map_or("Get-Date".to_owned(), |secs| {
            format!("[DateTimeOffset]::FromUnixTimeSeconds({secs}).ToLocalTime()")
        });
        run(
            "powershell",
            &[
                "-NoProfile",
                "-Command",
                &format!("({moment}).ToString('yyyy-MM-dd HH:mm:ss zzz')"),
            ],
            None,
        )
    } else {
        let format = "+%Y-%m-%d %H:%M:%S %z";
        match at {
            None => run("date", &[format], None),
            // BSD date takes -r SECONDS, GNU date takes -d @SECONDS
            Some(secs) => run("date", &["-r", &secs.to_string(), format], None)
                .or_else(|| run("date", &["-d", &format!("@{secs}"), format], None)),
        }
    }?;
    let (time, offset) = text.rsplit_once(' ')?;
    let digits: String = offset.chars().filter(char::is_ascii_digit).collect();
    let sign = offset.chars().next().filter(|c| matches!(c, '+' | '-'))?;
    (digits.len() == 4).then(|| format!("{time} UTC{sign}{}:{}", &digits[..2], &digits[2..]))
}

/// Unix seconds of an RFC 3339 time such as `2026-11-26T09:00:00.000Z` or `2026-11-26T17:00:00+08:00`.
pub fn parse_time(text: &str) -> Option<i64> {
    let text = text.trim();
    let (date, rest) = text.split_once(['T', ' '])?;
    let mut ymd = date.splitn(3, '-').map(|p| p.parse::<i64>().ok());
    let (year, month, day) = (ymd.next()??, ymd.next()??, ymd.next()??);
    let zone_at = rest.find(['Z', 'z', '+', '-'])?;
    let (clock, zone) = rest.split_at(zone_at);
    let mut hms = clock.split(':');
    let hour = hms.next()?.parse::<i64>().ok()?;
    let minute = hms.next()?.parse::<i64>().ok()?;
    let second = hms.next().map_or(Some(0.0), |s| s.parse::<f64>().ok())? as i64;
    let offset = match zone {
        "Z" | "z" => 0,
        _ => {
            let sign = if zone.starts_with('-') { -1 } else { 1 };
            let (h, m) = zone[1..]
                .split_once(':')
                .unwrap_or((&zone[1..3.min(zone.len())], &zone[3.min(zone.len())..]));
            sign * (h.parse::<i64>().ok()? * 3600 + m.parse::<i64>().unwrap_or(0) * 60)
        }
    };
    if !(1..=12).contains(&month)
        || !(1..=31).contains(&day)
        || hour > 23
        || minute > 59
        || second > 60
    {
        return None;
    }
    // Days from the civil date (Howard Hinnant's algorithm)
    let y = if month <= 2 { year - 1 } else { year };
    let era = y.div_euclid(400);
    let yoe = y - era * 400;
    let mp = (month + 9) % 12;
    let doy = (153 * mp + 2) / 5 + day - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    let days = era * 146097 + doe - 719468;
    Some(days * 86400 + hour * 3600 + minute * 60 + second - offset)
}

/// Commit and uncommitted file count of the checkout holding `target`, limited to that path.
pub fn revision(target: &Path) -> Option<String> {
    let dir = if target.is_dir() {
        target
    } else {
        target.parent()?
    };
    let commit = run("git", &["rev-parse", "--short=12", "HEAD"], Some(dir))?;
    let changed = run("git", &["status", "--porcelain", "--", "."], Some(dir))?
        .lines()
        .count();
    Some(if changed == 0 {
        commit
    } else {
        format!("{commit}, 未提交檔案 {changed} 個")
    })
}

/// File name with the first 12 hex digits of its SHA-256, or a note when it cannot be read.
pub fn input_line(path: &Path) -> String {
    let name = path.display();
    match fs::read(path) {
        Ok(bytes) => format!("{name} {}", &hex(&Sha256::digest(&bytes))[..12]),
        Err(_) => format!("{name} (無法讀取)"),
    }
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// Collects every field it can and returns `{"meta": {...}, "missing": [...]}`.
pub fn collect(facts: &Facts) -> Value {
    let mut meta = Map::new();
    let mut put = |key: &str, value: Option<String>| {
        if let Some(value) = value.filter(|v| !v.trim().is_empty()) {
            meta.insert(key.into(), Value::String(value));
        }
    };
    put(
        "tool",
        (!facts.tool.is_empty()).then(|| {
            format!("{} {}", facts.tool, facts.version)
                .trim()
                .to_owned()
        }),
    );
    put("format", Some(facts.format.to_owned()));
    let target = facts.target.map(|path| {
        fs::canonicalize(path)
            .or_else(|_| std::path::absolute(path))
            .unwrap_or_else(|_| path.to_owned())
    });
    put(
        "target",
        target.as_ref().map(|path| match facts.scope {
            Some(scope) if !scope.is_empty() => format!("{}\n範圍: {scope}", path.display()),
            _ => path.display().to_string(),
        }),
    );
    put("revision", target.as_deref().and_then(revision));
    put("generated", local_time_at(facts.at));
    put(
        "environment",
        Some(match facts.runtime {
            Some(runtime) if !runtime.is_empty() => format!(
                "{} {}, {runtime}",
                std::env::consts::OS,
                std::env::consts::ARCH
            ),
            _ => format!("{} {}", std::env::consts::OS, std::env::consts::ARCH),
        }),
    );
    if !facts.inputs.is_empty() {
        meta.insert(
            "inputs".into(),
            json!(facts
                .inputs
                .iter()
                .map(|p| input_line(p))
                .collect::<Vec<_>>()),
        );
    }
    let report = json!({ "meta": meta });
    let missing = missing(&report).unwrap_or_default();
    json!({ "meta": report["meta"], "missing": missing })
}
