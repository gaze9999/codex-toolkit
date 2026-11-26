use report_html::{markdown, meta, render, Style};
use std::fs;
use std::io::{Read, Write};
use std::path::PathBuf;

const HELP: &str = "report-html render --input FILE|- [--format html|md] [--style-dir DIR] [--out FILE]\n  Reads report-html/v1 JSON and prints one offline HTML page (or Markdown with --format md), or writes it to a new file with --out\n  Lists common meta fields the data leaves without a value on standard error\nreport-html meta --tool NAME --tool-version VERSION --format SCHEMA [--target PATH] [--scope TEXT] [--runtime TEXT] [--at RFC3339] [--input FILE]...\n  Prints {\"meta\": ..., \"missing\": [...]} with the common fields collected from the target and the system; --at formats a recorded run time\nreport-html meta --rows FILE|-\n  Reads a meta object, or report data holding one, and prints its [label, text] rows in display order";
const INPUT_LIMIT: u64 = 64 * 1024 * 1024;

fn cli(args: &[String]) -> Result<(), String> {
    let Some((command, args)) = args.split_first() else {
        println!("{HELP}");
        return Ok(());
    };
    match command.as_str() {
        "--version" => {
            println!("report-html {}", env!("CARGO_PKG_VERSION"));
            return Ok(());
        }
        "--help" | "-h" => {
            println!("{HELP}");
            return Ok(());
        }
        "render" | "meta" => {}
        _ => return Err(format!("Unknown command {command:?}\n{HELP}")),
    }
    let (pairs, rest) = args.as_chunks::<2>();
    if !rest.is_empty() {
        return Err(format!("Each option needs a value\n{HELP}"));
    }
    if command == "meta" {
        return collect(pairs);
    }
    let (mut input, mut style_dir, mut out, mut format) = (None, None, None, "html");
    for pair in pairs {
        let value = pair[1].as_str();
        match pair[0].as_str() {
            "--input" if !value.is_empty() => input = Some(value),
            "--style-dir" if !value.is_empty() => style_dir = Some(PathBuf::from(value)),
            "--out" if !value.is_empty() => out = Some(PathBuf::from(value)),
            "--format" if value == "html" || value == "md" => format = value,
            flag => return Err(format!("Invalid option or value for {flag:?}\n{HELP}")),
        }
    }
    let data = read_input(input.ok_or("--input is required")?)?;
    let report = serde_json::from_str(&data).map_err(|e| format!("Invalid report JSON: {e}"))?;
    let missing = meta::missing(&report)?;
    if !missing.is_empty() {
        eprintln!(
            "report-html: meta fields without a value: {}",
            missing.join(", ")
        );
    }
    let page = if format == "md" {
        markdown(&report)?
    } else {
        let style = match style_dir {
            Some(dir) => Style::load(&dir)?,
            None => Style::builtin(),
        };
        render(&report, &style)?
    };
    match out {
        // create_new keeps an existing file untouched
        Some(path) => fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)
            .and_then(|mut file| file.write_all(page.as_bytes()))
            .map_err(|e| format!("Cannot write {}: {e}", path.display())),
        None => {
            print!("{page}");
            Ok(())
        }
    }
}

fn read_input(path: &str) -> Result<String, String> {
    let mut data = String::new();
    if path == "-" {
        std::io::stdin()
            .take(INPUT_LIMIT)
            .read_to_string(&mut data)
            .map_err(|e| e.to_string())?;
    } else {
        let size = fs::metadata(path)
            .map_err(|e| format!("Cannot read {path}: {e}"))?
            .len();
        if size > INPUT_LIMIT {
            return Err(format!("{path} exceeds 64 MiB"));
        }
        data = fs::read_to_string(path).map_err(|e| format!("Cannot read {path}: {e}"))?;
    }
    Ok(data)
}

/// Rows of a meta object or of report data holding `meta`, for Markdown written by other tools.
fn print_rows(path: &str) -> Result<(), String> {
    let value: serde_json::Value =
        serde_json::from_str(&read_input(path)?).map_err(|e| format!("Invalid meta JSON: {e}"))?;
    let report = if value.get("meta").is_some() {
        value
    } else {
        serde_json::json!({ "meta": value })
    };
    let rows: Vec<serde_json::Value> = meta::rows(&report)?
        .into_iter()
        .map(|row| serde_json::json!([row.label, row.text]))
        .collect();
    println!("{}", serde_json::Value::Array(rows));
    Ok(())
}

fn collect(pairs: &[[String; 2]]) -> Result<(), String> {
    if let Some(pair) = pairs.iter().find(|pair| pair[0] == "--rows") {
        if pairs.len() > 1 {
            return Err(format!("--rows takes no other option\n{HELP}"));
        }
        return print_rows(&pair[1]);
    }
    let (mut tool, mut version, mut format) = (None, "", None);
    let (mut target, mut scope, mut runtime, mut inputs) = (None, None, None, Vec::new());
    let mut at = None;
    for pair in pairs {
        let value = pair[1].as_str();
        match pair[0].as_str() {
            "--tool" if !value.is_empty() => tool = Some(value),
            "--tool-version" => version = value,
            "--format" if !value.is_empty() => format = Some(value),
            "--target" if !value.is_empty() => target = Some(PathBuf::from(value)),
            "--scope" => scope = Some(value),
            "--runtime" => runtime = Some(value),
            "--input" if !value.is_empty() => inputs.push(PathBuf::from(value)),
            "--at" => {
                at = Some(meta::parse_time(value).ok_or_else(|| {
                    format!(
                        "--at needs an RFC 3339 time such as 2026-11-26T09:00:00Z, not {value:?}"
                    )
                })?)
            }
            flag => return Err(format!("Invalid option or value for {flag:?}\n{HELP}")),
        }
    }
    let facts = meta::Facts {
        tool: tool.ok_or("--tool is required")?,
        version,
        format: format.ok_or("--format is required")?,
        target: target.as_deref(),
        scope,
        runtime,
        inputs: &inputs,
        at,
    };
    println!("{}", meta::collect(&facts));
    Ok(())
}

fn main() {
    if let Err(error) = cli(&std::env::args().skip(1).collect::<Vec<_>>()) {
        eprintln!("report-html: {error}");
        std::process::exit(2);
    }
}
