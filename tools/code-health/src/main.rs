mod mcp;

use code_health::{html, markdown, scan, Check, Options, RetainedRange, Style};
use serde_json::json;
use std::fs;
use std::path::PathBuf;

const HELP: &str = "code-health scan --root DIR [--entry PATH] [--checks unused,duplicates,complexity]\n  [--marker-pattern REGEX] [--retain-file PATH] [--retain-range PATH:START:END]\n  [--min-tokens N] [--evidence FILE] [--format json,md,html|all] [--out DIR] [--style-dir DIR]\ncode-health mcp --allow-root DIR [--allow-root DIR]";

fn cli(args: &[String]) -> Result<(), String> {
    let Some((command, args)) = args.split_first() else {
        println!("{HELP}");
        return Ok(());
    };
    match command.as_str() {
        "--version" => {
            println!("code-health {}", env!("CARGO_PKG_VERSION"));
            return Ok(());
        }
        "--help" | "-h" => {
            println!("{HELP}");
            return Ok(());
        }
        "scan" | "mcp" => {}
        _ => return Err(format!("Unknown command {command:?}\n{HELP}")),
    }
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        println!("{HELP}");
        return Ok(());
    }
    let (chunks, rest) = args.as_chunks::<2>();
    if !rest.is_empty() {
        return Err(format!("Each option needs a value\n{HELP}"));
    }
    if command == "mcp" {
        let mut roots = Vec::new();
        for pair in chunks {
            if pair[0] != "--allow-root" {
                return Err(format!("Unknown MCP option {:?}", pair[0]));
            }
            roots.push(PathBuf::from(&pair[1]));
        }
        return mcp::serve(roots);
    }
    let mut options = Options::new("");
    let mut formats = vec!["json"];
    let mut out = None;
    let mut style_dir = None;
    for pair in chunks {
        let value = pair[1].as_str();
        match pair[0].as_str() {
            "--root" if options.root.as_os_str().is_empty() && !value.is_empty() => {
                options.root = value.into()
            }
            "--entry" => options.entries.push(value.into()),
            "--checks" => {
                options.checks = value
                    .split(',')
                    .map(Check::parse)
                    .collect::<Result<_, _>>()?
            }
            "--marker-pattern" => options.marker_patterns.push(value.into()),
            "--retain-file" => options.retained_files.push(value.into()),
            "--retain-range" => {
                let mut fields = value.rsplitn(3, ':');
                let end = fields.next().and_then(|s| s.parse().ok());
                let start = fields.next().and_then(|s| s.parse().ok());
                let (Some(path), Some(start_line), Some(end_line)) = (fields.next(), start, end)
                else {
                    return Err("Use --retain-range PATH:START:END".into());
                };
                options.retained_ranges.push(RetainedRange {
                    path: path.into(),
                    start_line,
                    end_line,
                });
            }
            "--min-tokens" => {
                options.min_tokens = value
                    .parse()
                    .map_err(|_| "Expected an integer for --min-tokens")?
            }
            "--format" => formats = parse_formats(value)?,
            "--out" if !value.is_empty() => out = Some(PathBuf::from(value)),
            "--style-dir" if !value.is_empty() => style_dir = Some(PathBuf::from(value)),
            "--evidence" if !value.is_empty() => options.evidence = Some(read_evidence(value)?),
            flag => return Err(format!("Invalid option or value for {flag:?}\n{HELP}")),
        }
    }
    if options.root.as_os_str().is_empty() {
        return Err("--root is required".into());
    }
    let style = match &style_dir {
        Some(dir) if formats.contains(&"html") => Style::load(dir)?,
        Some(_) => return Err("--style-dir applies to the html format".into()),
        None => Style::builtin(),
    };
    let report = scan(&options)?;
    let render = |format: &str| -> Result<String, String> {
        Ok(match format {
            "md" => markdown(&report),
            "html" => html(&report, &style)?,
            _ => serde_json::to_string_pretty(&report).map_err(|e| e.to_string())? + "\n",
        })
    };
    // One text format without --out keeps printing the report itself
    if out.is_none() && formats.len() == 1 && formats[0] != "html" {
        print!("{}", render(formats[0])?);
        return Ok(());
    }
    let contents = formats
        .iter()
        .map(|format| render(format))
        .collect::<Result<Vec<_>, _>>()?;
    let out = report_html::new_folder(out.as_deref(), &[&options.root], "code-health")?;
    let mut written = Vec::new();
    for (format, content) in formats.iter().zip(contents) {
        let name = format!("report.{format}");
        fs::write(out.join(&name), content).map_err(|e| e.to_string())?;
        written.push(name);
    }
    println!(
        "{}",
        json!({"out":out,"written":written,"style":if formats.contains(&"html") {json!(style.label())} else {json!(null)},
            "files_scanned":report["files_scanned"],"partial":report["partial"]})
    );
    Ok(())
}

fn read_evidence(path: &str) -> Result<serde_json::Value, String> {
    let size = fs::metadata(path)
        .map_err(|e| format!("Cannot read {path}: {e}"))?
        .len();
    if size > 16 * 1024 * 1024 {
        return Err(format!("{path} exceeds 16 MiB"));
    }
    let text = fs::read_to_string(path).map_err(|e| format!("Cannot read {path}: {e}"))?;
    serde_json::from_str(&text).map_err(|e| format!("Invalid evidence JSON in {path}: {e}"))
}

fn parse_formats(value: &str) -> Result<Vec<&'static str>, String> {
    if value == "all" {
        return Ok(vec!["json", "md", "html"]);
    }
    let mut formats = Vec::new();
    for name in value.split(',') {
        let format = match name.trim() {
            "json" => "json",
            "md" | "markdown" => "md",
            "html" => "html",
            other => {
                return Err(format!(
                    "Unknown format {other:?}; use json, md, html or all"
                ))
            }
        };
        if !formats.contains(&format) {
            formats.push(format);
        }
    }
    Ok(formats)
}

fn main() {
    if let Err(error) = cli(&std::env::args().skip(1).collect::<Vec<_>>()) {
        eprintln!("code-health: {error}");
        std::process::exit(2);
    }
}
