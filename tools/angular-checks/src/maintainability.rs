//! Bounded, read-only Angular maintenance review: selects and hashes inputs, then runs the
//! Skill's TypeScript/Angular AST worker with the approved installed compiler packages.
use crate::fsutil::posix;
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::path::{Component, Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

/// Contract version recorded in reports; the rule set and result fields are unchanged.
pub const VERSION: &str = "0.1.0";
const EXTENSIONS: [&str; 7] = ["ts", "tsx", "mts", "cts", "html", "css", "scss"];
const TYPESCRIPT: [&str; 4] = ["ts", "tsx", "mts", "cts"];
const STATUSES: [&str; 6] = ["PASS", "FAIL", "WARN", "SKIP", "ERROR", "MANUAL"];
const MODULE_SKIP: [&str; 5] = [".git", "node_modules", "dist", "build", ".angular"];
const MAX_FILES: usize = 1000;
const MAX_BYTES: u64 = 20_000_000;
const WORKER_TIMEOUT: Duration = Duration::from_secs(90);
/// The Skill keeps the single worker source; the binary carries it so no Skill path is needed at run time.
const WORKER: &str =
    include_str!("../../../skills/angular-development/scripts/maintainability_ast.cjs");
const CONVENTIONS: &str =
    include_str!("../../../skills/angular-development/scripts/check_conventions.cjs");

pub const HELP: &str = "angular-checks maintainability --root DIR --scope PATH --mode files|diff|module --typescript FILE --report FILE.json
    [--file PATH ...] [--dependency PATH ...] [--depth static|semantic|runtime] [--profile FILE]
    [--angular-compiler FILE] [--node EXE] [--staged] [--unstaged] [--untracked]

Writes one new JSON report outside --root and prints a one-line summary.
Exit codes: 0 no FAIL or ERROR, 1 mechanical FAIL, 2 tool or input error.";

#[derive(Debug, Default)]
pub struct Options {
    pub root: PathBuf,
    pub scope: String,
    pub mode: String,
    pub files: Vec<String>,
    pub dependencies: Vec<String>,
    pub depth: String,
    pub profile: Option<PathBuf>,
    pub typescript: PathBuf,
    pub angular_compiler: Option<PathBuf>,
    pub node: String,
    pub report: PathBuf,
    pub staged: bool,
    pub unstaged: bool,
    pub untracked: bool,
}

/// Parses the subcommand's own options; `--file` and `--dependency` repeat.
pub fn parse(args: &[String]) -> Result<Options, String> {
    let mut options = Options {
        depth: "static".into(),
        node: "node".into(),
        ..Options::default()
    };
    let (mut root, mut scope, mut mode, mut typescript, mut report) =
        (None, None, None, None, None);
    let mut iter = args.iter();
    while let Some(arg) = iter.next() {
        let mut value = || iter.next().cloned().ok_or(format!("{arg} needs a value"));
        let once = |slot: &mut Option<String>, value: String| match slot.replace(value) {
            Some(_) => Err(format!("{arg} is given more than once")),
            None => Ok(()),
        };
        match arg.as_str() {
            "--staged" => options.staged = true,
            "--unstaged" => options.unstaged = true,
            "--untracked" => options.untracked = true,
            "--file" => options.files.push(value()?),
            "--dependency" => options.dependencies.push(value()?),
            "--root" => once(&mut root, value()?)?,
            "--scope" => once(&mut scope, value()?)?,
            "--mode" => once(&mut mode, value()?)?,
            "--typescript" => once(&mut typescript, value()?)?,
            "--report" => once(&mut report, value()?)?,
            "--depth" => options.depth = value()?,
            "--profile" => options.profile = Some(PathBuf::from(value()?)),
            "--angular-compiler" => options.angular_compiler = Some(PathBuf::from(value()?)),
            "--node" => options.node = value()?,
            other => return Err(format!("Unknown option {other}")),
        }
    }
    let required = |slot: Option<String>, name: &str| slot.ok_or(format!("{name} is required"));
    options.root = PathBuf::from(required(root, "--root")?);
    options.scope = required(scope, "--scope")?;
    options.mode = required(mode, "--mode")?;
    options.typescript = PathBuf::from(required(typescript, "--typescript")?);
    options.report = PathBuf::from(required(report, "--report")?);
    if !["files", "diff", "module"].contains(&options.mode.as_str()) {
        return Err("--mode must be files, diff or module".into());
    }
    if !["static", "semantic", "runtime"].contains(&options.depth.as_str()) {
        return Err("--depth must be static, semantic or runtime".into());
    }
    Ok(options)
}

/// Absolute path with `.`/`..` applied and links resolved for every existing prefix.
fn resolve(path: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for part in path.components() {
        match part {
            Component::CurDir => {}
            Component::ParentDir => {
                out.pop();
            }
            other => {
                out.push(other.as_os_str());
                if let Ok(real) = fs::canonicalize(&out) {
                    out = real;
                }
            }
        }
    }
    out
}

fn absolute(path: &Path) -> PathBuf {
    if path.is_absolute() {
        resolve(path)
    } else {
        resolve(&std::env::current_dir().unwrap_or_default().join(path))
    }
}

/// `value` below `root` after link resolution, or an error when it escapes.
pub fn bounded(root: &Path, value: impl AsRef<Path>) -> Result<PathBuf, String> {
    let path = resolve(&root.join(value));
    if !path.starts_with(root) {
        return Err("Path escapes the selected root".into());
    }
    Ok(path)
}

fn extension(path: &Path) -> String {
    path.extension()
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_default()
}

fn digest(path: &Path) -> Result<String, String> {
    let bytes = fs::read(path).map_err(|error| error.to_string())?;
    Ok(format!("{:x}", Sha256::digest(bytes)))
}

fn relative(path: &Path, root: &Path) -> String {
    posix(path.strip_prefix(root).unwrap_or(path))
}

fn total_bytes(paths: &[PathBuf]) -> u64 {
    paths
        .iter()
        .filter_map(|path| fs::metadata(path).ok())
        .map(|meta| meta.len())
        .sum()
}

fn walk_module(scope: &Path) -> Vec<PathBuf> {
    let mut files = Vec::new();
    let mut pending = vec![scope.to_path_buf()];
    while let Some(current) = pending.pop() {
        let Ok(entries) = fs::read_dir(&current) else {
            continue;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            let name = entry.file_name().to_string_lossy().into_owned();
            let Ok(meta) = fs::symlink_metadata(&path) else {
                continue;
            };
            if meta.is_dir() {
                if !MODULE_SKIP.contains(&name.as_str()) {
                    pending.push(path);
                }
            } else if !(meta.file_type().is_symlink()
                && fs::metadata(&path).is_ok_and(|target| target.is_dir()))
            {
                files.push(path);
            }
        }
    }
    files
}

fn git(root: &Path, args: &[&str]) -> Option<(bool, Vec<u8>)> {
    let output = Command::new("git")
        .args(["--no-optional-locks", "-C"])
        .arg(root)
        .arg("--literal-pathspecs")
        .args(args)
        .current_dir(root)
        .output()
        .ok()?;
    Some((output.status.success(), output.stdout))
}

fn diff_candidates(options: &Options, root: &Path, scope: &Path) -> Result<Vec<PathBuf>, String> {
    if !options.staged && !options.unstaged && !options.untracked {
        return Err("diff mode requires a Git selection flag".into());
    }
    let top = git(root, &["rev-parse", "--show-toplevel"]).filter(|(ok, _)| *ok);
    let top = top.map(|(_, out)| resolve(Path::new(String::from_utf8_lossy(&out).trim())));
    if top.as_deref() != Some(root) {
        return Err("--root must be the Git root in diff mode".into());
    }
    let mut modes: Vec<Vec<&str>> = Vec::new();
    if options.staged {
        modes.push(vec![
            "diff",
            "--cached",
            "--name-only",
            "-z",
            "--diff-filter=ACMRT",
        ]);
    }
    if options.unstaged {
        modes.push(vec!["diff", "--name-only", "-z", "--diff-filter=ACMRT"]);
    }
    if options.untracked {
        modes.push(vec!["ls-files", "--others", "--exclude-standard", "-z"]);
    }
    let pathspec = match relative(scope, root) {
        text if text.is_empty() => ".".to_string(),
        text => text,
    };
    let mut candidates = Vec::new();
    for mut mode in modes {
        mode.extend(["--", pathspec.as_str()]);
        let Some((true, out)) = git(root, &mode) else {
            return Err("Git selection failed; no fallback scan".into());
        };
        for name in out.split(|byte| *byte == 0).filter(|name| !name.is_empty()) {
            candidates.push(bounded(root, String::from_utf8_lossy(name).as_ref())?);
        }
    }
    Ok(candidates)
}

/// Selected review files plus enumerated skips, within the literal scope and size limits.
pub fn select(options: &Options, root: &Path) -> Result<(Vec<PathBuf>, Vec<Value>), String> {
    let literal = Path::new(&options.scope);
    if literal.is_absolute()
        || literal
            .components()
            .any(|part| part == Component::ParentDir)
        || options.scope.starts_with(':')
    {
        return Err("Scope must be a literal root-relative path without parent traversal".into());
    }
    let scope = bounded(root, &options.scope)?;
    let candidates = match options.mode.as_str() {
        "files" => {
            if options.files.is_empty() {
                return Err("files mode requires --file".into());
            }
            options
                .files
                .iter()
                .map(|file| bounded(root, file))
                .collect::<Result<Vec<_>, _>>()?
        }
        mode => {
            if !options.files.is_empty() {
                return Err("--file belongs to files mode".into());
            }
            if mode == "module" {
                if !scope.is_dir() {
                    return Err("module scope must be an existing directory".into());
                }
                walk_module(&scope)
            } else {
                diff_candidates(options, root, &scope)?
            }
        }
    };
    let (mut selected, mut skipped) = (BTreeSet::new(), Vec::new());
    for candidate in candidates.into_iter().collect::<BTreeSet<_>>() {
        let real = bounded(root, &candidate)?;
        if !real.starts_with(&scope) {
            return Err("Selected file escapes the explicit scope".into());
        }
        if !real.is_file() {
            skipped.push(
                json!({ "path": relative(&candidate, root), "reason": "missing-or-not-file" }),
            );
        } else if !EXTENSIONS.contains(&extension(&real).as_str()) {
            skipped
                .push(json!({ "path": relative(&real, root), "reason": "unsupported-extension" }));
        } else {
            selected.insert(real);
        }
    }
    let selected: Vec<PathBuf> = selected.into_iter().collect();
    if selected.len() > MAX_FILES || total_bytes(&selected) > MAX_BYTES {
        return Err("Scope exceeds 1000 files or 20 MB; narrow it explicitly".into());
    }
    Ok((selected, skipped))
}

fn profile(path: Option<&Path>) -> Result<Value, String> {
    let Some(path) = path else {
        return Ok(json!({ "id": "portable", "version": "1" }));
    };
    let text = fs::read_to_string(path).map_err(|error| error.to_string())?;
    let value: Value = serde_json::from_str(text.trim_start_matches('\u{feff}'))
        .map_err(|error| error.to_string())?;
    let invalid =
        || "Invalid profile: explicit id/version and supported data fields required".to_string();
    let object = value.as_object().ok_or_else(invalid)?;
    let allowed = [
        "id",
        "version",
        "explicitPublic",
        "format",
        "compilerOptions",
    ];
    if object.keys().any(|key| !allowed.contains(&key.as_str()))
        || !object.get("id").is_some_and(Value::is_string)
        || !object.get("version").is_some_and(Value::is_string)
    {
        return Err(invalid());
    }
    if object
        .get("explicitPublic")
        .is_some_and(|flag| !flag.is_boolean())
    {
        return Err("explicitPublic must be boolean".into());
    }
    if let Some(format) = object.get("format") {
        let valid = format.as_object().is_some_and(|fields| {
            fields.len() == 2
                && fields
                    .get("indentSize")
                    .and_then(Value::as_i64)
                    .is_some_and(|size| (1..=16).contains(&size))
                && fields
                    .get("indentSize")
                    .is_some_and(|size| size.is_i64() || size.is_u64())
                && fields
                    .get("semicolons")
                    .and_then(Value::as_str)
                    .is_some_and(|mode| ["insert", "remove", "ignore"].contains(&mode))
        });
        if !valid {
            return Err("Invalid explicit formatter settings".into());
        }
    }
    Ok(value)
}

/// Unique temporary folder holding the worker and its sibling module, removed on drop.
struct WorkerDir(PathBuf);

impl WorkerDir {
    fn create() -> Result<Self, String> {
        let base = std::env::temp_dir();
        for attempt in 0..100u32 {
            let stamp = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map_or(0, |time| time.as_nanos());
            let path = base.join(format!(
                "angular-checks-worker-{}-{stamp}-{attempt}",
                std::process::id()
            ));
            if fs::create_dir(&path).is_ok() {
                let dir = Self(path);
                fs::write(dir.0.join("maintainability_ast.cjs"), WORKER)
                    .map_err(|error| error.to_string())?;
                fs::write(dir.0.join("check_conventions.cjs"), CONVENTIONS)
                    .map_err(|error| error.to_string())?;
                return Ok(dir);
            }
        }
        Err("Could not create a private worker folder".into())
    }
}

impl Drop for WorkerDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn run_worker(options: &Options, root: &Path, request: &Value) -> Result<Value, String> {
    let worker = WorkerDir::create()?;
    let mut command = Command::new(&options.node);
    command
        .arg(worker.0.join("maintainability_ast.cjs"))
        .current_dir(root)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000);
    }
    let failed =
        || "AST worker failed; inspect approved local environment, raw stderr withheld".to_string();
    let mut child = command.spawn().map_err(|_| failed())?;
    child
        .stdin
        .take()
        .ok_or_else(failed)?
        .write_all(request.to_string().as_bytes())
        .map_err(|_| failed())?;
    let mut stdout = child.stdout.take().ok_or_else(failed)?;
    let reader = std::thread::spawn(move || {
        let mut text = String::new();
        stdout.read_to_string(&mut text).map(|_| text)
    });
    let started = Instant::now();
    let status = loop {
        if let Some(status) = child.try_wait().map_err(|_| failed())? {
            break status;
        }
        if started.elapsed() > WORKER_TIMEOUT {
            let _ = child.kill();
            let _ = child.wait();
            return Err(failed());
        }
        std::thread::sleep(Duration::from_millis(20));
    };
    let text = reader.join().map_err(|_| failed())?.map_err(|_| failed())?;
    if !status.success() {
        return Err(failed());
    }
    serde_json::from_str(&text).map_err(|error| error.to_string())
}

