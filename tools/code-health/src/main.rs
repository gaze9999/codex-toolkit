mod mcp;

use code_health::{markdown, report_data, scan, summary, Check, Options, RetainedRange};
use report_html::output::{emit, parse_formats, Emit, Rendered, DEFAULT_FORMATS};
use std::fs;
use std::path::PathBuf;

const HELP: &str = "code-health scan --root DIR [--entry PATH] [--checks unused,duplicates,complexity]\n  [--marker-pattern REGEX] [--retain-file PATH] [--retain-range PATH:START:END]\n  [--min-tokens N] [--evidence FILE] [--format json,md,html|all] [--out DIR] [--style-dir DIR]\n  Prints a short summary and writes report.md (or the selected formats) into a new folder.\ncode-health mcp --allow-root DIR [--allow-root DIR]";

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
    let mut formats = DEFAULT_FORMATS.to_vec();
    let mut out = None;
    let mut style_dir = None;
    let mut seen = Vec::new();
    for pair in chunks {
        let value = pair[1].as_str();
        let repeatable = matches!(
            pair[0].as_str(),
            "--entry" | "--marker-pattern" | "--retain-file" | "--retain-range"
        );
        if !repeatable && seen.contains(&pair[0].as_str()) {
            return Err(format!("{} is given more than once", pair[0]));
        }
        seen.push(pair[0].as_str());
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
    let report = scan(&options)?;
    let rendered = Rendered {
        summary: summary(&report),
        page: report_data(&report),
        markdown: Some(markdown(&report)),
        notes: Vec::new(),
        json: report,
    };
    emit(
        "code-health",
        &[&options.root],
        &Emit {
            formats,
            out,
            style_dir,
        },
        &rendered,
    )
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

fn main() {
    if let Err(error) = cli(&std::env::args().skip(1).collect::<Vec<_>>()) {
        eprintln!("code-health: {error}");
        std::process::exit(2);
    }
}
