//! Estimate instruction, Skill and tool context from selected local sources.

use crate::{count_text, grouped, path_key, read_utf8_sig, resolve};
use regex::Regex;
use serde_json::{json, Map, Value};
use std::collections::HashSet;
use std::path::{Path, PathBuf};

pub const DEFAULT_PROFILE: &str = include_str!("../data/context_estimates.json");

#[derive(Debug, Clone)]
pub struct Options {
    pub encoding: String,
    pub instructions: Vec<PathBuf>,
    pub active_skills: Vec<PathBuf>,
    pub active_roles: Vec<PathBuf>,
    pub skill_roots: Vec<PathBuf>,
    pub tool_schemas: Vec<PathBuf>,
    pub contents: Vec<PathBuf>,
    pub builtin_tools: i64,
    pub mcp_tools: i64,
    /// Profile JSON text; `None` uses the bundled dated profile.
    pub profile: Option<String>,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            encoding: crate::DEFAULT_ENCODING.into(),
            instructions: Vec::new(),
            active_skills: Vec::new(),
            active_roles: Vec::new(),
            skill_roots: Vec::new(),
            tool_schemas: Vec::new(),
            contents: Vec::new(),
            builtin_tools: 10,
            mcp_tools: 0,
            profile: None,
        }
    }
}

fn read_config(path: &Path) -> Result<Map<String, Value>, String> {
    if !path.is_file() {
        return Ok(Map::new());
    }
    let text = read_utf8_sig(path)?;
    let table: toml::Table =
        toml::from_str(&text).map_err(|error| format!("{} 無法解析: {error}", path.display()))?;
    match serde_json::to_value(table) {
        Ok(Value::Object(map)) => Ok(map),
        _ => Err(format!("{} 無法解析", path.display())),
    }
}

/// Python truthiness for configuration values.
fn truthy(value: &Value) -> bool {
    match value {
        Value::Null => false,
        Value::Bool(flag) => *flag,
        Value::Number(number) => number.as_f64().is_some_and(|n| n != 0.0),
        Value::String(text) => !text.is_empty(),
        Value::Array(items) => !items.is_empty(),
        Value::Object(map) => !map.is_empty(),
    }
}

fn table(value: Option<&Value>) -> Option<&Map<String, Value>> {
    value.and_then(Value::as_object)
}

fn is_blank(bytes: &[u8]) -> bool {
    bytes
        .iter()
        .all(|byte| matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c))
}

pub fn first_instruction(folder: &Path, fallbacks: &[String]) -> Result<Option<PathBuf>, String> {
    let names = ["AGENTS.override.md".to_string(), "AGENTS.md".to_string()];
    for name in names.iter().chain(fallbacks) {
        if Path::new(name).file_name().and_then(|n| n.to_str()) != Some(name.as_str()) {
            return Err("指示檔 fallback 必須是檔名".into());
        }
        let path = folder.join(name);
        if path.is_file() {
            let bytes = std::fs::read(&path)
                .map_err(|error| format!("無法讀取 {}: {error}", path.display()))?;
            if !is_blank(&bytes) {
                return Ok(Some(path));
            }
        }
    }
    Ok(None)
}

/// Instruction files from the Git root down to `project`, one per directory.
pub fn project_chain(project: &Path, fallbacks: &[String]) -> Result<Vec<PathBuf>, String> {
    let mut folders = Vec::new();
    let mut found = false;
    for folder in project.ancestors() {
        folders.push(folder.to_path_buf());
        if folder.join(".git").exists() {
            found = true;
            break;
        }
    }
    if !found {
        folders = vec![project.to_path_buf()];
    }
    let mut chain = Vec::new();
    for folder in folders.iter().rev() {
        if let Some(path) = first_instruction(folder, fallbacks)? {
            chain.push(path);
        }
    }
    Ok(chain)
}

/// Python `str.splitlines()` boundaries.
fn split_lines(text: &str) -> Vec<&str> {
    let mut lines = Vec::new();
    let mut start = 0;
    let mut chars = text.char_indices().peekable();
    while let Some((index, ch)) = chars.next() {
        let boundary = matches!(
            ch,
            '\n' | '\r'
                | '\u{0b}'
                | '\u{0c}'
                | '\u{1c}'
                | '\u{1d}'
                | '\u{1e}'
                | '\u{85}'
                | '\u{2028}'
                | '\u{2029}'
        );
        if boundary {
            lines.push(&text[start..index]);
            let mut next = index + ch.len_utf8();
            if ch == '\r' {
                if let Some(&(_, '\n')) = chars.peek() {
                    chars.next();
                    next += 1;
                }
            }
            start = next;
        }
    }
    if start < text.len() {
        lines.push(&text[start..]);
    }
    lines
}