fn error_row(options: &Options, evidence: String) -> Value {
    json!({
        "ruleId": "TOOL.INPUT", "status": "ERROR", "severity": "error", "confidence": "high",
        "path": null, "line": null, "scope": options.scope, "depth": options.depth, "method": "input/runner boundary",
        "evidence": evidence, "sourceVersion": VERSION, "impact": "Coverage incomplete",
        "verification": "Correct inputs or environment; rerun", "autoFix": false,
    })
}

fn review(options: &Options, root: &Path, result: &mut Map<String, Value>) -> Result<(), String> {
    if options.mode != "diff" && (options.staged || options.unstaged || options.untracked) {
        return Err("Git selection flags require diff mode".into());
    }
    let (files, skipped) = select(options, root)?;
    let dependencies = options
        .dependencies
        .iter()
        .map(|path| bounded(root, path))
        .collect::<Result<Vec<_>, _>>()?;
    if dependencies
        .iter()
        .any(|path| !path.is_file() || !TYPESCRIPT.contains(&extension(path).as_str()))
    {
        return Err("Dependencies must be explicit existing TypeScript files".into());
    }
    if dependencies.len() > MAX_FILES || total_bytes(&dependencies) > MAX_BYTES {
        return Err("Dependency scope exceeds limits".into());
    }
    let profile_value = profile(options.profile.as_deref())?;
    let observed: BTreeSet<PathBuf> = files.iter().chain(&dependencies).cloned().collect();
    let mut hashes = Map::new();
    for path in &observed {
        hashes.insert(relative(path, root), digest(path)?.into());
    }
    result.insert("inputs".into(), Value::Object(hashes.clone()));
    result.insert("skipped".into(), skipped.into());
    result.insert("profile".into(), profile_value.clone());
    let profile_hash = match &options.profile {
        Some(path) => Value::from(digest(path)?),
        None => Value::Null,
    };
    result.insert("profileSha256".into(), profile_hash);
    let text = |paths: &[PathBuf]| {
        paths
            .iter()
            .map(|path| path.to_string_lossy().into_owned())
            .collect::<Vec<_>>()
    };
    let request = json!({
        "root": root.to_string_lossy(), "files": text(&files), "dependencies": text(&dependencies),
        "depth": options.depth, "profile": profile_value,
        "typescript": absolute(&options.typescript).to_string_lossy(),
        "angularCompiler": options.angular_compiler.as_deref().map(|path| absolute(path).to_string_lossy().into_owned()),
    });
    if let Value::Object(fields) = run_worker(options, root, &request)? {
        result.extend(fields);
    }
    for path in &observed {
        let unchanged = path.is_file()
            && digest(path).ok().as_deref()
                == hashes.get(&relative(path, root)).and_then(Value::as_str);
        if !unchanged {
            return Err("Inputs changed during review; findings require a fresh snapshot".into());
        }
    }
    result.insert("inputsUnchanged".into(), true.into());
    Ok(())
}

