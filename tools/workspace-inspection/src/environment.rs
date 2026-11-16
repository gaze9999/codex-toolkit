//! Compare two directory trees by relative path, size and SHA-256. Never writes to either side.
use regex::Regex;
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs;
use std::io::Read;
use std::path::Path;

pub const DEFAULT_EXCLUDES: [&str; 18] = [
    ".git/**",
    ".hg/**",
    ".svn/**",
    ".venv/**",
    "**/__pycache__/**",
    "**/*.pyc",
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "*.key",
    "*.pem",
    "**/*.key",
    "**/*.pem",
    "credentials*",
    "secrets*",
    "**/credentials*",
    "**/secrets*",
];

/// Shell-style pattern as a regular expression: `*` spans any characters including `/`, `?` is
/// one character and `[...]` a character set with `!` for negation.
fn translate(pattern: &str) -> String {
    let chars: Vec<char> = pattern.chars().collect();
    let mut out = String::from(r"(?s)\A(?:");
    let mut i = 0;
    while i < chars.len() {
        let ch = chars[i];
        i += 1;
        match ch {
            '*' => out.push_str(".*"),
            '?' => out.push('.'),
            '[' => {
                let mut j = i;
                if j < chars.len() && chars[j] == '!' {
                    j += 1;
                }
                if j < chars.len() && chars[j] == ']' {
                    j += 1;
                }
                while j < chars.len() && chars[j] != ']' {
                    j += 1;
                }
                if j >= chars.len() {
                    out.push_str(r"\[");
                    continue;
                }
                let mut set = String::new();
                for (index, item) in chars[i..j].iter().enumerate() {
                    match (index, item) {
                        (0, '!') => set.push('^'),
                        (0, '^') => set.push_str(r"\^"),
                        (_, '\\' | '[' | '&' | '~') => {
                            set.push('\\');
                            set.push(*item);
                        }
                        _ => set.push(*item),
                    }
                }
                out.push('[');
                out.push_str(&set);
                out.push(']');
                i = j + 1;
            }
            other => out.push_str(&regex::escape(&other.to_string())),
        }
    }
    out.push_str(r")\z");
    out
}

/// Compiled patterns; a path matches when the whole path or its last segment matches any of them.
pub struct Patterns(Vec<Result<Regex, String>>);
impl Patterns {
    pub fn new<S: AsRef<str>>(patterns: &[S]) -> Self {
        Self(
            patterns
                .iter()
                .map(|pattern| {
                    Regex::new(&translate(pattern.as_ref()))
                        .map_err(|_| pattern.as_ref().to_owned())
                })
                .collect(),
        )
    }
    fn is_empty(&self) -> bool {
        self.0.is_empty()
    }
    fn matches(&self, path: &str) -> bool {
        let name = path.rsplit('/').next().unwrap_or("");
        self.0.iter().any(|pattern| match pattern {
            Ok(regex) => regex.is_match(path) || regex.is_match(name),
            // A set the engine rejects is compared as plain text
            Err(literal) => literal == path || literal == name,
        })
    }
}

fn digest(path: &Path) -> std::io::Result<String> {
    let mut file = fs::File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = vec![0u8; 1024 * 1024];
    loop {
        let read = file.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }
    Ok(hasher
        .finalize()
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect())
}

struct Manifest {
    files: BTreeMap<String, Value>,
    excluded: u64,
    errors: Vec<Value>,
}

