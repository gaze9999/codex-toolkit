mod mcp;

use code_health::{markdown, scan, Check, Options, RetainedRange};
use std::path::PathBuf;

const HELP: &str = "code-health scan --root DIR [--entry PATH] [--checks unused,duplicates,complexity]\n  [--marker-pattern REGEX] [--retain-file PATH] [--retain-range PATH:START:END]\n  [--min-tokens N] [--format json|markdown]\ncode-health mcp --allow-root DIR [--allow-root DIR]";

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
    let mut chunks = args.chunks_exact(2);
    if !chunks.remainder().is_empty() {
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
    let mut format = "json";
    for pair in &mut chunks {
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
            "--format" if matches!(value, "json" | "markdown") => format = value,
            flag => return Err(format!("Invalid option or value for {flag:?}\n{HELP}")),
        }
    }
    if options.root.as_os_str().is_empty() {
        return Err("--root is required".into());
    }
    let report = scan(&options)?;
    if format == "markdown" {
        print!("{}", markdown(&report));
    } else {
        println!(
            "{}",
            serde_json::to_string_pretty(&report).map_err(|e| e.to_string())?
        );
    }
    Ok(())
}

fn main() {
    if let Err(error) = cli(&std::env::args().skip(1).collect::<Vec<_>>()) {
        eprintln!("code-health: {error}");
        std::process::exit(2);
    }
}
