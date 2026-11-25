use std::io::{IsTerminal, Read, Write};
use std::path::{Path, PathBuf};
use token_count::context::{self, Options};
use token_count::{count_result, format_json, format_report, html, read_utf8_sig, resolve};

const HELP: &str = "token-count [--input FILE [FILE ...] | --text TEXT] [--encoding NAME] [--json]
            [--html NEW.html] [--max-display-tokens N] [--output NEW_FILE]
token-count context [--project DIR] [--codex-home DIR] [--instruction FILE ...]
            [--active-skill FILE ...] [--active-role FILE ...] [--skill-root DIR ...]
            [--tool-schema FILE ...] [--content FILE ...] [--builtin-tools N]
            [--mcp-tools N] [--encoding NAME] [--profile FILE] [--json] [--output NEW_FILE]

本機精確計算 BPE Token, 預設 o200k_base, 編碼字典內建於執行檔, 不連網
未提供 --input 或 --text 時讀取 UTF-8 stdin
context 依 Global、Project Agent、Skills 與工具設定預估 Codex Context

編碼: gpt2, r50k_base, p50k_base, p50k_edit, cl100k_base, o200k_base, o200k_harmony
結束碼: 0 成功, 2 參數、輸入或輸出錯誤";

#[derive(Default)]
struct Parsed {
    values: Vec<(String, String)>,
    lists: Vec<(String, Vec<String>)>,
    flags: Vec<String>,
}

impl Parsed {
    fn value(&self, name: &str) -> Option<&str> {
        self.values
            .iter()
            .rev()
            .find(|(key, _)| key == name)
            .map(|(_, value)| value.as_str())
    }
    fn all(&self, name: &str) -> Vec<PathBuf> {
        self.values
            .iter()
            .filter(|(key, _)| key == name)
            .map(|(_, value)| PathBuf::from(value))
            .collect()
    }
    fn list(&self, name: &str) -> Option<&Vec<String>> {
        self.lists
            .iter()
            .rev()
            .find(|(key, _)| key == name)
            .map(|(_, items)| items)
    }
    fn flag(&self, name: &str) -> bool {
        self.flags.iter().any(|flag| flag == name)
    }
    fn int(&self, name: &str, default: i64) -> Result<i64, String> {
        match self.value(name) {
            None => Ok(default),
            Some(text) => text
                .trim()
                .parse()
                .map_err(|_| format!("{name} 需要整數: {text}")),
        }
    }
}

/// `--name VALUE`, `--name=VALUE`; list options take values until the next `--option`.
fn parse(
    args: &[String],
    values: &[&str],
    lists: &[&str],
    flags: &[&str],
) -> Result<Parsed, String> {
    let mut parsed = Parsed::default();
    let mut index = 0;
    while index < args.len() {
        let arg = &args[index];
        index += 1;
        let (name, inline) = match arg.split_once('=') {
            Some((name, value)) if name.starts_with("--") => (name, Some(value.to_string())),
            _ => (arg.as_str(), None),
        };
        if flags.contains(&name) && inline.is_none() {
            parsed.flags.push(name.into());
        } else if values.contains(&name) {
            let value = match inline {
                Some(value) => value,
                None => {
                    index += 1;
                    args.get(index - 1)
                        .cloned()
                        .ok_or(format!("{name} 需要值"))?
                }
            };
            parsed.values.push((name.into(), value));
        } else if lists.contains(&name) {
            let mut items: Vec<String> = inline.into_iter().collect();
            while index < args.len() && !args[index].starts_with("--") {
                items.push(args[index].clone());
                index += 1;
            }
            if items.is_empty() {
                return Err(format!("{name} 需要至少一個值"));
            }
            parsed.lists.push((name.into(), items));
        } else {
            return Err(format!("無法辨識的參數: {arg}"));
        }
    }
    Ok(parsed)
}

fn exists(path: &Path) -> bool {
    path.exists() || path.is_symlink()
}

fn write_new(path: &Path, text: &str) -> Result<(), String> {
    // Exclusive creation also guards an output appearing during counting.
    std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .and_then(|mut file| file.write_all(text.as_bytes()))
        .map_err(|error| format!("無法寫入 {}: {error}", path.display()))
}

fn wants_json(parsed: &Parsed) -> bool {
    parsed.flag("--json")
        || parsed.value("--output").is_some_and(|path| {
            Path::new(path)
                .extension()
                .is_some_and(|ext| ext.eq_ignore_ascii_case("json"))
        })
}