/// Rendered discovery entry: `- name: description (file: path)`.
pub fn skill_metadata(path: &Path) -> Result<String, String> {
    let text = read_utf8_sig(path)?;
    let frontmatter = Regex::new(r"(?s)\A---\r?\n(.*?)\r?\n---").expect("valid regex");
    let field = Regex::new(r"^(name|description):\s*(.*)$").expect("valid regex");
    let Some(captures) = frontmatter.captures(&text) else {
        return Err(format!("Skill 缺少 frontmatter: {}", path.display()));
    };
    let lines = split_lines(captures.get(1).map_or("", |m| m.as_str()));
    let (mut name, mut description) = (String::new(), String::new());
    for (index, line) in lines.iter().enumerate() {
        let Some(found) = field.captures(line) else {
            continue;
        };
        let mut value = found[2].to_string();
        if matches!(value.as_str(), ">" | ">-" | "|" | "|-") {
            let mut continuation = Vec::new();
            for following in &lines[index + 1..] {
                if following.chars().next().is_some_and(|c| !c.is_whitespace()) {
                    break;
                }
                continuation.push(following.trim());
            }
            value = continuation.join(" ");
        }
        let value = value.trim_matches(|c| c == '"' || c == '\'').to_string();
        if &found[1] == "name" {
            name = value;
        } else {
            description = value;
        }
    }
    if name.is_empty() || description.is_empty() {
        return Err(format!("Skill 缺少名稱或說明: {}", path.display()));
    }
    Ok(format!(
        "- {name}: {description} (file: {})",
        path.display()
    ))
}

fn sorted_dirs(root: &Path) -> Vec<PathBuf> {
    let mut dirs: Vec<PathBuf> = std::fs::read_dir(root)
        .map(|entries| {
            entries
                .filter_map(Result::ok)
                .map(|entry| entry.path())
                .filter(|path| path.is_dir())
                .collect()
        })
        .unwrap_or_default();
    dirs.sort_by(|a, b| a.file_name().cmp(&b.file_name()));
    dirs
}

/// `sorted(root.glob("*/SKILL.md"))`.
fn skill_files(root: &Path) -> Vec<PathBuf> {
    sorted_dirs(root)
        .into_iter()
        .map(|dir| dir.join("SKILL.md"))
        .filter(|path| path.exists())
        .collect()
}

fn version_key(name: &str) -> Vec<u128> {
    Regex::new(r"\d+")
        .expect("valid regex")
        .find_iter(name)
        .map(|m| m.as_str().parse().unwrap_or(u128::MAX))
        .collect()
}

pub fn discover_skills(
    home: &Path,
    project: &Path,
    config: &Map<String, Value>,
    extra_roots: &[PathBuf],
) -> Vec<PathBuf> {
    let mut roots = vec![
        home.join("skills"),
        home.parent().unwrap_or(home).join(".agents").join("skills"),
        project.join(".agents").join("skills"),
    ];
    roots.extend(extra_roots.iter().cloned());
    let mut disabled = HashSet::new();
    if let Some(rows) = table(config.get("skills"))
        .and_then(|skills| skills.get("config"))
        .and_then(Value::as_array)
    {
        let mut settings = Map::new();
        for row in rows {
            if let Some(path) = row.get("path").and_then(Value::as_str) {
                let enabled = row.get("enabled").cloned().unwrap_or(Value::Bool(true));
                settings.insert(path_key(Path::new(path)), enabled);
            }
        }
        for (key, enabled) in settings {
            if enabled == Value::Bool(false) {
                disabled.insert(key);
            }
        }
    }
    let plugins = table(config.get("plugins"));
    let version = Regex::new(r"^\d+(?:\.\d+)+(?:[-+][\w.-]+)?$").expect("valid regex");
    let cache = home.join("plugins").join("cache");
    if cache.is_dir() {
        for market in sorted_dirs(&cache) {
            let market_name = market.file_name().unwrap_or_default().to_string_lossy();
            for plugin in sorted_dirs(&market) {
                let plugin_name = plugin.file_name().unwrap_or_default().to_string_lossy();
                let off = plugins
                    .and_then(|map| table(map.get(&format!("{plugin_name}@{market_name}"))))
                    .and_then(|entry| entry.get("enabled"))
                    == Some(&Value::Bool(false));
                if off {
                    continue;
                }
                let mut latest: Option<(Vec<u128>, PathBuf)> = None;
                for candidate in sorted_dirs(&plugin) {
                    let name = candidate.file_name().unwrap_or_default().to_string_lossy();
                    if !version.is_match(&name) {
                        continue;
                    }
                    let key = version_key(&name);
                    if latest.as_ref().is_none_or(|(best, _)| key > *best) {
                        latest = Some((key, candidate.clone()));
                    }
                }
                if let Some((_, path)) = latest {
                    roots.push(path.join("skills"));
                }
            }
        }
    }
    let mut keys: Vec<String> = Vec::new();
    let mut paths: Vec<PathBuf> = Vec::new();
    for root in roots {
        let mut found = skill_files(&root);
        found.extend(skill_files(&root.join(".system")));
        for path in found {
            let key = path_key(&path);
            if disabled.contains(&key) {
                continue;
            }
            match keys.iter().position(|known| *known == key) {
                Some(index) => paths[index] = path,
                None => {
                    keys.push(key);
                    paths.push(path);
                }
            }
        }
    }
    paths
}

