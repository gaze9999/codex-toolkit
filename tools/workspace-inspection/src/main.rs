use report_html::output::{emit, parse_formats, Emit, Rendered, DEFAULT_FORMATS};
use serde_json::Value;
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use workspace_inspection::baseline::capture_baseline;
use workspace_inspection::environment::{compare_trees, DEFAULT_EXCLUDES};
use workspace_inspection::validation::index_evidence;
use workspace_inspection::{mcp, pages};

const HELP: &str =
    "workspace-inspection baseline --root DIR --source PATH [--source PATH] [--affected PATH] [--artifact PATH] [--out FILE]
workspace-inspection evidence [--root DIR] [--limit N] [--current-baseline FILE]
workspace-inspection compare --source DIR --target DIR [--include GLOB] [--exclude GLOB]
  [--no-default-excludes] [--max-files N]
workspace-inspection mcp --read-root DIR [--read-root DIR]

evidence and compare accept --format json,md,html|all, --out DIR and --style-dir DIR.
Each run prints a short summary and writes report.md (or the selected formats) into a new folder
outside the inspected folders; --out names that folder. --include and --exclude repeat.
Exit codes: 0 clear, 1 unreadable runs (evidence), differences or no compared file (compare), 2 invalid input.";

fn run(args: &[String]) -> Result<i32, String> {
    let Some((command, rest)) = args.split_first() else {
        println!("{HELP}");
        return Ok(0);
    };
    if matches!(command.as_str(), "--help" | "-h")
        || rest.iter().any(|a| a == "--help" || a == "-h")
    {
        println!("{HELP}");
        return Ok(0);
    }
    if command == "--version" {
        println!("workspace-inspection {}", env!("CARGO_PKG_VERSION"));
        return Ok(0);
    }
    let (value_flags, bool_flags): (&[&str], &[&str]) = match command.as_str() {
        "baseline" => (
            &["--root", "--source", "--affected", "--artifact", "--out"],
            &[],
        ),
        "evidence" => (&["--root", "--limit", "--current-baseline"], &[]),
        "compare" => (
            &[
                "--source",
                "--target",
                "--include",
                "--exclude",
                "--max-files",
            ],
            &["--no-default-excludes"],
        ),
        "mcp" => (&["--read-root"], &[]),
        other => return Err(format!("Unknown command {other:?}\n{HELP}")),
    };
    let common: &[&str] = if command == "mcp" {
        &[]
    } else {
        &["--format", "--out", "--style-dir"]
    };
    let mut values: Vec<(&str, &str)> = Vec::new();
    let mut flags: Vec<&str> = Vec::new();
    let mut iter = rest.iter();
    while let Some(arg) = iter.next() {
        if bool_flags.contains(&arg.as_str()) {
            flags.push(arg);
        } else if value_flags.contains(&arg.as_str()) || common.contains(&arg.as_str()) {
            let repeatable = [
                "--include",
                "--exclude",
                "--read-root",
                "--source",
                "--affected",
            ]
            .contains(&arg.as_str())
                && (arg != "--source" || command == "baseline");
            if !repeatable && values.iter().any(|(key, _)| key == arg) {
                return Err(format!("{arg} is given more than once"));
            }
            values.push((arg, iter.next().ok_or(format!("{arg} needs a value"))?));
        } else {
            return Err(format!("Unknown option or argument {arg}"));
        }
    }
    let all = |name: &str| -> Vec<&str> {
        values
            .iter()
            .filter(|(key, _)| *key == name)
            .map(|(_, value)| *value)
            .collect()
    };
    let one = |name: &str| all(name).last().copied();
    if command == "baseline" {
        let root = PathBuf::from(one("--root").ok_or("--root is required")?);
        let sources: Vec<String> = all("--source").into_iter().map(str::to_owned).collect();
        if sources.is_empty() {
            return Err("at least one --source is required".into());
        }
        let affected: Vec<String> = all("--affected").into_iter().map(str::to_owned).collect();
        let result = capture_baseline(&root, &sources, &affected, one("--artifact"))?;
        let text = serde_json::to_string_pretty(&result).map_err(|e| e.to_string())?;
        if let Some(path) = one("--out") {
            fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(path)
                .and_then(|mut file| writeln!(file, "{text}"))
                .map_err(|e| format!("{path}: {e}"))?;
        }
        println!("{text}");
        return Ok(if result["status"] == "partial" { 1 } else { 0 });
    }
    let number = |name: &str, default: i64| match one(name) {
        None => Ok(default),
        Some(text) => text
            .parse::<i64>()
            .map_err(|_| format!("{name} must be a whole number")),
    };
    if command == "mcp" {
        let roots: Vec<PathBuf> = all("--read-root").into_iter().map(PathBuf::from).collect();
        mcp::serve(&roots)?;
        return Ok(0);
    }
    let options = Emit {
        formats: match one("--format") {
            Some(list) => parse_formats(list)?,
            None => DEFAULT_FORMATS.to_vec(),
        },
        out: one("--out").map(PathBuf::from),
        style_dir: one("--style-dir").map(PathBuf::from),
    };
    let rendered = |json: Value, page: Value, summary: Vec<String>| Rendered {
        json,
        summary,
        notes: Vec::new(),
        page,
        markdown: None,
    };
    if command == "evidence" {
        let root = one("--root").map_or_else(|| PathBuf::from("."), PathBuf::from);
        let current: Option<Value> = match one("--current-baseline") {
            None => None,
            Some(path) => {
                let text = fs::read_to_string(path).map_err(|e| format!("{path}: {e}"))?;
                Some(
                    serde_json::from_str(text.trim_start_matches('\u{feff}'))
                        .map_err(|e| format!("{path}: {e}"))?,
                )
            }
        };
        let index = index_evidence(&root, number("--limit", 20)?, current.as_ref())?;
        let code = if index["errors"].as_array().is_some_and(|e| !e.is_empty()) {
            1
        } else {
            0
        };
        let page = pages::evidence(&index, current.is_some());
        let summary = pages::evidence_summary(&index, current.is_some());
        emit(
            "validation-evidence",
            &[&root],
            &options,
            &rendered(index, page, summary),
        )?;
        return Ok(code);
    }
    let source = PathBuf::from(one("--source").ok_or("--source is required")?);
    let target = PathBuf::from(one("--target").ok_or("--target is required")?);
    let mut excludes: Vec<&str> = if flags.contains(&"--no-default-excludes") {
        Vec::new()
    } else {
        DEFAULT_EXCLUDES.to_vec()
    };
    excludes.extend(all("--exclude"));
    let result = compare_trees(
        &source,
        &target,
        &all("--include"),
        &excludes,
        number("--max-files", 20_000)?,
    )?;
    let code = if result["status"] == "match" { 0 } else { 1 };
    let page = pages::comparison(&result);
    let summary = pages::comparison_summary(&result);
    emit(
        "environment-compare",
        &[&source, &target],
        &options,
        &rendered(result, page, summary),
    )?;
    Ok(code)
}

fn main() {
    match run(&std::env::args().skip(1).collect::<Vec<_>>()) {
        Ok(code) => std::process::exit(code),
        Err(error) => {
            eprintln!("error: {error}");
            std::process::exit(2);
        }
    }
}