fn count(args: &[String]) -> Result<String, String> {
    let parsed = parse(
        args,
        &[
            "--text",
            "--encoding",
            "--html",
            "--max-display-tokens",
            "--output",
        ],
        &["--input"],
        &["--json"],
    )?;
    let inputs: Vec<PathBuf> = parsed
        .list("--input")
        .map(|items| items.iter().map(PathBuf::from).collect())
        .unwrap_or_default();
    if !inputs.is_empty() && parsed.value("--text").is_some() {
        return Err("--input 與 --text 不可同時使用".into());
    }
    let encoding = parsed
        .value("--encoding")
        .unwrap_or(token_count::DEFAULT_ENCODING);
    let limit = parsed.int("--max-display-tokens", 2000)?;
    if limit < 1 {
        return Err("顯示 Token 數需大於 0".into());
    }
    let html_path = parsed.value("--html").map(PathBuf::from);
    let output = parsed.value("--output").map(PathBuf::from);
    if let Some(path) = &html_path {
        let parent = match path.parent() {
            Some(parent) if !parent.as_os_str().is_empty() => parent,
            _ => Path::new("."),
        };
        if !parent.is_dir() {
            return Err(format!("HTML 輸出目錄不存在: {}", parent.display()));
        }
        if exists(path) {
            return Err(format!("輸出檔已存在, 請使用新檔名: {}", path.display()));
        }
        if output
            .as_ref()
            .is_some_and(|out| resolve(out) == resolve(path))
        {
            return Err("HTML 與統計輸出需使用不同路徑".into());
        }
    }
    if let Some(path) = &output {
        if exists(path) {
            return Err(format!("輸出檔已存在, 請使用新檔名: {}", path.display()));
        }
        let target = resolve(path);
        if inputs.iter().any(|input| resolve(input) == target) {
            return Err("輸出路徑不可與來源檔相同".into());
        }
    }
    let documents: Vec<(String, String)> = if !inputs.is_empty() {
        inputs
            .iter()
            .map(|path| Ok((path.display().to_string(), read_utf8_sig(path)?)))
            .collect::<Result<_, String>>()?
    } else if let Some(text) = parsed.value("--text") {
        vec![("inline".into(), text.into())]
    } else if std::io::stdin().is_terminal() {
        return Err("請提供 --input、--text 或透過 stdin 傳入文字".into());
    } else {
        let mut bytes = Vec::new();
        std::io::stdin()
            .read_to_end(&mut bytes)
            .map_err(|error| format!("無法讀取 stdin: {error}"))?;
        let text =
            String::from_utf8(bytes).map_err(|_| "stdin 不是有效的 UTF-8 文字".to_string())?;
        vec![("stdin".into(), text)]
    };
    let results = documents
        .iter()
        .map(|(source, text)| count_result(source, text, encoding))
        .collect::<Result<Vec<_>, _>>()?;
    let page = match &html_path {
        Some(_) => Some(html::render_html(&documents, encoding, limit as usize)?),
        None => None,
    };
    let report = if wants_json(&parsed) {
        format_json(results)
    } else {
        format_report(&results)
    };
    if let Some(path) = &output {
        write_new(path, &report)?;
    }
    if let (Some(path), Some(page)) = (&html_path, page) {
        write_new(path, &page)?;
    }
    Ok(report)
}

fn default_codex_home() -> PathBuf {
    if let Some(home) = std::env::var_os("CODEX_HOME") {
        return PathBuf::from(home);
    }
    let user = std::env::var_os("HOME")
        .or_else(|| std::env::var_os("USERPROFILE"))
        .unwrap_or_default();
    PathBuf::from(user).join(".codex")
}

fn context(args: &[String]) -> Result<String, String> {
    let repeat = [
        "--instruction",
        "--active-skill",
        "--active-role",
        "--skill-root",
        "--tool-schema",
        "--content",
    ];
    let mut values = vec![
        "--project",
        "--codex-home",
        "--builtin-tools",
        "--mcp-tools",
        "--encoding",
        "--profile",
        "--output",
    ];
    values.extend(repeat);
    let parsed = parse(args, &values, &[], &["--json"])?;
    let output = parsed.value("--output").map(PathBuf::from);
    if let Some(path) = &output {
        if exists(path) {
            return Err(format!("輸出檔已存在: {}", path.display()));
        }
    }
    let profile = match parsed.value("--profile") {
        Some(path) => Some(
            std::fs::read_to_string(path).map_err(|error| format!("無法讀取 {path}: {error}"))?,
        ),
        None => None,
    };
    let options = Options {
        encoding: parsed
            .value("--encoding")
            .unwrap_or(token_count::DEFAULT_ENCODING)
            .into(),
        instructions: parsed.all("--instruction"),
        active_skills: parsed.all("--active-skill"),
        active_roles: parsed.all("--active-role"),
        skill_roots: parsed.all("--skill-root"),
        tool_schemas: parsed.all("--tool-schema"),
        contents: parsed.all("--content"),
        builtin_tools: parsed.int("--builtin-tools", 10)?,
        mcp_tools: parsed.int("--mcp-tools", 0)?,
        profile,
    };
    let project = parsed
        .value("--project")
        .map(PathBuf::from)
        .unwrap_or_else(|| std::env::current_dir().unwrap_or_default());
    let home = parsed
        .value("--codex-home")
        .map(PathBuf::from)
        .unwrap_or_else(default_codex_home);
    let report = context::estimate_context(&project, &home, &options)?;
    let rendered = if wants_json(&parsed) {
        format!(
            "{}\n",
            serde_json::to_string_pretty(&report).unwrap_or_default()
        )
    } else {
        context::format_budget(&report)
    };
    if let Some(path) = &output {
        write_new(path, &rendered)?;
    }
    Ok(rendered)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        println!("{HELP}");
        return;
    }
    if args.first().is_some_and(|arg| arg == "--version") {
        println!("token-count {}", env!("CARGO_PKG_VERSION"));
        return;
    }
    let (result, counting) = match args.first().map(String::as_str) {
        Some("context") => (context(&args[1..]), false),
        _ => (count(&args), true),
    };
    match result {
        Ok(text) => {
            let mut stdout = std::io::stdout().lock();
            let _ = stdout.write_all(text.as_bytes());
        }
        Err(error) => {
            eprintln!("錯誤: {error}");
            if counting {
                eprintln!("計數或匯出失敗, 請確認來源、輸出路徑及編碼");
            }
            std::process::exit(2);
        }
    }
}