fn profile_int(profile: &Value, field: &str) -> Result<u64, String> {
    profile
        .get(field)
        .filter(|value| value.is_i64() || value.is_u64())
        .and_then(Value::as_u64)
        .ok_or(format!("預估設定無效: {field}"))
}

fn profile_range(profile: &Value, field: &str) -> Result<(u64, u64), String> {
    let invalid = || format!("預估設定無效: {field}");
    let pair = profile
        .get(field)
        .and_then(Value::as_array)
        .ok_or_else(invalid)?;
    let numbers: Vec<u64> = pair
        .iter()
        .filter(|value| value.is_i64() || value.is_u64())
        .filter_map(Value::as_u64)
        .collect();
    match numbers.as_slice() {
        [low, high] if pair.len() == 2 && low <= high => Ok((*low, *high)),
        _ => Err(invalid()),
    }
}

fn source_url(profile: &Value, index: usize) -> Result<String, String> {
    profile["sources"][index]["url"]
        .as_str()
        .map(str::to_string)
        .ok_or("預估設定無效: sources".into())
}

struct Rows {
    rows: Vec<Value>,
    seen: HashSet<String>,
    encoding: String,
}

impl Rows {
    fn estimate(&mut self, category: String, low: u64, high: u64, url: String) {
        self.rows
            .push(json!({"category": category, "low": low, "high": high,
            "method": "community_estimate", "sources": [url]}));
    }

    fn add_text(
        &mut self,
        category: &str,
        text: &str,
        sources: Vec<String>,
        method: &str,
    ) -> Result<(), String> {
        let tokens = count_text(text, &self.encoding)?;
        self.rows
            .push(json!({"category": category, "low": tokens, "high": tokens,
            "method": method, "sources": sources}));
        Ok(())
    }

    /// Deduplicated files; `budget` truncates instruction files to the shared byte budget.
    fn add_files(
        &mut self,
        category: &str,
        paths: &[PathBuf],
        budget: Option<&mut u64>,
    ) -> Result<(), String> {
        let mut budget = budget;
        let (mut texts, mut sources) = (Vec::new(), Vec::new());
        for path in paths {
            if !self.seen.insert(path_key(path)) {
                continue;
            }
            let mut text = read_utf8_sig(path)?;
            if let Some(remaining) = budget.as_deref_mut() {
                let cut = (*remaining).min(text.len() as u64) as usize;
                let raw = &text.as_bytes()[..cut];
                let valid = match std::str::from_utf8(raw) {
                    Ok(valid) => valid,
                    Err(error) => {
                        std::str::from_utf8(&raw[..error.valid_up_to()]).unwrap_or_default()
                    }
                };
                text = valid.to_string();
                *remaining -= text.len() as u64;
            }
            texts.push(text);
            sources.push(path.display().to_string());
        }
        if !sources.is_empty() {
            self.add_text(category, &texts.join("\n\n"), sources, "file_bpe")?;
        }
        Ok(())
    }
}

