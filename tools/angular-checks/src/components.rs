//! Component inventory: maps Angular components in an Nx workspace to their source, template,
//! styles, selector and custom-element registration.
use crate::fsutil::{git_changed, normalize, relative, suffix, walk};
use crate::output::{column, Rendered};
use regex::{Captures, Regex};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::LazyLock;

const SKIP: [&str; 11] = [
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".angular",
    ".nx",
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
];
fn pattern(text: &str) -> Regex {
    Regex::new(text).expect("valid pattern")
}
/// A quoted value: single or double quotes on one line.
const QUOTED: &str = r#"(?:'([^'\n]*)'|"([^"\n]*)")"#;
static CLASS: LazyLock<Regex> = LazyLock::new(|| pattern(r"export\s+class\s+(\w+Component)\b"));
static SELECTOR: LazyLock<Regex> =
    LazyLock::new(|| pattern(&format!(r"\bselector\s*:\s*{QUOTED}")));
static TEMPLATE_URL: LazyLock<Regex> =
    LazyLock::new(|| pattern(&format!(r"\btemplateUrl\s*:\s*{QUOTED}")));
static STYLE_URL: LazyLock<Regex> =
    LazyLock::new(|| pattern(&format!(r"\bstyleUrl\s*:\s*{QUOTED}")));
