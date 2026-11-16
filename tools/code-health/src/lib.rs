mod complexity;
mod duplicates;
mod evidence;
mod html;
mod lexer;
mod module_graph;
mod summary;
mod unused;

pub use evidence::{SCHEMA as EVIDENCE_SCHEMA, STATUSES as EVIDENCE_STATUSES};
pub use html::{html, report_data};
use lexer::{pairs, tokenize, Language};
use module_graph::{Graph, Settings};
use regex::Regex;
pub use report_html::{Style, REQUIRED_CLASSES};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::io::{self, Read};
use std::path::{Path, PathBuf};
pub use summary::summary;

const FILE_LIMIT: u64 = 2 * 1024 * 1024;
const TOTAL_LIMIT: usize = 48 * 1024 * 1024;
const ENTRY_LIMIT: usize = 100_000;
const TOKEN_LIMIT: usize = 3_000_000;
const RESULT_LIMIT: usize = 1500;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum Check {
    Unused,
    Duplicates,
    Complexity,
}

impl Check {
    pub fn parse(name: &str) -> Result<Self, String> {
        match name {
            "unused" => Ok(Self::Unused),
            "duplicates" => Ok(Self::Duplicates),
            "complexity" => Ok(Self::Complexity),
            _ => Err(format!(
                "Unknown check {name:?}; use unused, duplicates or complexity"
            )),
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Self::Unused => "unused",
            Self::Duplicates => "duplicates",
            Self::Complexity => "complexity",
        }
    }
}

#[derive(Clone, Debug)]
pub struct Options {
    pub root: PathBuf,
    pub entries: Vec<PathBuf>,
    pub checks: BTreeSet<Check>,
    pub marker_patterns: Vec<String>,
    pub retained_files: Vec<PathBuf>,
    pub retained_ranges: Vec<RetainedRange>,
    pub min_tokens: usize,
    /// Semantic evidence (`code-health-evidence/1`) merged into matching candidates.
    pub evidence: Option<Value>,
}

impl Options {
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self {
            root: root.into(),
            entries: Vec::new(),
            checks: [Check::Unused, Check::Duplicates, Check::Complexity].into(),
            marker_patterns: Vec::new(),
            retained_files: Vec::new(),
            retained_ranges: Vec::new(),
            min_tokens: 50,
            evidence: None,
        }
    }
}

#[derive(Clone, Debug)]
pub struct RetainedRange {
    pub path: PathBuf,
    pub start_line: usize,
    pub end_line: usize,
}

#[derive(Clone, Copy)]
struct Span {
    start_line: usize,
    end_line: usize,
}

impl Span {
    fn intersects(self, start: usize, end: usize) -> bool {
        start <= self.end_line && end >= self.start_line
    }
}

type SourceId = usize;

struct Source {
    path: PathBuf,
    text: String,
    language: Language,
}

#[derive(Default)]
struct Project {
    sources: Vec<Source>,
    configs: BTreeMap<PathBuf, Value>,
    issues: Vec<Value>,
    partial: bool,
}

pub fn read_text(path: &Path, limit: u64) -> io::Result<String> {
    let mut text = String::new();
    if !fs::symlink_metadata(path)?.is_file() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "Expected a regular file",
        ));
    }
    fs::File::open(path)?
        .take(limit + 1)
        .read_to_string(&mut text)?;
    if text.len() as u64 > limit {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "Source exceeds scan size limit",
        ));
    }
    Ok(text)
}

impl Project {
    fn issue(&mut self, path: &Path, reason: &str) {
        self.partial = true;
        if self.issues.len() < RESULT_LIMIT {
            self.issues.push(json!({"path":path,"reason":reason}));
        }
    }

