//! Read-only file and Git helpers shared by the checks.
use std::collections::BTreeSet;
use std::fs;
use std::path::{Component, Path, PathBuf};
use std::process::Command;

/// Canonical form of an existing root.
pub fn root(path: &Path) -> Result<PathBuf, String> {
    fs::canonicalize(path).map_err(|e| format!("{}: {e}", path.display()))
}

/// Resolves `.` and `..` without touching the file system, for paths that may not exist.
pub fn normalize(path: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for part in path.components() {
        match part {
            Component::CurDir => {}
            Component::ParentDir => {
                out.pop();
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}

pub fn posix(path: &Path) -> String {
    path.to_string_lossy().replace('\\', "/")
}

/// Path below `root` with forward slashes; the full path when it lies elsewhere.
pub fn relative(path: &Path, root: &Path) -> String {
    posix(path.strip_prefix(root).unwrap_or(path))
}

/// Files below `root` in name order. Folders whose lowercase name is in `skip` and linked folders
/// are left out.
pub fn walk(root: &Path, skip: &[&str]) -> Vec<PathBuf> {
    let mut files = Vec::new();
    let mut pending = vec![root.to_path_buf()];
    while let Some(dir) = pending.pop() {
        let Ok(entries) = fs::read_dir(&dir) else {
            continue;
        };
        let mut entries: Vec<_> = entries.flatten().collect();
        entries.sort_by_key(|entry| entry.file_name());
        let mut folders = Vec::new();
        for entry in entries {
            let Ok(kind) = entry.file_type() else {
                continue;
            };
            let path = entry.path();
            if kind.is_dir() {
                let name = entry.file_name().to_string_lossy().to_lowercase();
                if !skip.contains(&name.as_str()) {
                    folders.push(path);
                }
            } else if !kind.is_symlink() || path.is_file() {
                files.push(path);
            }
        }
        // Reverse so the stack pops folders in name order
        pending.extend(folders.into_iter().rev());
    }
    files
}

/// Staged, unstaged and untracked paths. With `relative`, diff paths are relative to `root`
/// rather than the repository top level.
pub fn git_changed(root: &Path, relative: bool) -> Result<BTreeSet<String>, String> {
    let mut names = BTreeSet::new();
    for base in [
        vec!["diff", "--name-only"],
        vec!["diff", "--cached", "--name-only"],
        vec!["ls-files", "--others", "--exclude-standard"],
    ] {
        let mut command = Command::new("git");
        command.arg("-C").arg(root).args(&base);
        if relative && base[0] == "diff" {
            command.arg("--relative");
        }
        let output = command
            .arg("-z")
            .output()
            .map_err(|e| format!("Unable to read Git changes: {e}"))?;
        if !output.status.success() {
            return Err(format!(
                "Unable to read Git changes: git {} exited with {}",
                base.join(" "),
                output.status
            ));
        }
        names.extend(
            output
                .stdout
                .split(|byte| *byte == 0)
                .filter(|raw| !raw.is_empty())
                .map(|raw| String::from_utf8_lossy(raw).replace('\\', "/")),
        );
    }
    Ok(names)
}

/// Lowercase extension with its dot, or an empty string.
pub fn suffix(path: &Path) -> String {
    path.extension()
        .map(|ext| format!(".{}", ext.to_string_lossy().to_lowercase()))
        .unwrap_or_default()
}

pub fn read_lossy(path: &Path) -> std::io::Result<String> {
    Ok(String::from_utf8_lossy(&fs::read(path)?).into_owned())
}
