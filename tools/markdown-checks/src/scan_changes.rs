//! Classify changed files by likely documentation impact from Git or a unified diff.
use crate::text::suffix;
use regex::Regex;
use serde_json::{json, Value};
use std::collections::{BTreeSet, HashMap};
use std::fs;
use std::path::Path;
use std::process::Command;

const DOC_EXTS: [&str; 5] = [".md", ".mdx", ".rst", ".txt", ".adoc"];
const TEST_HINTS: [&str; 6] = ["test", "tests", "spec", "__tests__", "fixtures", "mocks"];
const CONFIG_NAMES: [&str; 11] = [
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "dockerfile",
    "docker-compose.yml",
    "compose.yml",
    ".env.example",
];
const PUBLIC_HINTS: [&str; 14] = [
    "api",
    "routes",
    "controllers",
    "schema",
    "schemas",
    "openapi",
    "swagger",
    "sdk",
    "cli",
    "commands",
    "config",
    "migration",
    "migrations",
    "public",
];
const UI_HINTS: [&str; 6] = ["components", "pages", "views", "ui", "screens", "routes"];
const DOC_HINTS: [&str; 7] = [
    "readme",
    "docs",
    "documentation",
    "memo",
    "memos",
    "notes",
    "changelog",
];
const DATA_EXTS: [&str; 4] = [".json", ".yaml", ".yml", ".toml"];
const SOURCE_EXTS: [&str; 10] = [
    ".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".java", ".cs", ".rb", ".php",
];

/// Largest untracked file whose lines are counted.
const COUNT_LIMIT: u64 = 4 * 1024 * 1024;

/// Where a change sits and its line counts; counts are `None` for binary files and unified-diff input.
#[derive(Clone, Debug, PartialEq)]
pub struct Fact {
    pub stage: &'static str,
    pub added: Option<u64>,
    pub deleted: Option<u64>,
}

pub struct Impact {
    pub path: String,
    pub change_type: String,
    pub category: &'static str,
    pub likely_doc_impact: &'static str,
    pub reason: &'static str,
}

fn git(repo: &Path, args: &[&str]) -> Result<Vec<u8>, String> {
    let output = Command::new("git")
        .args(args)
        .current_dir(repo)
        .output()
        .map_err(|error| error.to_string())?;
    if !output.status.success() {
        let detail = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(if detail.is_empty() {
            "git command failed".into()
        } else {
            detail
        });
    }
    Ok(output.stdout)
}

fn decode(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes).into_owned()
}

fn fields(data: &[u8]) -> Vec<&[u8]> {
    let trimmed = data.strip_suffix(b"\0").unwrap_or(data);
    if trimmed.is_empty() {
        Vec::new()
    } else {
        trimmed.split(|byte| *byte == 0).collect()
    }
}

/// `git diff --name-status -z` rows; renames and copies keep the destination path.
pub fn parse_name_status(data: &[u8]) -> Result<Vec<(String, String)>, String> {
    let parts = fields(data);
    let (mut rows, mut index) = (Vec::new(), 0);
    while index < parts.len() {
        let status = decode(parts[index]);
        let path = parts
            .get(index + 1)
            .ok_or("incomplete git --name-status output")?;
        index += 2;
        let path = if status.starts_with(['R', 'C']) {
            let target = parts
                .get(index)
                .ok_or("incomplete git rename/copy output")?;
            index += 1;
            decode(target)
        } else {
            decode(path)
        };
        rows.push((status, path));
    }
    Ok(rows)
}

/// Destination path with added and deleted lines.
pub type LineCounts = (String, Option<u64>, Option<u64>);

/// `git diff --numstat -z` rows as destination path, added and deleted lines; binary files report `None`.
pub fn parse_numstat(data: &[u8]) -> Result<Vec<LineCounts>, String> {
    let parts = fields(data);
    let (mut rows, mut index) = (Vec::new(), 0);
    while index < parts.len() {
        let record = decode(parts[index]);
        index += 1;
        let mut columns = record.splitn(3, '\t');
        let (Some(added), Some(deleted), Some(path)) =
            (columns.next(), columns.next(), columns.next())
        else {
            return Err("incomplete git --numstat output".into());
        };
        let path = if path.is_empty() {
            let target = parts
                .get(index + 1)
                .ok_or("incomplete git rename/copy output")?;
            index += 2;
            decode(target)
        } else {
            path.to_string()
        };
        rows.push((path, added.parse().ok(), deleted.parse().ok()));
    }
    Ok(rows)
}

fn sum(left: Option<u64>, right: Option<u64>) -> Option<u64> {
    Some(left? + right?)
}

/// Adds one line-count listing; a path seen under another stage becomes `staged+unstaged` with summed counts.
fn add_counts(
    facts: &mut HashMap<String, Fact>,
    stage: &'static str,
    data: &[u8],
) -> Result<(), String> {
    for (path, added, deleted) in parse_numstat(data)? {
        match facts.get_mut(&path) {
            Some(fact) => {
                if fact.stage != stage {
                    fact.stage = "staged+unstaged";
                }
                fact.added = sum(fact.added, added);
                fact.deleted = sum(fact.deleted, deleted);
            }
            None => {
                facts.insert(
                    path,
                    Fact {
                        stage,
                        added,
                        deleted,
                    },
                );
            }
        }
    }
    Ok(())
}

