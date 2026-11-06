mod apply;
#[cfg(target_os = "macos")]
mod darwin;
mod mcp;
mod reports;
mod safety;
mod scan;
use serde_json::{json, Value};
use std::{
    env, fs,
    io::{self, Write},
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
const VERSION: u64 = 1;
fn batch() -> String {
    format!(
        "{:x}-{:x}",
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos(),
        std::process::id()
    )
}
fn required<'a>(v: &'a Value, k: &str) -> Result<&'a str> {
    v[k].as_str()
        .ok_or_else(|| format!("Missing string: {k}").into())
}
fn list<'a>(v: &'a Value, k: &str) -> Result<&'a Vec<Value>> {
    v[k].as_array()
        .ok_or_else(|| format!("Missing array: {k}").into())
}
fn read_json(p: &Path) -> Result<Value> {
    Ok(serde_json::from_reader(fs::File::open(p)?)?)
}
fn write_new(p: &Path, data: &[u8]) -> Result<()> {
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(p)?;
    f.write_all(data)?;
    f.sync_all()?;
    Ok(())
}
fn home() -> Result<PathBuf> {
    env::var_os(if cfg!(windows) { "USERPROFILE" } else { "HOME" })
        .map(PathBuf::from)
        .ok_or("Missing home directory".into())
}
fn state() -> Result<PathBuf> {
    let base = if cfg!(windows) {
        env::var_os("LOCALAPPDATA")
            .map(PathBuf::from)
            .ok_or("Missing LOCALAPPDATA")?
    } else {
        home()?.join("Library/Application Support")
    };
    let dir = base.join("agent-artifact-audit");
    fs::create_dir_all(&dir)?;
    safety::plain(&dir)?;
    Ok(dir)
}
fn run_dir(out: &str, id: &str) -> Result<PathBuf> {
    let out = std::path::absolute(out)?;
    fs::create_dir_all(&out)?;
    safety::plain(&out)?;
    let dir = out.join(id);
    fs::create_dir(&dir)?;
    Ok(dir)
}
fn dispatch(cmd: &str, args: &Value) -> Result<Value> {
    match cmd {
        "scan" => scan::run(args),
        "apply" => apply::run(args),
        "report" => reports::recover(Path::new(required(args, "run")?)),
        _ => Err("Unknown command".into()),
    }
}
const HELP:&str="agent-artifact-audit scan --workspace PATH [--workspace PATH] [--codex-home PATH] [--claude-home PATH] --out DIR\nagent-artifact-audit apply --report scan.json --selection selection.json --out DIR\nagent-artifact-audit report --run RUN_DIR\nagent-artifact-audit mcp";
fn main() -> Result<()> {
    let mut args = env::args().skip(1);
    let cmd = args.next().unwrap_or_default();
    if cmd.is_empty() || cmd == "--help" || cmd == "-h" {
        println!("{HELP}");
        return Ok(());
    }
    if cmd == "mcp" {
        return mcp::serve();
    }
    let result = (|| -> Result<Value> {
        let mut input = json!({});
        while let Some(flag) = args.next() {
            let key = flag
                .strip_prefix("--")
                .ok_or("Expected --option")?
                .replace('-', "_");
            let allowed = match cmd.as_str() {
                "scan" => vec!["workspace", "out", "codex_home", "claude_home"],
                "apply" => vec!["report", "selection", "out"],
                "report" => vec!["run"],
                _ => return Err("Unknown command".into()),
            };
            if !allowed.contains(&key.as_str()) {
                return Err(format!("Unknown option {flag}").into());
            }
            let value = args.next().ok_or("Missing option value")?;
            if key == "workspace" {
                if input["workspace"].is_null() {
                    input["workspace"] = json!([])
                }
                input["workspace"]
                    .as_array_mut()
                    .unwrap()
                    .push(json!(value))
            } else if input.get(&key).is_some() {
                return Err(format!("Repeated {flag}").into());
            } else {
                input[key] = json!(value)
            }
        }
        dispatch(&cmd, &input)
    })();
    match result {
        Ok(v) => {
            println!("{v}");
            if v["partial"] == true {
                std::process::exit(1)
            }
        }
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2)
        }
    }
    Ok(())
}
