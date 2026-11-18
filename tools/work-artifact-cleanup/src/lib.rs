//! Preview and quarantine disposable development caches and work artifacts.
use chrono::{DateTime, Local, Utc};
use serde_json::{json, Map, Value};
use std::fs::{self, File, OpenOptions};
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{Duration, SystemTime};

const CACHE_DIRECTORIES: [&str; 7] = [
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "htmlcov",
];
const BUILD_DIRECTORIES: [&str; 2] = ["build", "dist"];
const WORK_DIRECTORIES: [&str; 4] = ["work", ".work", "tmp", "temp"];
const CACHE_FILE_NAMES: [&str; 4] = [".coverage", ".DS_Store", "Thumbs.db", "desktop.ini"];
const CACHE_FILE_SUFFIXES: [&str; 5] = ["pyc", "pyo", "tmp", "temp", "swp"];
const NEVER_ENTER: [&str; 7] = [
    ".git",
    ".hg",
    ".svn",
    ".codex",
    "logs",
    "backups",
    "quarantine",
];
const REPOSITORY_MARKERS: [&str; 3] = [".git", ".hg", ".svn"];
/// Marker file name and owners stay compatible with batches written by the earlier Python tool.
pub const QUARANTINE_MARKER: &str = ".my-py-tools-quarantine.json";
const MARKER_TOOL: &str = "work-artifact-cleanup";
const OWNED_TOOLS: [&str; 2] = [MARKER_TOOL, "my-py-tools.cleanup_work_artifacts"];
const MAX_DAYS: f64 = 365_000.0;

pub const USAGE: &str = "usage: work-artifact-cleanup [--root [PATH]]... [--apply] [--include-build] [--include-work-dirs]
                             [--min-age-days DAYS] [--output-dir PATH] [--purge-quarantine] [--older-than-days DAYS]