/// Lines of an untracked text file as Git counts an added file; `None` when it is binary, too large or unreadable.
fn untracked_lines(path: &Path) -> Option<u64> {
    if fs::metadata(path).ok()?.len() > COUNT_LIMIT {
        return None;
    }
    let bytes = fs::read(path).ok()?;
    if bytes.contains(&0) {
        return None;
    }
    let breaks = bytes.iter().filter(|byte| **byte == b'\n').count() as u64;
    Some(breaks + u64::from(bytes.last().is_some_and(|byte| *byte != b'\n')))
}

/// Paths in first-seen order, each with its distinct statuses joined by `/`.
pub fn merge_rows(groups: &[Vec<(String, String)>]) -> Vec<(String, String)> {
    let mut order: Vec<(String, Vec<String>)> = Vec::new();
    for (status, path) in groups.iter().flatten() {
        match order.iter_mut().find(|(seen, _)| seen == path) {
            Some((_, states)) if !states.contains(status) => states.push(status.clone()),
            Some(_) => {}
            None => order.push((path.clone(), vec![status.clone()])),
        }
    }
    order
        .into_iter()
        .map(|(path, states)| (states.join("/"), path))
        .collect()
}

type Changes = (Vec<(String, String)>, HashMap<String, Fact>);

fn from_repo(repo: &Path, base: Option<&str>, stat: bool) -> Result<Changes, String> {
    let mut facts = HashMap::new();
    let tracked = match base {
        Some(base) => {
            if stat {
                add_counts(
                    &mut facts,
                    "base",
                    &git(repo, &["diff", "--numstat", "-z", base])?,
                )?;
            }
            parse_name_status(&git(repo, &["diff", "--name-status", "-z", base])?)?
        }
        None => {
            let staged =
                parse_name_status(&git(repo, &["diff", "--cached", "--name-status", "-z"])?)?;
            let unstaged = parse_name_status(&git(repo, &["diff", "--name-status", "-z"])?)?;
            let merged = merge_rows(&[staged, unstaged]);
            if merged.is_empty() {
                match git(repo, &["diff", "--name-status", "-z", "HEAD~1", "HEAD"]) {
                    Ok(data) => {
                        if stat {
                            let counts = git(repo, &["diff", "--numstat", "-z", "HEAD~1", "HEAD"])?;
                            add_counts(&mut facts, "commit", &counts)?;
                        }
                        parse_name_status(&data)?
                    }
                    Err(_) => Vec::new(),
                }
            } else {
                if stat {
                    let staged = git(repo, &["diff", "--cached", "--numstat", "-z"])?;
                    add_counts(&mut facts, "staged", &staged)?;
                    let unstaged = git(repo, &["diff", "--numstat", "-z"])?;
                    add_counts(&mut facts, "unstaged", &unstaged)?;
                }
                merged
            }
        }
    };
    let untracked = git(repo, &["ls-files", "--others", "--exclude-standard", "-z"])?;
    let untracked: Vec<(String, String)> = fields(&untracked)
        .into_iter()
        .map(|path| ("??".to_string(), decode(path)))
        .collect();
    if stat {
        for (_, path) in &untracked {
            facts.entry(path.clone()).or_insert_with(|| Fact {
                stage: "untracked",
                added: untracked_lines(&repo.join(path)),
                deleted: Some(0),
            });
        }
    }
    Ok((merge_rows(&[tracked, untracked]), facts))
}

fn from_diff(file: &Path) -> Result<Vec<(String, String)>, String> {
    let text = decode(&fs::read(file).map_err(|error| error.to_string())?);
    let target = Regex::new(r" b/(.+)$").unwrap();
    let rows = crate::text::split_lines(&text)
        .into_iter()
        .filter(|line| line.starts_with("diff --git "))
        .filter_map(|line| {
            target
                .captures(line)
                .map(|found| ("M".to_string(), found[1].to_string()))
        })
        .collect();
    Ok(merge_rows(&[rows]))
}

fn any(set: &BTreeSet<String>, hints: &[&str]) -> bool {
    hints.iter().any(|hint| set.contains(*hint))
}