    fn read(root: &Path, read_config: bool) -> Self {
        let mut project = Self::default();
        let mut pending = vec![PathBuf::new()];
        let mut scanned = 0;
        let mut bytes = 0;
        'walk: while let Some(directory) = pending.pop() {
            let Ok(entries) = fs::read_dir(root.join(&directory)) else {
                project.issue(&directory, "Directory could not be read");
                continue;
            };
            let mut batch = Vec::new();
            for entry in entries {
                scanned += 1;
                if scanned > ENTRY_LIMIT {
                    project.issue(&directory, "Directory entry limit reached");
                    break 'walk;
                }
                match entry {
                    Ok(entry) => batch.push(entry),
                    Err(_) => project.issue(&directory, "Directory entry could not be read"),
                }
            }
            batch.sort_by_key(|entry| entry.file_name());
            for entry in batch {
                let name = entry.file_name();
                let relative = directory.join(&name);
                let Some(name) = name.to_str() else {
                    project.issue(&relative, "Path is not UTF-8");
                    continue;
                };
                let Ok(kind) = entry.file_type() else {
                    project.issue(&relative, "File type unavailable");
                    continue;
                };
                if kind.is_dir()
                    && !matches!(
                        name,
                        ".git"
                            | ".hg"
                            | ".svn"
                            | ".codex"
                            | ".claude"
                            | ".angular"
                            | "node_modules"
                            | "dist"
                            | "target"
                            | "coverage"
                    )
                {
                    pending.push(relative);
                } else if kind.is_file() {
                    let language = Language::from_path(&relative);
                    let config = read_config
                        && (name == "project.json"
                            || (name.starts_with("tsconfig") && name.ends_with(".json")));
                    if language.is_none() && !config {
                        continue;
                    }
                    let Ok(text) = read_text(&entry.path(), FILE_LIMIT) else {
                        project.issue(&relative, "File could not be read as bounded UTF-8 source");
                        continue;
                    };
                    bytes += text.len();
                    if bytes > TOTAL_LIMIT {
                        project.issue(&relative, "Total source byte limit reached");
                        break 'walk;
                    }
                    if let Some(language) = language {
                        project.sources.push(Source {
                            path: relative,
                            text,
                            language,
                        });
                    } else if let Ok(value) = module_graph::jsonc(&text) {
                        project.configs.insert(relative, value);
                    } else {
                        project.issue(&relative, "Project configuration could not be parsed");
                    }
                }
            }
        }
        project.sources.sort_by(|a, b| a.path.cmp(&b.path));
        project
    }
}

fn selected_path(path: &Path) -> Result<PathBuf, String> {
    if path.is_absolute()
        || path.components().any(|part| {
            matches!(
                part,
                std::path::Component::Prefix(_) | std::path::Component::RootDir
            )
        })
    {
        return Err(format!("Expected a root-relative path: {}", path.display()));
    }
    module_graph::normalize(path)
        .filter(|path| !path.as_os_str().is_empty())
        .ok_or_else(|| format!("Path escapes the scan root: {}", path.display()))
}

fn retention(
    options: &Options,
    sources: &[Source],
    paths: &BTreeMap<PathBuf, SourceId>,
) -> Result<(Vec<Vec<Span>>, Vec<Value>), String> {
    let patterns = options
        .marker_patterns
        .iter()
        .map(|pattern| Regex::new(pattern).map_err(|e| format!("Invalid marker pattern: {e}")))
        .collect::<Result<Vec<_>, _>>()?;
    let mut spans = vec![Vec::new(); sources.len()];
    let mut rows = Vec::new();
    let mut whole = BTreeMap::new();
    for file in &options.retained_files {
        let path = selected_path(file)?;
        let id = paths
            .get(&path)
            .ok_or_else(|| format!("Retained source is not in the scan: {}", path.display()))?;
        whole.insert(*id, "selected_file");
    }
    for (id, source) in sources.iter().enumerate() {
        if patterns
            .iter()
            .any(|pattern| pattern.is_match(&source.text))
        {
            whole.insert(id, "pattern");
        }
    }
    for (id, reason) in whole {
        spans[id].push(Span {
            start_line: 1,
            end_line: usize::MAX,
        });
        rows.push(json!({"path":sources[id].path,"scope":"file","reason":reason}));
    }
    for range in &options.retained_ranges {
        let path = selected_path(&range.path)?;
        let id = paths
            .get(&path)
            .ok_or_else(|| format!("Retained source is not in the scan: {}", path.display()))?;
        if range.start_line == 0
            || range.end_line < range.start_line
            || range.end_line > sources[*id].text.lines().count()
        {
            return Err(format!("Invalid retained range in {}", path.display()));
        }
        spans[*id].push(Span {
            start_line: range.start_line,
            end_line: range.end_line,
        });
        rows.push(json!({"path":path,"scope":"range","start_line":range.start_line,"end_line":range.end_line,"reason":"selected_range"}));
    }
    Ok((spans, rows))
}