static STYLE_URLS: LazyLock<Regex> = LazyLock::new(|| pattern(r"\bstyleUrls\s*:\s*\[([^\]]*)\]"));
static ANY_QUOTED: LazyLock<Regex> = LazyLock::new(|| pattern(QUOTED));
static IMPORT: LazyLock<Regex> =
    LazyLock::new(|| pattern(r#"import\s*\{([^}]+)\}\s*from\s*(?:'([^']*)'|"([^"]*)")"#));
static MAPPING: LazyLock<Regex> = LazyLock::new(|| {
    pattern(r#"selector\s*:\s*(?:'([^']*)'|"([^"]*)")\s*,\s*component\s*:\s*(\w+)"#)
});
static STANDALONE: LazyLock<Regex> = LazyLock::new(|| pattern(r"\bstandalone\s*:\s*true\b"));

fn either<'a>(caps: &Captures<'a>, first: usize) -> &'a str {
    caps.get(first)
        .or_else(|| caps.get(first + 1))
        .map_or("", |m| m.as_str())
}

struct Project {
    name: String,
    root: PathBuf,
    source_root: PathBuf,
}

pub struct Options {
    pub root: PathBuf,
    pub query: Vec<String>,
    pub project: Option<String>,
    pub changed: bool,
    pub limit: usize,
}

fn projects(root: &Path, files: &[PathBuf], warnings: &mut Vec<String>) -> Vec<Project> {
    let mut projects = Vec::new();
    for file in files
        .iter()
        .filter(|path| path.file_name().is_some_and(|name| name == "project.json"))
    {
        let data = fs::read_to_string(file)
            .map_err(|e| e.to_string())
            .and_then(|text| serde_json::from_str::<Value>(&text).map_err(|e| e.to_string()));
        let data = match data {
            Ok(data) if data.is_object() => data,
            Ok(_) => {
                warnings.push(format!(
                    "Project file is not a JSON object: {}",
                    relative(file, root)
                ));
                continue;
            }
            Err(error) => {
                warnings.push(format!("Unable to read {}: {error}", relative(file, root)));
                continue;
            }
        };
        let project_root = file.parent().unwrap_or(root).to_path_buf();
        let source_root = match data["sourceRoot"].as_str() {
            Some(value) => normalize(&root.join(value)),
            None => project_root.clone(),
        };
        let name = data["name"].as_str().map(str::to_owned).unwrap_or_else(|| {
            project_root
                .file_name()
                .map(|name| name.to_string_lossy().into_owned())
                .unwrap_or_default()
        });
        projects.push(Project {
            name,
            root: project_root,
            source_root,
        });
    }
    // The deepest source root wins when roots nest
    projects.sort_by_key(|project| std::cmp::Reverse(project.source_root.components().count()));
    projects
}

fn resolve_import(source: &Path, module: &str) -> Option<PathBuf> {
    if !module.starts_with('.') {
        return None;
    }
    let target = normalize(&source.parent()?.join(module));
    let mut direct = target.clone().into_os_string();
    direct.push(".ts");
    let direct = PathBuf::from(direct);
    let index = target.join("index.ts");
    Some(if !direct.is_file() && index.is_file() {
        index
    } else {
        direct
    })
}

/// Selectors registered as custom elements, keyed by the component source file and class name.
fn custom_elements(
    root: &Path,
    files: &[PathBuf],
    warnings: &mut Vec<String>,
) -> BTreeMap<(PathBuf, String), BTreeSet<String>> {
    let mut result = BTreeMap::<(PathBuf, String), BTreeSet<String>>::new();
    for file in files.iter().filter(|path| {
        path.file_name()
            .is_some_and(|name| name == "component-mapping.ts")
    }) {
        let text = match fs::read_to_string(file) {
            Ok(text) => text,
            Err(error) => {
                warnings.push(format!("Unable to read {}: {error}", relative(file, root)));
                continue;
            }
        };
        let mut imports = BTreeMap::new();
        for caps in IMPORT.captures_iter(&text) {
            let Some(resolved) = resolve_import(file, either(&caps, 2)) else {
                continue;
            };
            // `Original as Alias`: the mapping uses the alias, the component file declares the original
            for imported in caps[1].split(',') {
                let names: Vec<&str> = imported.trim().split(" as ").map(str::trim).collect();
                let (original, alias) = (names[0], names[names.len() - 1]);
                if !alias.is_empty() {
                    imports.insert(alias.to_owned(), (resolved.clone(), original.to_owned()));
                }
            }
        }
        for caps in MAPPING.captures_iter(&text) {
            if let Some(target) = imports.get(&caps[3]) {
                result
                    .entry(target.clone())
                    .or_default()
                    .insert(either(&caps, 1).to_owned());
            }
        }
    }
    result
}

/// The JSDoc block directly above the decorator, or the class name split into words.
fn description(text: &str, component_at: usize, class_name: &str) -> String {
    let prefix = text[..component_at].trim_end();
    if prefix.ends_with("*/") {
        if let Some(start) = prefix.rfind("/**") {
            let lines: Vec<&str> = prefix[start + 3..prefix.len() - 2]
                .lines()
                .map(|line| line.trim().trim_start_matches('*').trim())
                .filter(|line| !line.is_empty() && !line.starts_with('@'))
                .collect();
            if !lines.is_empty() {
                return lines.join(" ");
            }
        }
    }
    let name = class_name.strip_suffix("Component").unwrap_or(class_name);
    let mut words = String::new();
    let mut previous = ' ';
    for ch in name.chars() {
        if ch.is_ascii_uppercase() && (previous.is_ascii_lowercase() || previous.is_ascii_digit()) {
            words.push(' ');
        }
        words.push(ch);
        previous = ch;
    }
    if words.trim().is_empty() {
        class_name.to_owned()
    } else {
        words.trim().to_owned()
    }
}

fn scan(root: &Path, warnings: &mut Vec<String>) -> Vec<Value> {
    let files = walk(root, &SKIP);
    let projects = projects(root, &files, warnings);
    let custom = custom_elements(root, &files, warnings);
    let mut components = Vec::new();
    for source in files.iter().filter(|path| suffix(path) == ".ts") {
        let name = source
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_default();
        if [".spec.ts", ".test.ts", ".d.ts"]
            .iter()
            .any(|end| name.ends_with(end))
        {
            continue;
        }
        let text = match fs::read_to_string(source) {
            Ok(text) => text,
            Err(error) => {
                warnings.push(format!(
                    "Unable to read {}: {error}",
                    relative(source, root)
                ));
                continue;
            }
        };
        let fallback;
        let project = match projects
            .iter()
            .find(|project| source.starts_with(&project.source_root))
        {
            Some(project) => project,
            None => {
                fallback = Project {
                    name: "(workspace)".into(),
                    root: root.to_path_buf(),
                    source_root: root.to_path_buf(),
                };
                &fallback
            }
        };
        let folder = source.parent().unwrap_or(root);
        let companion = |value: &str| relative(&normalize(&folder.join(value)), root);
        let mut search_at = 0;
        while let Some(found) = text[search_at..].find("@Component") {
            let component_at = search_at + found;
            let Some(class) = CLASS.captures_at(&text, component_at) else {
                break;
            };
            let whole = class.get(0).expect("match");
            search_at = whole.end();
            let metadata = &text[component_at..whole.start()];
            let mut styles: Vec<String> = STYLE_URL
                .captures(metadata)
                .map(|caps| companion(either(&caps, 1)))
                .into_iter()
                .collect();
            if let Some(list) = STYLE_URLS.captures(metadata) {
                styles.extend(
                    ANY_QUOTED
                        .captures_iter(&list[1])
                        .map(|caps| companion(either(&caps, 1))),
                );
            }
            components.push(json!({
                "project":project.name,
                "class_name":&class[1],
                "selector":SELECTOR.captures(metadata).map_or("", |caps| either(&caps, 1)),
                "custom_elements":custom.get(&(source.clone(), class[1].to_owned())).map(|set| set.iter().collect::<Vec<_>>()).unwrap_or_default(),
                "source":relative(source, root),
                "project_relative":relative(source, &project.root),
                "template":TEMPLATE_URL.captures(metadata).map(|caps| companion(either(&caps, 1))),
                "styles":styles,
                "standalone":STANDALONE.is_match(metadata),
                "description":description(&text, component_at, &class[1]),
            }));
        }
    }
    components.sort_by_key(|item| {
        (
            item["project"].as_str().unwrap_or("").to_lowercase(),
            item["source"].as_str().unwrap_or("").to_lowercase(),
        )
    });
    components
}

fn strings(value: &Value) -> Vec<&str> {
    value
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect()
}

fn matches(component: &Value, terms: &[String]) -> bool {
    let mut parts = vec![
        component["project"].as_str().unwrap_or(""),
        component["class_name"].as_str().unwrap_or(""),
        component["selector"].as_str().unwrap_or(""),
    ];
    parts.extend(strings(&component["custom_elements"]));
    parts.extend([
        component["source"].as_str().unwrap_or(""),
        component["project_relative"].as_str().unwrap_or(""),
        component["template"].as_str().unwrap_or(""),
    ]);
    parts.extend(strings(&component["styles"]));
    parts.push(component["description"].as_str().unwrap_or(""));
    let haystack = parts.join("\n").to_lowercase();
    terms
        .iter()
        .all(|term| haystack.contains(&term.to_lowercase()))
}

fn changed(component: &Value, names: &BTreeSet<String>) -> bool {
    let mut companions = vec![
        component["source"].as_str().unwrap_or(""),
        component["template"].as_str().unwrap_or(""),
    ];
    companions.extend(strings(&component["styles"]));
    companions.iter().any(|path| names.contains(*path))
        || (!strings(&component["custom_elements"]).is_empty()
            && names
                .iter()
                .any(|path| path.rsplit('/').next() == Some("component-mapping.ts")))
}

/// Runs the inventory. The exit code is 0 with results and 1 without.
pub fn run(options: &Options) -> Result<(Rendered, i32), String> {
    let root = &options.root;
    if !root.join("nx.json").is_file() {
        return Err(format!("not an Nx workspace root: {}", root.display()));
    }
    let mut warnings = Vec::new();
    let mut results: Vec<Value> = scan(root, &mut warnings)
        .into_iter()
        .filter(|item| matches(item, &options.query))
        .collect();
    if let Some(project) = &options.project {
        results.retain(|item| {
            item["project"].as_str().unwrap_or("").to_lowercase() == project.to_lowercase()
        });
    }
    if options.changed {
        let names = git_changed(root, true)?;
        results.retain(|item| changed(item, &names));
    }
    let total = results.len();
    // Totals describe every match; the report lists only the rows within the limit
    let all_projects: BTreeSet<String> = results
        .iter()
        .filter_map(|item| item["project"].as_str().map(str::to_owned))
        .collect();
    let all_standalone = results
        .iter()
        .filter(|item| item["standalone"] == true)
        .count();
    let all_custom = results
        .iter()
        .filter(|item| !strings(&item["custom_elements"]).is_empty())
        .count();
    let shown: Vec<Value> = if options.limit == 0 {
        results
    } else {
        results.into_iter().take(options.limit).collect()
    };
    let mut notes: Vec<String> = warnings
        .iter()
        .map(|warning| format!("warning: {warning}"))
        .collect();
    if total > shown.len() {
        notes.insert(
            0,
            format!(
                "... {} more result(s); raise --limit or use --limit 0",
                total - shown.len()
            ),
        );
    }
    let rows: Vec<Value> = shown
        .iter()
        .map(|item| {
            json!({
                "project":item["project"],"class_name":item["class_name"],"selector":item["selector"],
                "custom_elements":strings(&item["custom_elements"]).join(", "),
                "source":item["source"],"template":item["template"],
                "styles":strings(&item["styles"]).join("\n"),
                "standalone":if item["standalone"] == true {"是"} else {"否"},
                "description":item["description"],
            })
        })
        .collect();
    let count = |test: &dyn Fn(&Value) -> bool| shown.iter().filter(|item| test(item)).count();
    let projects: BTreeSet<&str> = shown
        .iter()
        .filter_map(|item| item["project"].as_str())
        .collect();
    let page = json!({
        "schema":report_html::SCHEMA,"title":"Angular 元件盤點",
        "tags":[{"label":format!("{total} 個元件"),"tone":"category"}],
        "meta":crate::output::page_meta(root, None, &[]),
        "info":[
            ["篩選條件", if options.query.is_empty() {"—".to_owned()} else {options.query.join(" ")}],
            ["專案", options.project.clone().unwrap_or_else(|| "全部".into())],
            ["範圍", if options.changed {"只含有變更的元件"} else {"全部元件"}],
            ["顯示筆數", format!("{} / {total}", shown.len())]
        ],
        "headings":{"stats":"盤點結果"},
        "stats":[
            {"label":"元件","value":shown.len(),"tone":"category"},
            {"label":"專案","value":projects.len()},
            {"label":"Standalone","value":count(&|item| item["standalone"] == true)},
            {"label":"Custom element","value":count(&|item| !strings(&item["custom_elements"]).is_empty())},
            {"label":"警告","value":warnings.len(),"tone":if warnings.is_empty() {"neutral"} else {"warning"}}
        ],
        "sections":[
            {"label":"元件","empty":"沒有符合條件的元件","rows":rows,"columns":[
                column("project","專案","text"),column("class_name","類別","code"),column("selector","Selector","code"),
                column("custom_elements","Custom element","code"),column("source","原始檔","code"),column("template","範本","code"),
                column("styles","樣式","code"),column("standalone","Standalone","text"),column("description","說明","text")]},
            {"label":"警告","empty":"沒有警告","rows":warnings.iter().map(|w| json!({"text":w})).collect::<Vec<_>>(),
                "columns":[column("text","內容","text")]}
        ]
    });
    Ok((
        Rendered {
            summary: vec![format!(
                "components: {total} found in {} projects, {} in the report; standalone {all_standalone}, custom elements {all_custom}, warnings {}",
                all_projects.len(),
                shown.len(),
                warnings.len()
            )],
            json: json!({"workspace":root.to_string_lossy(),"count":total,"components":shown,"warnings":warnings}),
            notes,
            page,
            markdown: None,
        },
        if total > 0 { 0 } else { 1 },
    ))
}
