use decisions::{
    compact, completed, config_from, evaluate, mcp, preview, read_json, status, Config, Https,
    ReadError,
};
use serde_json::{json, Value};
use std::path::PathBuf;

const HELP: &str = "decisions [--config FILE] status
decisions [--config FILE] validate --input REQUEST.json
decisions [--config FILE] evaluate --input REQUEST.json [--approved]
decisions [--config FILE] mcp

status    Check that the selected credential variable has a value; no network
validate  Validate the request offline and return its size and SHA-256, never the evidence
evaluate  Send one request to https://api.openai.com/v1/decisions, only with --approved
mcp       Serve decisions_status, decisions_validate and decisions_evaluate over stdio

--config accepts JSON with credential_env, model and timeout_seconds; never secret values.
Exit codes: 0 completed (including refusals), 1 any other status, 2 invalid arguments.";

struct Args {
    config: Option<PathBuf>,
    command: String,
    input: Option<PathBuf>,
    approved: bool,
}

fn parse(args: &[String]) -> Result<Args, String> {
    let mut parsed = Args {
        config: None,
        command: String::new(),
        input: None,
        approved: false,
    };
    let mut iter = args.iter();
    while let Some(arg) = iter.next() {
        let (name, inline) = match arg.split_once('=') {
            Some((name, value)) if name.starts_with("--") => (name, Some(value.to_string())),
            _ => (arg.as_str(), None),
        };
        let mut value = |label: &str| {
            inline
                .clone()
                .or_else(|| iter.next().cloned())
                .ok_or(format!("{label} needs a value"))
        };
        match name {
            "--config" => parsed.config = Some(PathBuf::from(value("--config")?)),
            "--input" => parsed.input = Some(PathBuf::from(value("--input")?)),
            "--approved" if inline.is_none() => parsed.approved = true,
            "status" | "validate" | "evaluate" | "mcp" if parsed.command.is_empty() => {
                parsed.command = name.to_string()
            }
            _ => return Err(format!("Unexpected argument {arg:?}")),
        }
    }
    if parsed.command.is_empty() {
        return Err("A command is required".into());
    }
    if matches!(parsed.command.as_str(), "validate" | "evaluate") && parsed.input.is_none() {
        return Err("--input is required".into());
    }
    Ok(parsed)
}

fn load_config(path: &Option<PathBuf>) -> Result<Config, Value> {
    let supplied = match path {
        None => None,
        Some(path) => Some(read_json(path, 4096).map_err(failure)?),
    };
    config_from(supplied.as_ref())
        .map_err(|problem| json!({"status": "invalid_input", "reason": problem.0}))
}

fn failure(error: ReadError) -> Value {
    match error {
        ReadError::Local => json!({"status": "local_error"}),
        ReadError::Problem(problem) => json!({"status": "invalid_input", "reason": problem.0}),
    }
}

fn run(args: &Args) -> Value {
    let config = match load_config(&args.config) {
        Ok(config) => config,
        Err(result) => return result,
    };
    if args.command == "status" {
        return status(&config);
    }
    let request = match read_json(
        args.input.as_deref().unwrap_or_else(|| "".as_ref()),
        decisions::MAX_BYTES,
    ) {
        Ok(request) => request,
        Err(error) => return failure(error),
    };
    let outcome = if args.command == "validate" {
        preview(&request, &config)
    } else {
        evaluate(&request, &config, args.approved, &Https)
    };
    outcome.unwrap_or_else(|problem| json!({"status": "invalid_input", "reason": problem.0}))
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        println!("{HELP}");
        return;
    }
    if args.first().is_some_and(|arg| arg == "--version") {
        println!("decisions {}", decisions::VERSION);
        return;
    }
    let parsed = match parse(&args) {
        Ok(parsed) => parsed,
        Err(error) => {
            eprintln!("error: {error}\n\n{HELP}");
            std::process::exit(2);
        }
    };
    if parsed.command == "mcp" {
        let config = match load_config(&parsed.config) {
            Ok(config) => config,
            Err(result) => {
                eprintln!("{}", compact(&result));
                std::process::exit(2);
            }
        };
        if let Err(error) = mcp::serve(&config) {
            eprintln!("error: {error}");
            std::process::exit(1);
        }
        return;
    }
    let result = run(&parsed);
    println!("{}", compact(&result));
    let done = result["status"].as_str().is_some_and(completed);
    std::process::exit(if done { 0 } else { 1 });
}