fn strings(value: Option<&Value>) -> Vec<String> {
    value
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(|v| v.as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default()
}

pub fn estimate_context(project: &Path, home: &Path, options: &Options) -> Result<Value, String> {
    let (project, home) = (resolve(project), resolve(home));
    if !project.is_dir() {
        return Err(format!("專案目錄不存在: {}", project.display()));
    }
    if options.builtin_tools < 0 || options.mcp_tools < 0 {
        return Err("工具數量需大於等於 0".into());
    }
    let (builtin_tools, mcp_tools) = (options.builtin_tools as u64, options.mcp_tools as u64);
    let profile: Value =
        serde_json::from_str(options.profile.as_deref().unwrap_or(DEFAULT_PROFILE))
            .map_err(|error| format!("預估設定無法解析: {error}"))?;
    let system_tokens = profile_int(&profile, "system_tokens")?;
    let builtin_tool_tokens = profile_int(&profile, "builtin_tool_tokens")?;
    let mcp_server_tokens = profile_range(&profile, "mcp_server_tokens")?;
    let mcp_tool_tokens = profile_range(&profile, "mcp_tool_tokens")?;

    let home_config_path = home.join("config.toml");
    let mut config = read_config(&home_config_path)?;
    let git_root = project
        .ancestors()
        .find(|folder| folder.join(".git").exists())
        .unwrap_or(&project)
        .to_path_buf();
    let project_config_path = git_root.join(".codex").join("config.toml");
    let project_config = read_config(&project_config_path)?;
    for field in ["mcp_servers", "plugins"] {
        let mut merged = table(config.get(field)).cloned().unwrap_or_default();
        if let Some(extra) = table(project_config.get(field)) {
            for (key, value) in extra {
                merged.insert(key.clone(), value.clone());
            }
        }
        config.insert(field.into(), Value::Object(merged));
    }
    let skill_rows = |cfg: &Map<String, Value>| {
        table(cfg.get("skills"))
            .and_then(|skills| skills.get("config"))
            .and_then(Value::as_array)
            .cloned()
            .unwrap_or_default()
    };
    let mut skill_config = skill_rows(&config);
    skill_config.extend(skill_rows(&project_config));
    config.insert("skills".into(), json!({"config": skill_config}));
    for field in ["project_doc_max_bytes", "project_doc_fallback_filenames"] {
        if let Some(value) = project_config.get(field) {
            config.insert(field.into(), value.clone());
        }
    }
    let mut byte_budget = match config.get("project_doc_max_bytes") {
        None => 32768,
        Some(value) => value
            .as_i64()
            .filter(|n| *n >= 0)
            .ok_or("project_doc_max_bytes 需大於等於 0")? as u64,
    };

    let mut rows = Rows {
        rows: Vec::new(),
        seen: HashSet::new(),
        encoding: options.encoding.clone(),
    };
    let global = first_instruction(&home, &[])?;
    rows.add_files(
        "Global Agent",
        &global.into_iter().collect::<Vec<_>>(),
        Some(&mut byte_budget),
    )?;
    let fallbacks = strings(config.get("project_doc_fallback_filenames"));
    rows.add_files(
        "Project Agent",
        &project_chain(&project, &fallbacks)?,
        Some(&mut byte_budget),
    )?;
    rows.add_files("其他指示與參考", &options.instructions, None)?;
    let skills = discover_skills(&home, &git_root, &config, &options.skill_roots);
    if !skills.is_empty() {
        let rendered = skills
            .iter()
            .map(|path| skill_metadata(path))
            .collect::<Result<Vec<_>, _>>()?
            .join("\n");
        let sources = skills.iter().map(|p| p.display().to_string()).collect();
        rows.add_text("Skills 探索清單", &rendered, sources, "catalog_render_bpe")?;
    }
    rows.add_files("啟用的 Skills", &options.active_skills, None)?;
    rows.add_files("啟用的角色", &options.active_roles, None)?;
    let memory = home.join("memories").join("memory_summary.md");
    if memory.is_file() {
        rows.add_files("Memory 摘要", &[memory], None)?;
    }
    let mut roles = Map::new();
    let mut role_sources = Vec::new();
    for (path, cfg) in [
        (&home_config_path, &config),
        (&project_config_path, &project_config),
    ] {
        for (name, value) in table(cfg.get("agents")).into_iter().flatten() {
            let Some(description) = value.get("description").filter(|d| truthy(d)) else {
                continue;
            };
            if value.is_object() {
                let text = match description {
                    Value::String(text) => text.clone(),
                    other => other.to_string(),
                };
                roles.insert(name.clone(), Value::String(text));
                role_sources.push(path.display().to_string());
            }
        }
    }
    if !roles.is_empty() {
        let mut names: Vec<&String> = roles.keys().collect();
        names.sort();
        let text = names
            .iter()
            .map(|name| format!("- {name}: {}", roles[*name].as_str().unwrap_or("")))
            .collect::<Vec<_>>()
            .join("\n");
        role_sources.sort();
        role_sources.dedup();
        rows.add_text("角色探索清單", &text, role_sources, "catalog_render_bpe")?;
    }
    rows.add_files("任務文字與文件", &options.contents, None)?;
    let servers: Vec<String> = table(config.get("mcp_servers"))
        .into_iter()
        .flatten()
        .filter(|(_, value)| value.get("enabled").is_none_or(truthy))
        .map(|(name, _)| name.clone())
        .collect();
    rows.estimate(
        "系統基礎預估".into(),
        system_tokens,
        system_tokens,
        source_url(&profile, 0)?,
    );
    if !options.tool_schemas.is_empty() {
        rows.add_files("選定工具定義", &options.tool_schemas, None)?;
    } else if builtin_tools > 0 {
        let total = builtin_tools * builtin_tool_tokens;
        rows.estimate(
            format!("內建工具預估 ({builtin_tools} 項)"),
            total,
            total,
            source_url(&profile, 1)?,
        );
    }
    if !servers.is_empty() {
        let count = servers.len() as u64;
        rows.estimate(
            format!("MCP Server 預估 ({count} 個)"),
            count * mcp_server_tokens.0,
            count * mcp_server_tokens.1,
            source_url(&profile, 1)?,
        );
    }
    if mcp_tools > 0 && options.tool_schemas.is_empty() {
        rows.estimate(
            format!("MCP 工具預估 ({mcp_tools} 項)"),
            mcp_tools * mcp_tool_tokens.0,
            mcp_tools * mcp_tool_tokens.1,
            source_url(&profile, 2)?,
        );
    }
    let low: u64 = rows.rows.iter().filter_map(|row| row["low"].as_u64()).sum();
    let high: u64 = rows
        .rows
        .iter()
        .filter_map(|row| row["high"].as_u64())
        .sum();
    let mut sources: Vec<Value> = profile["sources"].as_array().cloned().unwrap_or_default();
    sources.extend(
        profile["official_sources"]
            .as_array()
            .into_iter()
            .flatten()
            .map(|url| json!({"url": url})),
    );
    Ok(json!({
        "encoding": options.encoding,
        "project": project.display().to_string(),
        "profile_checked_on": profile.get("checked_on").cloned().ok_or("預估設定無效: checked_on")?,
        "skill_count": skills.len(),
        "mcp_servers": servers,
        "components": rows.rows,
        "total": {"low": low, "high": high},
        "sources": sources,
    }))
}

pub fn format_budget(report: &Value) -> String {
    let value = |low: u64, high: u64| {
        if low == high {
            grouped(low)
        } else {
            format!("{}–{}", grouped(low), grouped(high))
        }
    };
    let number = |row: &Value, key: &str| row[key].as_u64().unwrap_or(0);
    let checked = match &report["profile_checked_on"] {
        Value::String(text) => text.clone(),
        other => other.to_string(),
    };
    let mut lines = vec![
        format!("編碼: {}", report["encoding"].as_str().unwrap_or("")),
        format!("來源日期: {checked}"),
        String::new(),
        "| 項目 | Token |".into(),
        "|---|---:|".into(),
    ];
    let components = report["components"].as_array().cloned().unwrap_or_default();
    for row in &components {
        lines.push(format!(
            "| {} | {} |",
            row["category"].as_str().unwrap_or(""),
            value(number(row, "low"), number(row, "high"))
        ));
    }
    let total = &report["total"];
    lines.push(format!(
        "| 預估總計 | {} |",
        value(number(total, "low"), number(total, "high"))
    ));
    lines.push(String::new());
    lines.push("來源:".into());
    for row in &components {
        let category = row["category"].as_str().unwrap_or("");
        let sources: Vec<&str> = row["sources"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .collect();
        let label = if category == "Skills 探索清單" && sources.len() > 3 {
            format!("{} 份 SKILL.md metadata", sources.len())
        } else {
            sources.join("、")
        };
        lines.push(format!("- {category}: {label}"));
    }
    lines.join("\n") + "\n"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn splits_like_python() {
        assert_eq!(split_lines("a\r\nb\rc\n"), vec!["a", "b", "c"]);
        assert_eq!(split_lines("a\n\nb"), vec!["a", "", "b"]);
        assert!(split_lines("").is_empty());
    }

    #[test]
    fn parses_folded_description() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("SKILL.md");
        std::fs::write(
            &path,
            "---\nname: \"demo\"\ndescription: >-\n  first\n  second\nother: x\n---\nbody",
        )
        .unwrap();
        let line = skill_metadata(&path).unwrap();
        assert!(line.starts_with("- demo: first second (file: "), "{line}");
        std::fs::write(&path, "no frontmatter").unwrap();
        assert!(skill_metadata(&path).is_err());
    }

    #[test]
    fn picks_latest_plugin_version() {
        assert!(version_key("1.10.0") > version_key("1.9.3"));
        assert!(version_key("2.0") > version_key("1.99.99"));
    }
}
