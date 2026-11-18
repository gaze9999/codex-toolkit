use angular_checks::output::{emit, parse_formats, Emit, Rendered, DEFAULT_FORMATS};
use angular_checks::{
    change_impact, components, form_contract, fsutil, maintainability, preflight,
};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

const HELP: &str =
    "angular-checks components [TERM ...] [-- TERM ...] [--root DIR] [--project NAME] [--changed] [--limit N]
angular-checks form-contract --contract FILE [--root DIR]
angular-checks generator-preflight --identifier ID [--selector NAME] [--allow-existing] [--root DIR]
angular-checks change-impact [--root DIR]
angular-checks maintainability --root DIR --scope PATH --mode files|diff|module --typescript FILE --report FILE.json

Every command accepts --format json,md,html|all, --json, --out DIR and --style-dir DIR.
--root defaults to the current directory. Each run prints a short summary and writes report.md
(or the selected formats) into a new folder outside the root; --out names that folder.
Exit codes: 0 clear, 1 findings (components: no result), 2 invalid input or environment.";

struct Args {
    positional: Vec<String>,
    values: BTreeMap<String, String>,
    flags: Vec<String>,
}

fn parse(args: &[String], value_flags: &[&str], bool_flags: &[&str]) -> Result<Args, String> {
    let mut parsed = Args {
        positional: Vec::new(),
        values: BTreeMap::new(),
        flags: Vec::new(),
    };
    let common = ["--root", "--format", "--out", "--style-dir"];
    let mut iter = args.iter();
    while let Some(arg) = iter.next() {
        if arg == "--" {
            // Everything after the separator is a term, even when it starts with dashes
            parsed.positional.extend(iter.by_ref().cloned());
        } else if !arg.starts_with("--") {
            parsed.positional.push(arg.clone());
        } else if arg == "--json" || bool_flags.contains(&arg.as_str()) {
            parsed.flags.push(arg.clone());
        } else if common.contains(&arg.as_str()) || value_flags.contains(&arg.as_str()) {
            let value = iter.next().ok_or(format!("{arg} needs a value"))?;
            if parsed.values.insert(arg.clone(), value.clone()).is_some() {
                return Err(format!("{arg} is given more than once"));
            }
        } else {
            return Err(format!("Unknown option {arg}"));
        }
    }
    Ok(parsed)
}

fn run(args: &[String]) -> Result<i32, String> {
    let Some((command, rest)) = args.split_first() else {
        println!("{HELP}");
        return Ok(0);
    };
    if matches!(command.as_str(), "--help" | "-h")
        || rest.iter().any(|a| a == "--help" || a == "-h")
    {
        println!(
            "{}",
            if command == "maintainability" {
                maintainability::HELP
            } else {
                HELP
            }
        );
        return Ok(0);
    }
    if command == "--version" {
        println!("angular-checks {}", env!("CARGO_PKG_VERSION"));
        return Ok(0);
    }
    if command == "maintainability" {
        let options = maintainability::parse(rest)
            .map_err(|error| format!("{error}\n{}", maintainability::HELP))?;
        return maintainability::run(&options);
    }
    let (value_flags, bool_flags): (&[&str], &[&str]) = match command.as_str() {
        "components" => (&["--project", "--limit"], &["--changed"]),
        "form-contract" => (&["--contract"], &[]),
        "generator-preflight" => (&["--identifier", "--selector"], &["--allow-existing"]),
        "change-impact" => (&[], &[]),
        other => return Err(format!("Unknown command {other:?}\n{HELP}")),
    };
    let parsed = parse(rest, value_flags, bool_flags)?;
    if command != "components" && !parsed.positional.is_empty() {
        return Err(format!("Unexpected argument {:?}", parsed.positional[0]));
    }
    let value = |name: &str| parsed.values.get(name).map(String::as_str);
    let flag = |name: &str| parsed.flags.iter().any(|f| f == name);
    let formats = match (value("--format"), flag("--json")) {
        (Some(_), true) => return Err("Use --format or --json, not both".into()),
        (Some(list), false) => parse_formats(list)?,
        (None, true) => vec!["json"],
        (None, false) => DEFAULT_FORMATS.to_vec(),
    };
    let options = Emit {
        formats,
        out: value("--out").map(PathBuf::from),
        style_dir: value("--style-dir").map(PathBuf::from),
    };
    let given = value("--root").map_or_else(|| PathBuf::from("."), PathBuf::from);
    let (tool, (rendered, code)): (&str, (Rendered, i32)) = match command.as_str() {
        "components" => {
            let limit = match value("--limit") {
                None => 50,
                Some(text) => text
                    .parse::<usize>()
                    .map_err(|_| "--limit must be 0 or greater")?,
            };
            let root = fsutil::root(&given)?;
            (
                "angular-components",
                components::run(&components::Options {
                    root,
                    query: parsed.positional.clone(),
                    project: value("--project").map(str::to_owned),
                    changed: flag("--changed"),
                    limit,
                })?,
            )
        }
        "form-contract" => {
            let contract = value("--contract").ok_or("--contract is required")?;
            (
                "angular-form-contract",
                form_contract::run(&fsutil::root(&given)?, Path::new(contract))?,
            )
        }
        "generator-preflight" => {
            let identifier = value("--identifier").ok_or("--identifier is required")?;
            let root = fsutil::root(&given)
                .map_err(|_| format!("Generator root does not exist: {}", given.display()))?;
            (
                "angular-generator-preflight",
                preflight::run(
                    &root,
                    identifier,
                    value("--selector"),
                    flag("--allow-existing"),
                )?,
            )
        }
        _ => (
            "angular-change-impact",
            change_impact::run(&fsutil::root(&given)?)?,
        ),
    };
    let scanned = fsutil::root(&given)?;
    emit(tool, &[&scanned], &options, &rendered)?;
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
