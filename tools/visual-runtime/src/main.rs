use visual_runtime::{compact, mcp, Previews, Workspace};

const HELP: &str = "visual-runtime --root DIR inspect
visual-runtime --root DIR artifacts --files FILE [FILE ...]
visual-runtime --root DIR preview --entry FILE.html --files FILE [FILE ...]
visual-runtime mcp

inspect    Framework and version declarations from package.json and Unity settings; scripts never run
artifacts  Bytes and SHA-256 of explicit files relative to the root
preview    Serve a snapshot of the listed files on 127.0.0.1 until Ctrl+C
mcp        Stdio MCP server; each file operation names its own root

Exit codes: 0 success, 1 local error, 2 invalid arguments.";

struct Args {
    root: Option<String>,
    command: String,
    files: Vec<String>,
    entry: Option<String>,
}

fn parse(args: &[String]) -> Result<Args, String> {
    let mut parsed = Args {
        root: None,
        command: String::new(),
        files: Vec::new(),
        entry: None,
    };
    let mut index = 0;
    while index < args.len() {
        let arg = &args[index];
        index += 1;
        let (name, inline) = match arg.split_once('=') {
            Some((name, value)) if name.starts_with("--") => (name, Some(value.to_string())),
            _ => (arg.as_str(), None),
        };
        match name {
            "--root" | "--entry" => {
                let value = match inline {
                    Some(value) => value,
                    None => {
                        index += 1;
                        args.get(index - 1)
                            .cloned()
                            .ok_or(format!("{name} needs a value"))?
                    }
                };
                if name == "--root" {
                    parsed.root = Some(value);
                } else {
                    parsed.entry = Some(value);
                }
            }
            "--files" => {
                parsed.files = inline.into_iter().collect();
                while index < args.len() && !args[index].starts_with("--") {
                    parsed.files.push(args[index].clone());
                    index += 1;
                }
                if parsed.files.is_empty() {
                    return Err("--files needs at least one value".into());
                }
            }
            "inspect" | "artifacts" | "preview" | "mcp" if parsed.command.is_empty() => {
                parsed.command = name.to_string()
            }
            _ => return Err(format!("Unexpected argument {arg:?}")),
        }
    }
    if parsed.command.is_empty() {
        return Err("A command is required".into());
    }
    if parsed.command != "mcp" && parsed.root.is_none() {
        return Err("--root is required".into());
    }
    Ok(parsed)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        println!("{HELP}");
        return;
    }
    if args.first().is_some_and(|arg| arg == "--version") {
        println!("visual-runtime {}", visual_runtime::VERSION);
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
        if let Err(error) = mcp::serve() {
            eprintln!("error: {error}");
            std::process::exit(1);
        }
        return;
    }
    let previews = Previews::default();
    let outcome = Workspace::new(parsed.root.as_deref().unwrap_or("")).and_then(|workspace| {
        match parsed.command.as_str() {
            "inspect" => workspace.inspect(),
            "artifacts" => workspace.artifacts(&parsed.files),
            _ => previews.start(
                &workspace,
                parsed.entry.as_deref().unwrap_or(""),
                &parsed.files,
            ),
        }
    });
    match outcome {
        Ok(result) => {
            println!("{}", compact(&result));
            if parsed.command == "preview" {
                // Serve in the foreground until the process is interrupted.
                loop {
                    std::thread::park();
                }
            }
        }
        Err(_) => {
            println!("{{\"status\":\"local_error\"}}");
            std::process::exit(1);
        }
    }
}