pub fn classify(path: &str, status: &str) -> Impact {
    let lower = path.to_lowercase();
    let separators: &[char] = if cfg!(windows) { &['/', '\\'] } else { &['/'] };
    let parts: BTreeSet<String> = lower
        .split(separators)
        .filter(|part| !part.is_empty() && *part != ".")
        .map(str::to_string)
        .collect();
    let tokens: BTreeSet<String> = lower
        .split(|ch: char| !ch.is_ascii_lowercase() && !ch.is_ascii_digit())
        .map(str::to_string)
        .collect();
    let name = lower
        .rsplit(separators)
        .next()
        .unwrap_or(&lower)
        .to_string();
    let ext = suffix(&name);
    let impact = |category, level, reason| Impact {
        path: path.to_string(),
        change_type: status.to_string(),
        category,
        likely_doc_impact: level,
        reason,
    };
    if CONFIG_NAMES.contains(&name.as_str()) || any(&parts, &["config", ".github", "scripts"]) {
        impact(
            "configuration",
            "yes",
            "configuration, setup, or automation path",
        )
    } else if any(&parts, &TEST_HINTS) || any(&tokens, &TEST_HINTS) {
        impact("test", "no", "test or fixture path")
    } else if DOC_EXTS.contains(&ext.as_str())
        || any(&parts, &DOC_HINTS)
        || any(&tokens, &DOC_HINTS)
    {
        impact("documentation", "yes", "documentation file")
    } else if any(&tokens, &PUBLIC_HINTS) {
        impact(
            "public-contract",
            "yes",
            "public API, schema, CLI, config, or migration path",
        )
    } else if any(&tokens, &UI_HINTS) {
        impact("ui-or-route", "maybe", "UI or route path")
    } else if DATA_EXTS.contains(&ext.as_str()) {
        impact("structured-data", "maybe", "structured data or metadata")
    } else if SOURCE_EXTS.contains(&ext.as_str()) {
        impact("source", "maybe", "source file")
    } else {
        impact("other", "no", "no path-only documentation signal")
    }
}

pub struct Options {
    pub repo: String,
    pub base: Option<String>,
    pub diff_file: Option<String>,
    pub max_files: usize,
    pub json: bool,
    /// Adds each path's stage and line counts.
    pub stat: bool,
    /// Renders a Markdown table with the stage and line counts.
    pub table: bool,
}

fn count_text(count: Option<u64>) -> String {
    count.map_or("-".into(), |value| value.to_string())
}

/// Rendered output and exit code.
pub fn run(options: &Options) -> (String, i32) {
    let stat = options.stat || options.table;
    let rows = match &options.diff_file {
        Some(file) => from_diff(Path::new(file)).map(|rows| (rows, HashMap::new())),
        None => fs::canonicalize(&options.repo)
            .map_err(|error| format!("{}: {error}", options.repo))
            .and_then(|repo| from_repo(&repo, options.base.as_deref(), stat)),
    };
    let (rows, facts) = match rows {
        Ok(rows) => rows,
        Err(error) if options.json => {
            return (
                crate::text::compact(&json!({ "status": "error", "message": error })),
                2,
            )
        }
        Err(error) => return (format!("ERROR: {error}"), 2),
    };
    let items: Vec<Impact> = rows
        .iter()
        .map(|(status, path)| classify(path, status))
        .collect();
    let count = |level: &str| {
        items
            .iter()
            .filter(|item| item.likely_doc_impact == level)
            .count()
    };
    let shown = if options.max_files == 0 {
        &items[..]
    } else {
        &items[..items.len().min(options.max_files)]
    };
    let omitted = items.len() - shown.len();
    let unknown = Fact {
        stage: if options.diff_file.is_some() {
            "diff"
        } else {
            "unknown"
        },
        added: None,
        deleted: None,
    };
    let fact = |path: &str| facts.get(path).unwrap_or(&unknown);
    if options.json {
        let files: Vec<Value> = shown
            .iter()
            .map(|item| {
                let mut file = json!({ "path": item.path, "change_type": item.change_type, "category": item.category,
                    "likely_doc_impact": item.likely_doc_impact, "reason": item.reason });
                if stat {
                    let fact = fact(&item.path);
                    file["stage"] = json!(fact.stage);
                    file["added"] = json!(fact.added);
                    file["deleted"] = json!(fact.deleted);
                }
                file
            })
            .collect();
        let counts = json!({ "yes": count("yes"), "maybe": count("maybe"), "no": count("no") });
        return (
            crate::text::pretty(
                &json!({ "status": "ok", "counts": counts, "omitted": omitted, "files": files }),
            ),
            0,
        );
    }
    let mut lines = vec![format!(
        "files={} yes={} maybe={} no={} omitted={omitted}",
        items.len(),
        count("yes"),
        count("maybe"),
        count("no")
    )];
    if options.table {
        lines.push(String::new());
        lines.push("| File | Stage | Change | Added | Deleted | Category | Doc impact |".into());
        lines.push("| --- | --- | --- | ---: | ---: | --- | --- |".into());
        for item in shown {
            let fact = fact(&item.path);
            lines.push(format!(
                "| `{}` | {} | {} | {} | {} | {} | {} |",
                item.path.replace('|', "\\|"),
                fact.stage,
                item.change_type,
                count_text(fact.added),
                count_text(fact.deleted),
                item.category,
                item.likely_doc_impact
            ));
        }
        return (lines.join("\n"), 0);
    }
    for item in shown {
        let counts = if stat {
            let fact = fact(&item.path);
            format!(
                " [{} +{} -{}]",
                fact.stage,
                count_text(fact.added),
                count_text(fact.deleted)
            )
        } else {
            String::new()
        };
        lines.push(format!(
            "- [{}] {} {}{counts} ({}: {})",
            item.likely_doc_impact, item.change_type, item.path, item.category, item.reason
        ));
    }
    (lines.join("\n"), 0)
}