/// Resolved configuration settings, entry sources and the configuration files that could not be read.
type ResolvedSettings = (
    BTreeMap<PathBuf, Settings>,
    BTreeSet<SourceId>,
    BTreeSet<PathBuf>,
);

fn settings(
    project: &Project,
    paths: &BTreeMap<PathBuf, SourceId>,
    explicit: &[PathBuf],
) -> Result<ResolvedSettings, String> {
    let mut entries = BTreeSet::new();
    let mut configs = BTreeMap::new();
    let mut invalid = BTreeSet::new();
    for (path, value) in &project.configs {
        let name = path.file_name().unwrap_or_default();
        if name == "project.json" {
            entries.extend(
                module_graph::project_entries(path, value)
                    .iter()
                    .filter_map(|entry| module_graph::resolve_entry(entry, paths)),
            );
        } else {
            let config =
                module_graph::settings(path, &project.configs, &mut BTreeSet::new(), &mut invalid);
            entries.extend(
                config
                    .entries
                    .iter()
                    .filter_map(|entry| module_graph::resolve_entry(entry, paths)),
            );
            if name == "tsconfig.json"
                || name == "tsconfig.base.json"
                || name == "tsconfig.app.json"
            {
                let dir = path.parent().unwrap_or(Path::new("")).to_owned();
                let selected = configs.entry(dir).or_insert_with(Settings::default);
                if config.base.is_some() {
                    selected.base = config.base;
                }
                if !config.aliases.is_empty() {
                    selected.aliases = config.aliases;
                }
            }
        }
    }
    for path in explicit {
        let path = selected_path(path)?;
        let id = module_graph::resolve_entry(&path, paths)
            .ok_or_else(|| format!("Entry point is not a scanned source: {}", path.display()))?;
        if project.sources[id].language != Language::Script {
            return Err(format!(
                "Entry point is not a JavaScript or TypeScript module: {}",
                path.display()
            ));
        }
        entries.insert(id);
    }
    entries.retain(|id| project.sources[*id].language == Language::Script);
    Ok((configs, entries, invalid))
}