/// Runs one review and returns the exit code; argument errors return before any report.
pub fn run(options: &Options) -> Result<i32, String> {
    let root = fs::canonicalize(&options.root)
        .map_err(|error| format!("{}: {error}", options.root.display()))?;
    let report = absolute(&options.report);
    if fs::symlink_metadata(&report).is_ok()
        || report.starts_with(&root)
        || extension(&report) != "json"
    {
        return Err("Report must be a new .json file outside the scan root".into());
    }
    let mut result = Map::new();
    result.insert("schemaVersion".into(), 1.into());
    result.insert("toolVersion".into(), VERSION.into());
    result.insert(
        "selection".into(),
        json!({ "mode": options.mode, "scope": options.scope, "depth": options.depth, "content": "working-tree", "dependencies": options.dependencies }),
    );
    result.insert("results".into(), json!([]));
    if let Err(error) = review(options, &root, &mut result) {
        if let Some(Value::Array(rows)) = result.get_mut("results") {
            rows.push(error_row(options, error));
        }
    }
    let rows = result
        .get("results")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let mut summary = Map::new();
    for status in STATUSES {
        summary.insert(
            status.into(),
            rows.iter()
                .filter(|row| row["status"] == status)
                .count()
                .into(),
        );
    }
    let count = |status: &str| summary[status].as_u64().unwrap_or(0);
    let exit = if count("ERROR") > 0 {
        2
    } else if count("FAIL") > 0 {
        1
    } else {
        0
    };
    let complete = ["ERROR", "SKIP", "MANUAL"]
        .iter()
        .all(|status| count(status) == 0);
    result.insert("summary".into(), Value::Object(summary.clone()));
    result.insert("exitCode".into(), exit.into());
    result.insert("complete".into(), complete.into());
    // Exclusive creation keeps evidence and sources from being overwritten through a link.
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&report)
        .map_err(|error| format!("{}: {error}", report.display()))?;
    let text =
        serde_json::to_string_pretty(&Value::Object(result)).map_err(|error| error.to_string())?;
    file.write_all(format!("{text}\n").as_bytes())
        .map_err(|error| error.to_string())?;
    println!(
        "{}",
        json!({ "report": report.to_string_lossy(), "summary": summary, "exitCode": exit, "complete": complete })
    );
    Ok(exit)
}