Preview and quarantine disposable development caches and work artifacts.
  --root [PATH]           Directory to scan; may be repeated. Omit its value to use the current directory.
  --apply                 Move candidates to quarantine; default is preview.
  --include-build         Include untracked build/dist/*.egg-info directories.
  --include-work-dirs     Include untracked work/.work/tmp/temp directories.
  --min-age-days DAYS     Minimum age in days; default: 1.
  --output-dir PATH       Parent for logs and quarantine; default: ~/.work-artifact-cleaner.
  --purge-quarantine      Permanently delete old quarantine runs this tool created.
  --older-than-days DAYS  Quarantine retention before purge; default: 7.

Exit codes: 0 preview, quarantine or purge completed; 2 invalid input, safety check, I/O or Git failure";

#[derive(Debug)]
pub struct Options {
    pub roots: Vec<String>,
    pub apply: bool,
    pub include_build: bool,
    pub include_work_dirs: bool,
    pub min_age_days: f64,
    pub output_dir: PathBuf,
    pub purge_quarantine: bool,
    pub older_than_days: f64,
}

fn home() -> PathBuf {
    std::env::var_os("HOME")
        .or_else(|| std::env::var_os("USERPROFILE"))
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."))
}

fn expand_user(value: &str) -> PathBuf {
    match value.strip_prefix('~') {
        Some(rest) if rest.is_empty() || rest.starts_with('/') || rest.starts_with('\\') => {
            home().join(rest.trim_start_matches(['/', '\\']))
        }
        _ => PathBuf::from(value),
    }
}

pub fn parse_args(args: &[String]) -> Result<Options, String> {
    let mut options = Options {
        roots: Vec::new(),
        apply: false,
        include_build: false,
        include_work_dirs: false,
        min_age_days: 1.0,
        output_dir: home().join(".work-artifact-cleaner"),
        purge_quarantine: false,
        older_than_days: 7.0,
    };
    let mut index = 0;
    let days = |value: Option<&String>, name: &str| -> Result<f64, String> {
        value
            .ok_or(format!("{name} needs a value"))?
            .parse::<f64>()
            .map_err(|_| format!("{name} needs a number"))
    };
    while index < args.len() {
        let arg = &args[index];
        let (flag, inline) = match arg.split_once('=') {
            Some((flag, value)) if flag.starts_with("--") => (flag, Some(value.to_string())),
            _ => (arg.as_str(), None),
        };
        let mut take = || -> Option<String> {
            inline.clone().or_else(|| {
                index += 1;
                args.get(index).cloned()
            })
        };
        match flag {
            "--root" => {
                let value = match inline.clone() {
                    Some(value) => value,
                    None if args
                        .get(index + 1)
                        .is_some_and(|next| !next.starts_with('-')) =>
                    {
                        index += 1;
                        args[index].clone()
                    }
                    None => ".".into(),
                };
                options.roots.push(value);
            }
            "--apply" => options.apply = true,
            "--include-build" => options.include_build = true,
            "--include-work-dirs" => options.include_work_dirs = true,
            "--purge-quarantine" => options.purge_quarantine = true,
            "--min-age-days" => options.min_age_days = days(take().as_ref(), flag)?,
            "--older-than-days" => options.older_than_days = days(take().as_ref(), flag)?,
            "--output-dir" => {
                options.output_dir = expand_user(&take().ok_or("--output-dir needs a value")?)
            }
            other => return Err(format!("unrecognized argument {other}")),
        }
        index += 1;
    }
    for value in [options.min_age_days, options.older_than_days] {
        if !value.is_finite() || !(0.0..=MAX_DAYS).contains(&value) {
            return Err("day values must be finite and between 0 and 365000".into());
        }
    }
    Ok(options)
}

/// Python-compatible ISO 8601 text: microseconds only when present, explicit +00:00 offset.
pub fn utc_iso(time: SystemTime) -> String {
    let value: DateTime<Utc> = time.into();
    let format = if value.timestamp_subsec_micros() == 0 {
        "%Y-%m-%dT%H:%M:%S+00:00"
    } else {
        "%Y-%m-%dT%H:%M:%S%.6f+00:00"
    };
    value.format(format).to_string()
}

fn cutoff(days: f64) -> SystemTime {
    SystemTime::now()
        .checked_sub(Duration::from_secs_f64(days * 86_400.0))
        .unwrap_or(SystemTime::UNIX_EPOCH)
}

fn is_symlink(path: &Path) -> bool {
    fs::symlink_metadata(path)
        .map(|meta| meta.file_type().is_symlink())
        .unwrap_or(false)
}

fn real_dir(path: &Path) -> bool {
    fs::symlink_metadata(path)
        .map(|meta| meta.is_dir())
        .unwrap_or(false)
}

/// Directory entries split like os.walk: names that resolve to directories, then the rest.
fn split_entries(path: &Path) -> io::Result<(Vec<String>, Vec<String>)> {
    let (mut directories, mut files) = (Vec::new(), Vec::new());
    for entry in fs::read_dir(path)? {
        let entry = entry?;
        let name = entry.file_name().to_string_lossy().into_owned();
        if fs::metadata(entry.path())
            .map(|meta| meta.is_dir())
            .unwrap_or(false)
        {
            directories.push(name);
        } else {
            files.push(name);
        }
    }
    directories.sort();
    files.sort();
    Ok((directories, files))
}

fn mtime(meta: &fs::Metadata) -> SystemTime {
    meta.modified().unwrap_or(SystemTime::UNIX_EPOCH)
}

/// Total file bytes and the newest modification time inside a directory, without following links.
pub fn directory_metrics(path: &Path) -> (u64, SystemTime) {
    let Ok(meta) = fs::symlink_metadata(path) else {
        return (0, SystemTime::UNIX_EPOCH);
    };
    if meta.file_type().is_symlink() {
        return (0, mtime(&meta));
    }
    let (mut total, mut latest) = (0, mtime(&meta));
    let mut pending = vec![path.to_path_buf()];
    while let Some(current) = pending.pop() {
        if let Ok(meta) = fs::symlink_metadata(&current) {
            latest = latest.max(mtime(&meta));
        }
        let Ok(entries) = fs::read_dir(&current) else {
            continue;
        };
        for entry in entries.flatten() {
            let Ok(meta) = fs::symlink_metadata(entry.path()) else {
                continue;
            };
            if meta.is_dir() {
                pending.push(entry.path());
            } else if fs::metadata(entry.path())
                .map(|target| !target.is_dir())
                .unwrap_or(true)
            {
                total += meta.len();
                latest = latest.max(mtime(&meta));
            }
        }
    }
    (total, latest)
}

pub fn contains_nested_repository(path: &Path) -> bool {
    if !real_dir(path) {
        return false;
    }
    let mut pending = vec![path.to_path_buf()];
    while let Some(current) = pending.pop() {
        let Ok((directories, files)) = split_entries(&current) else {
            continue;
        };
        if directories
            .iter()
            .chain(&files)
            .any(|name| REPOSITORY_MARKERS.contains(&name.as_str()))
        {
            return true;
        }
        for name in directories {
            let child = current.join(&name);
            if !NEVER_ENTER.contains(&name.as_str()) && !is_symlink(&child) {
                pending.push(child);
            }
        }
    }
    false
}

fn repository_root(path: &Path) -> Option<PathBuf> {
    let directory = if path.is_dir() { path } else { path.parent()? };
    let output = Command::new("git")
        .arg("-C")
        .arg(directory)
        .args(["rev-parse", "--show-toplevel"])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    PathBuf::from(String::from_utf8_lossy(&output.stdout).trim())
        .canonicalize()
        .ok()
}

pub fn contains_tracked_content(path: &Path) -> bool {
    let Some(repository) = repository_root(path) else {
        return false;
    };
    let Ok(resolved) = path.canonicalize() else {
        return false;
    };
    let Ok(relative) = resolved.strip_prefix(&repository) else {
        return false;
    };
    let mut pathspec = relative.to_string_lossy().replace('\\', "/");
    if real_dir(path) {
        pathspec.push('/');
    }
    match Command::new("git")
        .arg("-C")
        .arg(&repository)
        .args(["ls-files", "-z", "--", &pathspec])
        .output()
    {
        Ok(output) => !output.status.success() || !output.stdout.is_empty(),
        Err(_) => true,
    }
}

fn reason_for(
    path: &Path,
    name: &str,
    include_build: bool,
    include_work_dirs: bool,
) -> Option<&'static str> {
    let lower = name.to_lowercase();
    if real_dir(path) {
        if CACHE_DIRECTORIES.contains(&name) {
            return Some("standard_cache_directory");
        }
        if include_build
            && (BUILD_DIRECTORIES.contains(&lower.as_str()) || lower.ends_with(".egg-info"))
        {
            return Some("optional_build_directory");
        }
        if include_work_dirs && WORK_DIRECTORIES.contains(&lower.as_str()) {
            return Some("optional_work_directory");
        }
        return None;
    }
    let suffix = Path::new(name)
        .extension()
        .map(|value| value.to_string_lossy().to_lowercase());
    let cache_suffix = suffix.is_some_and(|value| CACHE_FILE_SUFFIXES.contains(&value.as_str()));
    (CACHE_FILE_NAMES.contains(&name) || cache_suffix || name.ends_with('~'))
        .then_some("standard_cache_file")
}

#[derive(Debug, Clone)]
pub struct Candidate {
    pub root: PathBuf,
    pub path: PathBuf,
    pub relative_path: String,
    pub kind: &'static str,
    pub reason: &'static str,
    pub size_bytes: u64,
    pub modified_at: String,
}

impl Candidate {
    fn to_json(&self) -> Value {
        json!({
            "root": display(&self.root), "path": display(&self.path), "relative_path": self.relative_path,
            "kind": self.kind, "reason": self.reason, "size_bytes": self.size_bytes, "modified_at": self.modified_at,
        })
    }
}

fn display(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

fn skip(skipped: &mut Vec<Value>, path: &Path, reason: impl Into<String>) {
    skipped.push(json!({ "path": display(path), "reason": reason.into() }));
}

fn relative(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .to_string_lossy()
        .replace('\\', "/")
}

pub fn scan_root(root: &Path, options: &Options) -> (Vec<Candidate>, Vec<Value>) {
    let limit = cutoff(options.min_age_days);
    let (mut candidates, mut skipped) = (Vec::new(), Vec::new());
    let mut pending = vec![root.to_path_buf()];
    while let Some(current) = pending.pop() {
        let Ok((directories, files)) = split_entries(&current) else {
            continue;
        };
        let mut descend = Vec::new();
        for name in directories
            .iter()
            .filter(|name| !NEVER_ENTER.contains(&name.as_str()))
        {
            let path = current.join(name);
            let Some(reason) = reason_for(
                &path,
                name,
                options.include_build,
                options.include_work_dirs,
            ) else {
                if !is_symlink(&path) {
                    descend.push(path);
                }
                continue;
            };
            if contains_nested_repository(&path) {
                skip(&mut skipped, &path, "contains_nested_repository");
                continue;
            }
            if contains_tracked_content(&path) {
                skip(&mut skipped, &path, "contains_git_tracked_content");
                continue;
            }
            if let Err(error) = fs::symlink_metadata(&path) {
                skip(&mut skipped, &path, format!("stat_failed: {error}"));
                continue;
            }
            let (size, latest) = directory_metrics(&path);
            if latest > limit {
                skip(&mut skipped, &path, "newer_than_minimum_age");
                continue;
            }
            candidates.push(Candidate {
                root: root.to_path_buf(),
                relative_path: relative(root, &path),
                path,
                kind: "directory",
                reason,
                size_bytes: size,
                modified_at: utc_iso(latest),
            });
        }
        for name in &files {
            let path = current.join(name);
            let Some(reason) = reason_for(
                &path,
                name,
                options.include_build,
                options.include_work_dirs,
            ) else {
                continue;
            };
            if contains_tracked_content(&path) {
                skip(&mut skipped, &path, "git_tracked");
                continue;
            }
            let meta = match fs::symlink_metadata(&path) {
                Ok(meta) => meta,
                Err(error) => {
                    skip(&mut skipped, &path, format!("stat_failed: {error}"));
                    continue;
                }
            };
            if mtime(&meta) > limit {
                skip(&mut skipped, &path, "newer_than_minimum_age");
                continue;
            }
            candidates.push(Candidate {
                root: root.to_path_buf(),
                relative_path: relative(root, &path),
                path,
                kind: "file",
                reason,
                size_bytes: meta.len(),
                modified_at: utc_iso(mtime(&meta)),
            });
        }
        descend.reverse();
        pending.extend(descend);
    }
    (candidates, skipped)
}

pub fn resolve_roots(values: &[String]) -> Result<Vec<PathBuf>, String> {
    let defaults = [".".to_string()];
    let values = if values.is_empty() {
        &defaults[..]
    } else {
        values
    };
    let mut roots = Vec::new();
    for value in values {
        let path = expand_user(value);
        let root = path.canonicalize().map_err(|_| {
            format!(
                "Root does not exist or is not a directory: {}",
                path.display()
            )
        })?;
        if !root.is_dir() {
            return Err(format!(
                "Root does not exist or is not a directory: {}",
                root.display()
            ));
        }
        if root.parent().is_none() {
            return Err(format!(
                "Refusing to scan a filesystem root: {}",
                root.display()
            ));
        }
        if !roots.contains(&root) {
            roots.push(root);
        }
    }
    Ok(roots)
}

fn sync_write(path: &Path, text: &str) -> io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let temporary = PathBuf::from(format!("{}.tmp", path.display()));
    let mut handle = File::create(&temporary)?;
    handle.write_all(text.as_bytes())?;
    handle.sync_all()?;
    fs::rename(&temporary, path)
}

fn pretty(value: &Value) -> String {
    serde_json::to_string_pretty(value).unwrap_or_default()
}

pub fn write_json(path: &Path, value: &Value) -> io::Result<()> {
    sync_write(path, &(pretty(value) + "\n"))
}

pub fn append_event(path: &Path, event: Value) -> io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut record = Map::new();
    record.insert("timestamp".into(), utc_iso(SystemTime::now()).into());
    if let Value::Object(fields) = event {
        record.extend(fields);
    }
    let mut handle = OpenOptions::new().create(true).append(true).open(path)?;
    writeln!(handle, "{}", Value::Object(record))?;
    handle.sync_all()
}

fn copy_tree(source: &Path, target: &Path) -> io::Result<()> {
    let meta = fs::symlink_metadata(source)?;
    if meta.is_dir() {
        fs::create_dir_all(target)?;
        for entry in fs::read_dir(source)? {
            let entry = entry?;
            copy_tree(&entry.path(), &target.join(entry.file_name()))?;
        }
    } else if meta.file_type().is_symlink() {
        let link = fs::read_link(source)?;
        #[cfg(unix)]
        std::os::unix::fs::symlink(link, target)?;
        #[cfg(windows)]
        std::os::windows::fs::symlink_file(link, target)?;
    } else {
        fs::copy(source, target)?;
    }
    Ok(())
}

/// Rename within one volume; copy then remove when the rename crosses volumes.
fn move_path(source: &Path, target: &Path) -> io::Result<()> {
    if fs::rename(source, target).is_ok() {
        return Ok(());
    }
    copy_tree(source, target)?;
    if real_dir(source) {
        fs::remove_dir_all(source)
    } else {
        fs::remove_file(source)
    }
}

pub fn quarantine(
    candidates: &[Candidate],
    roots: &[PathBuf],
    destination: &Path,
    event_log: &Path,
) -> io::Result<Vec<Value>> {
    let mut moved = Vec::new();
    if !candidates.is_empty() {
        write_json(
            &destination.join(QUARANTINE_MARKER),
            &json!({ "schema_version": 1, "tool": MARKER_TOOL, "created_at": utc_iso(SystemTime::now()) }),
        )?;
    }
    for candidate in candidates {
        let number = roots
            .iter()
            .position(|root| root == &candidate.root)
            .map_or(0, |index| index + 1);
        let root_name = candidate
            .root
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_else(|| "scan".into());
        let target = destination
            .join(format!("root-{number:02}-{root_name}"))
            .join(&candidate.relative_path);
        let source = &candidate.path;
        if fs::symlink_metadata(source).is_err() {
            append_event(
                event_log,
                json!({ "event": "skipped_missing", "source": display(source) }),
            )?;
            continue;
        }
        if contains_nested_repository(source) || contains_tracked_content(source) {
            append_event(
                event_log,
                json!({ "event": "skipped_recheck", "source": display(source) }),
            )?;
            continue;
        }
        if let Some(parent) = target.parent() {
            fs::create_dir_all(parent)?;
        }
        if fs::symlink_metadata(&target).is_ok() {
            return Err(io::Error::new(
                io::ErrorKind::AlreadyExists,
                format!("Quarantine target already exists: {}", target.display()),
            ));
        }
        move_path(source, &target)?;
        let record = json!({ "source": display(source), "destination": display(&target) });
        let mut event = json!({ "event": "quarantined" });
        if let (Value::Object(fields), Value::Object(extra)) = (&mut event, record.clone()) {
            fields.extend(extra);
        }
        append_event(event_log, event)?;
        moved.push(record);
    }
    Ok(moved)
}

pub fn purge_quarantine(
    base: &Path,
    older_than_days: f64,
    event_log: &Path,
) -> io::Result<(u64, u64)> {
    if !real_dir(base) {
        return Ok((0, 0));
    }
    let limit = cutoff(older_than_days);
    let (mut count, mut size) = (0, 0);
    let mut runs: Vec<PathBuf> = fs::read_dir(base)?
        .flatten()
        .map(|entry| entry.path())
        .collect();
    runs.sort();
    for run in runs {
        if !real_dir(&run) {
            continue;
        }
        let owned = fs::read_to_string(run.join(QUARANTINE_MARKER))
            .ok()
            .and_then(|text| serde_json::from_str::<Value>(&text).ok())
            .and_then(|marker| {
                marker
                    .get("tool")
                    .and_then(Value::as_str)
                    .map(str::to_string)
            })
            .is_some_and(|tool| OWNED_TOOLS.contains(&tool.as_str()));
        if !owned {
            continue;
        }
        let (run_size, latest) = directory_metrics(&run);
        if latest > limit {
            continue;
        }
        fs::remove_dir_all(&run)?;
        count += 1;
        size += run_size;
        append_event(
            event_log,
            json!({ "event": "purged", "path": display(&run), "size_bytes": run_size }),
        )?;
    }
    Ok((count, size))
}

fn normalized_key(path: &Path) -> String {
    let resolved = path.canonicalize().unwrap_or_else(|_| path.to_path_buf());
    let text = display(&resolved);
    if cfg!(windows) {
        text.to_lowercase()
    } else {
        text
    }
}

fn execute(
    options: &Options,
    out: &mut dyn Write,
    log_directory: &Path,
    event_log: &Path,
    name: &str,
) -> Result<(), String> {
    let output_directory = options
        .output_dir
        .canonicalize()
        .unwrap_or_else(|_| options.output_dir.clone());
    let quarantine_base = output_directory.join("quarantine");
    let io_error = |error: io::Error| error.to_string();
    if options.purge_quarantine {
        let (count, size) = purge_quarantine(&quarantine_base, options.older_than_days, event_log)
            .map_err(io_error)?;
        let result = json!({ "mode": "purge", "status": "completed", "removed_runs": count, "removed_bytes": size });
        write_json(&log_directory.join("result.json"), &result).map_err(io_error)?;
        writeln!(out, "{}", pretty(&result)).map_err(io_error)?;
        return Ok(());
    }
    let roots = resolve_roots(&options.roots)?;
    let (mut candidates, mut skipped) = (Vec::new(), Vec::new());
    for root in &roots {
        let (found, passed) = scan_root(root, options);
        candidates.extend(found);
        skipped.extend(passed);
    }
    let mut seen = std::collections::HashSet::new();
    candidates.retain(|candidate| seen.insert(normalized_key(&candidate.path)));
    let candidate_bytes: u64 = candidates.iter().map(|item| item.size_bytes).sum();
    let mode = if options.apply {
        "quarantine"
    } else {
        "preview"
    };
    let manifest = json!({
        "schema_version": 1, "mode": mode, "created_at": utc_iso(SystemTime::now()),
        "roots": roots.iter().map(|root| display(root)).collect::<Vec<_>>(),
        "candidate_count": candidates.len(), "candidate_bytes": candidate_bytes,
        "candidates": candidates.iter().map(Candidate::to_json).collect::<Vec<_>>(), "skipped": skipped,
    });
    let manifest_path = log_directory.join("manifest.json");
    write_json(&manifest_path, &manifest).map_err(io_error)?;
    append_event(
        event_log,
        json!({ "event": "scan_completed", "candidate_count": candidates.len() }),
    )
    .map_err(io_error)?;
    if !options.apply {
        let summary = json!({ "mode": mode, "candidate_count": candidates.len(), "candidate_bytes": candidate_bytes });
        writeln!(
            out,
            "{}\nManifest: {}",
            pretty(&summary),
            manifest_path.display()
        )
        .map_err(io_error)?;
        return Ok(());
    }
    let quarantine_directory = quarantine_base.join(name);
    let moved =
        quarantine(&candidates, &roots, &quarantine_directory, event_log).map_err(io_error)?;
    let result = json!({
        "mode": "quarantine", "status": "completed", "moved_count": moved.len(), "candidate_bytes": candidate_bytes,
        "quarantine_directory": display(&quarantine_directory), "moved": moved,
    });
    write_json(&log_directory.join("result.json"), &result).map_err(io_error)?;
    let summary = json!({
        "status": "completed", "moved_count": moved.len(), "candidate_bytes": candidate_bytes,
        "quarantine_directory": display(&quarantine_directory),
    });
    writeln!(out, "{}", pretty(&summary)).map_err(io_error)?;
    Ok(())
}

/// Runs one invocation and returns the process exit code.
pub fn run(args: &[String], out: &mut dyn Write, err: &mut dyn Write) -> i32 {
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        let _ = writeln!(out, "{USAGE}");
        return 0;
    }
    let options = match parse_args(args) {
        Ok(options) => options,
        Err(error) => {
            let _ = writeln!(err, "error: {error}\n\n{USAGE}");
            return 2;
        }
    };
    let output_directory = options
        .output_dir
        .canonicalize()
        .unwrap_or_else(|_| options.output_dir.clone());
    let name = format!("cache-cleanup-{}", Local::now().format("%Y%m%d-%H%M%S-%6f"));
    let log_directory = output_directory.join("logs").join(&name);
    let event_log = log_directory.join("cleanup.jsonl");
    match execute(&options, out, &log_directory, &event_log, &name) {
        Ok(()) => 0,
        Err(error) => {
            let _ = append_event(&event_log, json!({ "event": "failed", "error": error }));
            let _ = writeln!(err, "error: {error}");
            2
        }
    }
}