fn manifest(
    root: &Path,
    includes: &Patterns,
    excludes: &Patterns,
    max_files: usize,
) -> Result<Manifest, String> {
    let mut result = Manifest {
        files: BTreeMap::new(),
        excluded: 0,
        errors: Vec::new(),
    };
    let mut pending = vec![(root.to_path_buf(), String::new())];
    while let Some((dir, prefix)) = pending.pop() {
        let entries = match fs::read_dir(&dir) {
            Ok(entries) => entries,
            Err(error) => {
                result
                    .errors
                    .push(json!({"path":dir.to_string_lossy(),"error":error.to_string()}));
                continue;
            }
        };
        let mut entries: Vec<_> = entries.flatten().collect();
        entries.sort_by_key(|entry| entry.file_name().to_string_lossy().to_lowercase());
        let mut folders = Vec::new();
        for entry in entries {
            let name = entry.file_name().to_string_lossy().into_owned();
            let relative = format!("{prefix}{name}");
            let kind = entry.file_type();
            // Links are never followed or hashed
            if kind.as_ref().is_ok_and(|kind| kind.is_symlink()) {
                result.excluded += 1;
            } else if kind.as_ref().is_ok_and(|kind| kind.is_dir()) {
                if excludes.matches(&format!("{relative}/")) {
                    result.excluded += 1;
                } else {
                    folders.push((entry.path(), format!("{relative}/")));
                }
            } else if excludes.matches(&relative)
                || (!includes.is_empty() && !includes.matches(&relative))
            {
                result.excluded += 1;
            } else {
                if result.files.len() >= max_files {
                    return Err(format!("File limit exceeded: {max_files}"));
                }
                let path = entry.path();
                match fs::metadata(&path).and_then(|meta| Ok((meta.len(), digest(&path)?))) {
                    Ok((size, sha256)) => {
                        result
                            .files
                            .insert(relative, json!({"size":size,"sha256":sha256}));
                    }
                    Err(error) => result
                        .errors
                        .push(json!({"path":path.to_string_lossy(),"error":error.to_string()})),
                }
            }
        }
        pending.extend(folders.into_iter().rev());
    }
    Ok(result)
}

/// Compares `source` and `target`. `excludes` is the complete exclusion list; callers add
/// `DEFAULT_EXCLUDES` when they want the defaults.
pub fn compare_trees<S: AsRef<str>>(
    source: &Path,
    target: &Path,
    includes: &[S],
    excludes: &[S],
    max_files: i64,
) -> Result<Value, String> {
    let resolve =
        |path: &Path| fs::canonicalize(path).map_err(|e| format!("{}: {e}", path.display()));
    let (source, target) = (resolve(source)?, resolve(target)?);
    if !source.is_dir() || !target.is_dir() {
        return Err("source and target must be existing directories".into());
    }
    if source.starts_with(&target) || target.starts_with(&source) {
        return Err("source and target must be separate, non-nested directories".into());
    }
    if !(1..=200_000).contains(&max_files) {
        return Err("max_files must be between 1 and 200000".into());
    }
    let (includes, excludes) = (Patterns::new(includes), Patterns::new(excludes));
    let left = manifest(&source, &includes, &excludes, max_files as usize)?;
    let right = manifest(&target, &includes, &excludes, max_files as usize)?;
    let missing: Vec<&String> = left
        .files
        .keys()
        .filter(|path| !right.files.contains_key(*path))
        .collect();
    let extra: Vec<&String> = right
        .files
        .keys()
        .filter(|path| !left.files.contains_key(*path))
        .collect();
    let changed: Vec<Value> = left
        .files
        .iter()
        .filter_map(|(path, entry)| {
            let other = right.files.get(path)?;
            (entry != other).then(|| json!({"path":path,"source":entry,"target":other}))
        })
        .collect();
    let matched = missing.is_empty()
        && extra.is_empty()
        && changed.is_empty()
        && left.errors.is_empty()
        && right.errors.is_empty();
    let mut result = Map::new();
    result.insert("source".into(), json!(source.to_string_lossy()));
    result.insert("target".into(), json!(target.to_string_lossy()));
    result.insert(
        "status".into(),
        json!(if matched { "match" } else { "different" }),
    );
    result.insert("source_files".into(), json!(left.files.len()));
    result.insert("target_files".into(), json!(right.files.len()));
    result.insert("missing_in_target".into(), json!(missing));
    result.insert("extra_in_target".into(), json!(extra));
    result.insert("changed".into(), json!(changed));
    result.insert(
        "excluded".into(),
        json!({"source":left.excluded,"target":right.excluded}),
    );
    result.insert(
        "errors".into(),
        json!({"source":left.errors,"target":right.errors}),
    );
    Ok(Value::Object(result))
}
