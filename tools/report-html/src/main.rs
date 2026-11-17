use report_html::{render, Style};
use std::fs;
use std::io::{Read, Write};
use std::path::PathBuf;

const HELP: &str = "report-html render --input FILE|- [--style-dir DIR] [--out FILE]\n  Reads report-html/v1 JSON and prints one offline HTML page, or writes it to a new file with --out";
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
        "render" => {}
        _ => return Err(format!("Unknown command {command:?}\n{HELP}")),
    }
    let (pairs, rest) = args.as_chunks::<2>();
    if !rest.is_empty() {
        return Err(format!("Each option needs a value\n{HELP}"));
    }
    let (mut input, mut style_dir, mut out) = (None, None, None);
    for pair in pairs {
        let value = pair[1].as_str();
        match pair[0].as_str() {
            "--input" if !value.is_empty() => input = Some(value),
            "--style-dir" if !value.is_empty() => style_dir = Some(PathBuf::from(value)),
            "--out" if !value.is_empty() => out = Some(PathBuf::from(value)),
            flag => return Err(format!("Invalid option or value for {flag:?}\n{HELP}")),
        }
    }
    let mut data = String::new();
    match input.ok_or("--input is required")? {
        "-" => std::io::stdin()
            .take(INPUT_LIMIT)
            .read_to_string(&mut data)
            .map(|_| ())
            .map_err(|e| e.to_string())?,
        path => {
            let size = fs::metadata(path)
                .map_err(|e| format!("Cannot read {path}: {e}"))?
                .len();
            if size > INPUT_LIMIT {
                return Err(format!("{path} exceeds 64 MiB"));
            }
            data = fs::read_to_string(path).map_err(|e| format!("Cannot read {path}: {e}"))?;
        }
    }
    let report = serde_json::from_str(&data).map_err(|e| format!("Invalid report JSON: {e}"))?;
    let style = match style_dir {
        Some(dir) => Style::load(&dir)?,
        None => Style::builtin(),
    };
    let page = render(&report, &style)?;
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

fn main() {
    if let Err(error) = cli(&std::env::args().skip(1).collect::<Vec<_>>()) {
        eprintln!("report-html: {error}");
        std::process::exit(2);
    }
}