/// Scan a single explicit local root. Findings are syntax-level candidates for review.
pub fn scan(options: &Options) -> Result<Value, String> {
    if !(8..=1000).contains(&options.min_tokens) {
        return Err("min_tokens must be between 8 and 1000".into());
    }
    if options.checks.is_empty() {
        return Err("Select at least one check".into());
    }
    let root = options
        .root
        .canonicalize()
        .map_err(|e| format!("Scan root unavailable: {e}"))?;
    if !root.is_dir() || root.parent().is_none() {
        return Err("Select a directory below the filesystem root".into());
    }
    let graph_enabled = options.checks.contains(&Check::Unused);
    let project = Project::read(&root, graph_enabled);
    let mut tokens = Vec::new();
    let mut token_count = 0;
    let mut token_limit = None;
    for source in &project.sources {
        let file = if token_count < TOKEN_LIMIT {
            tokenize(&source.text, source.language)
        } else {
            Vec::new()
        };
        token_count += file.len();
        if token_count >= TOKEN_LIMIT {
            token_limit.get_or_insert(&source.path);
            tokens.push(Vec::new());
        } else {
            tokens.push(file);
        }
    }
    let paths: BTreeMap<_, _> = project
        .sources
        .iter()
        .enumerate()
        .map(|(id, source)| (source.path.clone(), id))
        .collect();
    let (config, entries, invalid) = if graph_enabled {
        settings(&project, &paths, &options.entries)?
    } else {
        Default::default()
    };
    let (retained, mut kept) = retention(options, &project.sources, &paths)?;
    let delimiters = if graph_enabled || options.checks.contains(&Check::Complexity) {
        tokens.iter().map(|file| pairs(file)).collect::<Vec<_>>()
    } else {
        Vec::new()
    };
    let incomplete = project.partial || token_limit.is_some() || !invalid.is_empty();
    let files_scanned = token_limit.map_or(project.sources.len(), |path| paths[path]);
    let mut report = json!({"schema_version":1,"root":root,"files_scanned":files_scanned,"partial":incomplete,
        "checks":options.checks.iter().map(|check| check.name()).collect::<Vec<_>>()});
    let mut review = project.issues;
    if let Some(path) = token_limit {
        review.push(json!({"path":path,"reason":"Total token limit reached"}));
    }
    for path in invalid {
        review.push(json!({"path":path,"reason":"A TypeScript configuration extension could not be read within the scan root"}));
    }
    if graph_enabled {
        let modules = tokens
            .iter()
            .zip(&delimiters)
            .zip(&project.sources)
            .map(|((file, delimiters), source)| {
                if source.language == Language::Script {
                    module_graph::parse(file, delimiters)
                } else {
                    module_graph::parse(&[], &[])
                }
            })
            .collect();
        let graph = Graph::build(&project.sources, modules, &config, &paths, entries);
        if graph.entries.is_empty() {
            review.push(json!({"path":"","reason":"No entry points were resolved; file and export reachability requires manual confirmation"}));
        }
        for (id, module) in graph.modules.iter().enumerate() {
            for (line, reason) in &module.review {
                review.push(json!({"path":project.sources[id].path,"line":line,"reason":reason}));
            }
        }
        for (id, line, name) in &graph.unresolved {
            review.push(json!({"path":project.sources[*id].path,"line":line,"reason":format!("Local module {name:?} is outside the resolved graph")}));
        }
        let (mut findings, uncertain) = unused::find(
            &project.sources,
            &tokens,
            &delimiters,
            &paths,
            &graph,
            &retained,
            incomplete,
        );
        review.extend(uncertain);
        report["entry_points"] = json!(graph
            .entries
            .iter()
            .map(|id| &project.sources[*id].path)
            .collect::<Vec<_>>());
        cap(&mut findings, &mut report);
        report["unused"] = json!(findings);
    }
    if options.checks.contains(&Check::Duplicates) {
        let (mut groups, partial) =
            duplicates::find(&project.sources, &tokens, options.min_tokens, &retained);
        if partial {
            report["partial"] = json!(true);
            review.push(json!({"path":"","reason":"Duplicate comparison limit reached"}));
        }
        // Preserve the largest evidence per pair before filling the remaining output budget.
        let total: usize = groups
            .iter()
            .map(|group| group["regions"].as_array().unwrap().len())
            .sum();
        let mut remaining = RESULT_LIMIT;
        let mut pairs_left = groups.len();
        groups.retain_mut(|group| {
            let regions = group["regions"].as_array_mut().unwrap();
            let allowed = if total > RESULT_LIMIT {
                remaining
                    .saturating_sub(pairs_left.saturating_sub(1))
                    .max(usize::from(remaining > 0))
            } else {
                remaining
            };
            if regions.len() > allowed {
                regions.sort_by_key(|region| std::cmp::Reverse(region["tokens"].as_u64()));
                regions.truncate(allowed);
            }
            remaining -= regions.len();
            pairs_left -= 1;
            !regions.is_empty()
        });
        if total > RESULT_LIMIT {
            report["partial"] = json!(true);
            review.push(json!({"path":"","reason":format!("Duplicate report limited to {RESULT_LIMIT} of {total} verified regions")}));
        }
        report["duplicates"] = json!(groups);
    }
    if options.checks.contains(&Check::Complexity) {
        let mut results = Vec::new();
        for (id, source) in project
            .sources
            .iter()
            .enumerate()
            .filter(|(_, s)| s.language == Language::Script)
        {
            let functions = complexity::functions(&tokens[id], &delimiters[id]);
            for (function, branches) in functions
                .iter()
                .zip(complexity::branches(&tokens[id], &functions))
            {
                let start = tokens[id][function.start].line;
                let end = tokens[id][function.end].end_line;
                if retained[id].iter().any(|span| span.intersects(start, end)) {
                    continue;
                }
                results.push(json!({"path":source.path,"name":function.name,"start_line":start,"end_line":end,"lines":end-start+1,"branches":branches}));
            }
        }
        results.sort_by_key(|row| {
            (
                std::cmp::Reverse(row["branches"].as_u64()),
                std::cmp::Reverse(row["lines"].as_u64()),
            )
        });
        cap(&mut results, &mut report);
        report["complexity"] = json!(results);
    }
    cap(&mut review, &mut report);
    cap(&mut kept, &mut report);
    report["retained"] = json!(kept);
    report["needs_review"] = json!(review);
    #[cfg(windows)]
    portable_report_paths(&mut report);
    evidence::assign_ids(&mut report);
    if let Some(evidence) = &options.evidence {
        evidence::merge(&mut report, evidence)?;
    }
    Ok(report)
}

