use markdown_checks::{context_brief, diff, scan_changes, sync};
use std::path::{Path, PathBuf};

const HELP: &str = "markdown-checks diff --left FILE --right FILE
markdown-checks context-brief FILE [--required-heading TEXT ...] [--json] [--strict]
markdown-checks scan-changes [--repo DIR] [--base REF] [--diff-file FILE] [--max-files N] [--json]
markdown-checks sync-inspect FILE [--include-notion-metadata] [--json]
markdown-checks sync-write FILE --content-file FILE --expected-sha256 HASH [--dry-run]

diff           Compare headings, list items and table rows outside fenced code
context-brief  Structural checks on a context brief; exit 1 when a check fails
scan-changes   Classify changed files by likely documentation impact
sync-inspect   Read one Markdown sync target: path, SHA-256, headings, optional Notion metadata
sync-write     Replace that target only when its SHA-256 still matches; exit 3 when it changed

Exit codes: 0 success, 1 failed context-brief check, 2 invalid input or I/O error, 3 stale sync target.";

struct Args {
    positional: Vec<String>,
    values: Vec<(String, String)>,
    flags: Vec<String>,
}

impl Args {
    fn value(&self, name: &str) -> Option<&str> {
        self.values
            .iter()
            .rev()
            .find(|(key, _)| key == name)
            .map(|(_, value)| value.as_str())
    }
    fn all(&self, name: &str) -> Vec<String> {
        self.values
            .iter()
            .filter(|(key, _)| key == name)
            .map(|(_, value)| value.clone())
            .collect()
    }
    fn flag(&self, name: &str) -> bool {
        self.flags.iter().any(|flag| flag == name)
    }
    fn required(&self, name: &str) -> Result<&str, String> {
        self.value(name).ok_or(format!("{name} is required"))
    }
    fn one_positional(&self, what: &str) -> Result<&str, String> {
        match self.positional.as_slice() {
            [only] => Ok(only),
            [] => Err(format!("{what} is required")),
            [_, extra, ..] => Err(format!("Unexpected argument {extra:?}")),
        }
    }
}

fn parse(args: &[String], values: &[&str], flags: &[&str]) -> Result<Args, String> {
    let mut parsed = Args {
        positional: Vec::new(),
        values: Vec::new(),
        flags: Vec::new(),
    };
    let mut iter = args.iter();
    while let Some(arg) = iter.next() {
        let (name, inline) = match arg.split_once('=') {
            Some((name, value)) if name.starts_with("--") => (name, Some(value.to_string())),
            _ => (arg.as_str(), None),
        };
        if flags.contains(&name) && inline.is_none() {
            parsed.flags.push(name.to_string());
        } else if values.contains(&name) {
            let value = match inline {
                Some(value) => value,
                None => iter
                    .next()
                    .cloned()
                    .ok_or(format!("{name} needs a value"))?,
            };
            parsed.values.push((name.to_string(), value));
        } else if arg.starts_with("--") {
            return Err(format!("Unknown option {arg}"));
        } else {
            parsed.positional.push(arg.clone());
        }
    }
    Ok(parsed)
}

/// Exit code plus stdout and stderr text.
fn run(args: &[String]) -> Result<(i32, String, String), String> {
    let Some((command, rest)) = args.split_first() else {
        return Ok((0, HELP.into(), String::new()));
    };
    if matches!(command.as_str(), "--help" | "-h")
        || rest.iter().any(|arg| arg == "--help" || arg == "-h")
    {
        return Ok((0, HELP.into(), String::new()));
    }
    if command == "--version" {
        return Ok((
            0,
            format!("markdown-checks {}", env!("CARGO_PKG_VERSION")),
            String::new(),
        ));
    }
    match command.as_str() {
        "diff" => {
            let parsed = parse(rest, &["--left", "--right"], &[])?;
            if let Some(extra) = parsed.positional.first() {
                return Err(format!("Unexpected argument {extra:?}"));
            }
            let left = PathBuf::from(parsed.required("--left")?);
            let right = PathBuf::from(parsed.required("--right")?);
            Ok(match diff::run(&left, &right) {
                Ok(text) => (0, text, String::new()),
                Err(error) => (2, String::new(), format!("error: {error}")),
            })
        }
        "context-brief" => {
            let parsed = parse(rest, &["--required-heading"], &["--json", "--strict"])?;
            let path = Path::new(parsed.one_positional("FILE")?);
            let checks = context_brief::validate(
                path,
                &parsed.all("--required-heading"),
                parsed.flag("--strict"),
            )?;
            let (text, code) = context_brief::report(&checks, parsed.flag("--json"));
            Ok((code, text, String::new()))
        }
        "scan-changes" => {
            let parsed = parse(
                rest,
                &["--repo", "--base", "--diff-file", "--max-files"],
                &["--json"],
            )?;
            if let Some(extra) = parsed.positional.first() {
                return Err(format!("Unexpected argument {extra:?}"));
            }
            let max_files = match parsed.value("--max-files") {
                None => 80,
                Some(text) => match text.parse::<i64>() {
                    Ok(value) if value >= 0 => value as usize,
                    Ok(_) => {
                        return Ok((
                            2,
                            "ERROR: --max-files must be 0 or greater".into(),
                            String::new(),
                        ))
                    }
                    Err(_) => return Err("--max-files needs an integer".into()),
                },
            };
            let options = scan_changes::Options {
                repo: parsed.value("--repo").unwrap_or(".").to_string(),
                base: parsed.value("--base").map(str::to_string),
                diff_file: parsed.value("--diff-file").map(str::to_string),
                max_files,
                json: parsed.flag("--json"),
            };
            let (text, code) = scan_changes::run(&options);
            Ok((code, text, String::new()))
        }
        "sync-inspect" => {
            let parsed = parse(rest, &[], &["--include-notion-metadata", "--json"])?;
            let path = Path::new(parsed.one_positional("FILE")?);
            let (text, code) = sync::inspect_report(
                path,
                parsed.flag("--include-notion-metadata"),
                parsed.flag("--json"),
            );
            Ok((code, text, String::new()))
        }
        "sync-write" => {
            let parsed = parse(
                rest,
                &["--content-file", "--expected-sha256"],
                &["--dry-run"],
            )?;
            let options = sync::WriteOptions {
                target: PathBuf::from(parsed.one_positional("FILE")?),
                content: PathBuf::from(parsed.required("--content-file")?),
                expected: parsed.required("--expected-sha256")?.to_string(),
                dry_run: parsed.flag("--dry-run"),
            };
            Ok(match sync::write(&options) {
                Ok(text) => (0, text, String::new()),
                Err((code, message)) => (code, String::new(), message),
            })
        }
        other => Err(format!("Unknown command {other:?}")),
    }
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match run(&args) {
        Ok((code, stdout, stderr)) => {
            if !stdout.is_empty() {
                println!("{stdout}");
            }
            if !stderr.is_empty() {
                eprintln!("{stderr}");
            }
            std::process::exit(code);
        }
        Err(error) => {
            eprintln!("error: {error}\n\n{HELP}");
            std::process::exit(2);
        }
    }
}