#[cfg(windows)]
fn portable_report_paths(value: &mut Value) {
    match value {
        Value::Object(fields) => {
            for (key, value) in fields {
                if key == "path" {
                    if let Some(path) = value.as_str().filter(|path| Path::new(path).is_relative())
                    {
                        *value = json!(path.replace('\\', "/"));
                    }
                } else if key == "entry_points" {
                    if let Some(paths) = value.as_array_mut() {
                        for path in paths.iter_mut() {
                            if let Some(text) = path.as_str() {
                                *path = json!(text.replace('\\', "/"));
                            }
                        }
                        paths.sort_by(|a, b| a.as_str().cmp(&b.as_str()));
                    }
                }
                portable_report_paths(value);
            }
        }
        Value::Array(values) => {
            for value in values {
                portable_report_paths(value);
            }
        }
        _ => {}
    }
}

fn cap(rows: &mut Vec<Value>, report: &mut Value) {
    if rows.len() > RESULT_LIMIT {
        report["partial"] = json!(true);
        rows.truncate(RESULT_LIMIT);
    }
}

fn cell(value: &Value) -> String {
    value
        .as_str()
        .map_or_else(
            || {
                if value.is_null() {
                    String::new()
                } else {
                    value.to_string()
                }
            },
            str::to_owned,
        )
        .replace('|', "\\|")
        .replace(['\n', '\r'], " ")
}

pub fn markdown(report: &Value) -> String {
    let mut out = format!(
        "# Code health\n\nScanned {} files. Partial: {}.\n",
        report["files_scanned"], report["partial"]
    );
    if report.get("semantic").is_some() {
        out.push_str("\nSemantic statuses are provider-reported; evidence freshness is unverified. Recheck against current sources before acting.\n");
    }
    for (section, columns) in [
        (
            "unused",
            &["id", "kind", "path", "line", "name", "evidence", "semantic"][..],
        ),
        (
            "complexity",
            &["path", "name", "start_line", "lines", "branches"][..],
        ),
        (
            "retained",
            &["path", "scope", "start_line", "end_line", "reason"][..],
        ),
        (
            "needs_review",
            &["id", "path", "line", "symbol", "reason", "semantic"][..],
        ),
        ("duplicates", &["left", "right", "regions"][..]),
    ] {
        let Some(rows) = report[section].as_array() else {
            continue;
        };
        // The semantic column appears only when evidence was merged
        let columns: Vec<&str> = columns
            .iter()
            .copied()
            .filter(|key| *key != "semantic" || report.get("semantic").is_some())
            .collect();
        out.push_str(&format!(
            "\n## {section}\n\n| {} |\n| {} |\n",
            columns.join(" | "),
            vec!["---"; columns.len()].join(" | ")
        ));
        if section == "duplicates" {
            for group in rows {
                for region in group["regions"].as_array().into_iter().flatten() {
                    out.push_str(&format!(
                        "| {}:{}-{} | {}:{}-{} | {} tokens |\n",
                        cell(&group["left"]),
                        region["left"]["start_line"],
                        region["left"]["end_line"],
                        cell(&group["right"]),
                        region["right"]["start_line"],
                        region["right"]["end_line"],
                        region["tokens"]
                    ));
                }
            }
        } else {
            for row in rows {
                out.push_str(&format!(
                    "| {} |\n",
                    columns
                        .iter()
                        .map(|key| match *key {
                            "semantic" => cell(&row["semantic"]["status"]),
                            key => cell(&row[key]),
                        })
                        .collect::<Vec<_>>()
                        .join(" | ")
                ));
            }
        }
    }
    out
}
