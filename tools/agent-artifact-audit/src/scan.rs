use super::*;
use std::{
    collections::{BTreeMap, BTreeSet},
    process::Command,
};
fn git(dir: &Path, args: &[&str]) -> Result<std::process::Output> {
    let mut command = Command::new("git");
    for key in [
        "GIT_DIR",
        "GIT_COMMON_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_NAMESPACE",
    ] {
        command.env_remove(key);
    }
    command.arg("--no-optional-locks");
    if args.first() == Some(&"ls-files") {
        command.arg("--literal-pathspecs");
    }
    Ok(command.arg("-C").arg(dir).args(args).output()?)
}
fn git_data(dir: &Path, args: &[&str]) -> Result<String> {
    let r = git(dir, args)?;
    if !r.status.success() {
        return Err(String::from_utf8_lossy(&r.stderr).trim().to_string().into());
    }
    Ok(String::from_utf8(r.stdout)?)
}
pub fn eligible(p: &Path, tree: &Path) -> Result<()> {
    safety::plain(p)?;
    safety::plain(&tree.join(".git"))?;
    let relative = p.strip_prefix(tree)?;
    if relative.as_os_str().is_empty()
        || relative
            .components()
            .any(|c| c.as_os_str().to_string_lossy().eq_ignore_ascii_case(".git"))
    {
        return Err("Protected root".into());
    }
    let relative = relative.to_str().ok_or("Unsupported path")?;
    let root = git_data(tree, &["rev-parse", "--show-toplevel"])?;
    if fs::canonicalize(root.trim_end())? != fs::canonicalize(tree)? {
        return Err("Worktree changed".into());
    }
    if !git_data(tree, &["ls-files", "--cached", "-z", "--", relative])?.is_empty() {
        return Err("Git tracked".into());
    }
    if !git(tree, &["check-ignore", "-q", "--", relative])?
        .status
        .success()
    {
        return Err("Not explicitly Git ignored".into());
    }
    let parent = p.parent().ok_or("Missing parent")?;
    if p.is_dir() {
        if p.file_name().is_none_or(|n| n != "__pycache__") {
            return Err("Unknown directory".into());
        }
    } else {
        let name = p
            .file_name()
            .and_then(|n| n.to_str())
            .ok_or("Unknown name")?;
        let (stem, version) = name.split_once(".cpython-").ok_or("Unknown cache file")?;
        if parent.file_name().is_none_or(|n| n != "__pycache__")
            || !version
                .strip_suffix(".pyc")
                .is_some_and(|s| !s.is_empty() && s.chars().all(|c| c.is_ascii_digit()))
        {
            return Err("Unknown cache format".into());
        }
        let source = parent.with_file_name(format!("{stem}.py"));
        safety::plain(&source)?;
        if !source.is_file() {
            return Err("Missing source".into());
        }
    }
    Ok(())
}
fn classify(name: &str) -> Option<(&'static str, &'static str)> {
    if name == "__pycache__" {
        Some(("python-cache", "快取"))
    } else if name.to_ascii_lowercase().contains("backup") || name.ends_with(".bak") {
        Some(("backup-name", "備份"))
    } else if matches!(name, "build" | "dist" | "target") {
        Some(("build-name", "建置"))
    } else if matches!(name, "tmp" | "temp" | ".tmp") {
        Some(("temporary-name", "暫存"))
    } else {
        None
    }
}

fn backup_stamp(name: &str) -> bool {
    name.len() == 22
        && name.bytes().enumerate().all(|(i, b)| match i {
            8 => b == b'T',
            21 => b == b'Z',
            _ => b.is_ascii_digit(),
        })
}

pub fn backup_home(path: &Path) -> Option<&Path> {
    let name = path.file_name()?.to_str()?;
    if !matches!(
        name,
        "AGENTS.md" | "AGENTS.zh-TW.md" | "CLAUDE.md" | "CLAUDE.zh-TW.md"
    ) {
        return None;
    }
    let batch = path.parent()?;
    if !backup_stamp(batch.file_name()?.to_str()?) {
        return None;
    }
    let owner = batch.parent()?;
    let backups = owner.parent()?;
    if owner.file_name()? != "codex-setup" || backups.file_name()? != "backups" {
        return None;
    }
    backups.parent()
}

pub fn backup_eligible(path: &Path) -> Result<()> {
    safety::plain(path)?;
    let home = backup_home(path).ok_or("Unknown installer backup layout")?;
    for ancestor in path.ancestors().skip(1) {
        if ancestor.join(".git").try_exists()? {
            return Err("Backup inside a Git repository".into());
        }
    }
    let name = path.file_name().ok_or("Missing backup filename")?;
    let current = home.join(name);
    safety::plain(&current)?;
    if !current.is_file() || !path.is_file() {
        return Err("Missing active file or backup".into());
    }
    let batch = path.parent().unwrap();
    for entry in fs::read_dir(batch.parent().unwrap())? {
        let entry = entry?;
        let newer = entry.path().join(name);
        if entry.file_name().as_os_str() > batch.file_name().unwrap()
            && entry.file_name().to_str().is_some_and(backup_stamp)
            && safety::plain(&newer).is_ok()
            && newer.is_file()
        {
            return Ok(());
        }
    }
    Err("保留最新備份, 找不到同檔名的較新備份".into())
}
struct Scan {
    sizes: BTreeMap<String, u64>,
    trees: BTreeMap<PathBuf, String>,
    pending: BTreeSet<PathBuf>,
    homes: Vec<PathBuf>,
    excluded: Vec<PathBuf>,
    items: BTreeMap<PathBuf, Value>,
    gaps: Vec<String>,
}
impl Scan {
    fn visit(&mut self, p: &Path, owner: &Path, project: &str) -> Result<u64> {
        if self.excluded.iter().any(|e| p.starts_with(e)) {
            return Ok(0);
        }
        safety::plain(p)?;
        if !p.is_dir() {
            return Err("Expected directory".into());
        }
        let identity = safety::snapshot(p)?;
        let key = required(&identity, "identity")?.to_owned();
        if let Some(size) = self.sizes.get(&key) {
            return Ok(*size);
        }
        self.sizes.insert(key.clone(), 0);
        let mut total = 0;
        let mut tree = owner.to_owned();
        let mut repo = project.to_owned();
        if p.join(".git").try_exists()? {
            safety::plain(&p.join(".git"))?;
            tree = p.to_owned();
            repo = p.display().to_string();
            match git_data(p, &["worktree", "list", "--porcelain", "-z"]) {
                Ok(data) => {
                    for s in data.split('\0').filter_map(|v| v.strip_prefix("worktree ")) {
                        self.pending.insert(PathBuf::from(s));
                    }
                    if let Some(first) = data
                        .split('\0')
                        .next()
                        .and_then(|s| s.strip_prefix("worktree "))
                    {
                        repo = first.to_owned()
                    }
                }
                Err(e) => self.gaps.push(format!("{}: {e}", p.display())),
            }
            self.trees.insert(tree.clone(), repo.clone());
        }
        for entry in fs::read_dir(p)? {
            let entry = match entry {
                Ok(v) => v,
                Err(e) => {
                    self.gaps.push(format!("{}: {e}", p.display()));
                    continue;
                }
            };
            let child = entry.path();
            let Some(name) = child.file_name().and_then(|s| s.to_str()) else {
                self.gaps
                    .push(format!("{}: non-UTF-8 filename", p.display()));
                continue;
            };
            if name.eq_ignore_ascii_case(".git")
                || self.excluded.iter().any(|e| child.starts_with(e))
            {
                continue;
            }
            let result = (|| -> Result<()> {
                let meta = fs::symlink_metadata(&child)?;
                if safety::link(&meta) {
                    return Ok(());
                }
                let size = if meta.is_dir() {
                    self.visit(&child, &tree, &repo)?
                } else if meta.is_file() {
                    meta.len()
                } else {
                    return Ok(());
                };
                total += size;
                let owned_backup =
                    backup_home(&child).is_some_and(|h| self.homes.iter().any(|root| root == h));
                if owned_backup {
                    self.item(&child, &tree, &repo, "setup-rotation", "備份", size)?
                } else if let Some((rule, kind)) = classify(name) {
                    self.item(&child, &tree, &repo, rule, kind, size)?
                }
                Ok(())
            })();
            if let Err(e) = result {
                self.gaps.push(format!("{}: {e}", child.display()))
            }
        }
        self.sizes.insert(key, total);
        Ok(total)
    }
    fn item(
        &mut self,
        p: &Path,
        tree: &Path,
        project: &str,
        rule: &str,
        kind: &str,
        size: u64,
    ) -> Result<()> {
        let protected = self.homes.iter().any(|h| p.starts_with(h)) || p.join(".git").exists();
        let mut members = vec![];
        let mut reason = "名稱只供辨識, 用途待確認".to_owned();
        let mut selectable = false;
        if rule == "python-cache" && !protected && p.is_dir() && self.trees.contains_key(tree) {
            let checked = (|| -> Result<()> {
                eligible(p, tree)?;
                for entry in fs::read_dir(p)? {
                    let f = entry?.path();
                    eligible(&f, tree)?;
                    if !f.is_file() {
                        return Err("Unexpected cache member".into());
                    }
                    members.push(json!({"path":f,"stamp":safety::snapshot(&f)?}))
                }
                members.sort_by_key(|v| v["path"].as_str().unwrap_or("").to_owned());
                Ok(())
            })();
            match checked {
                Ok(()) => {
                    selectable = true;
                    reason = "Git 已忽略的 Python 位元組碼快取, 對應原始碼仍存在".into()
                }
                Err(e) => reason = e.to_string(),
            }
        }
        let mut protected = protected;
        if rule == "setup-rotation" {
            match backup_eligible(p) {
                Ok(()) => {
                    protected = false;
                    selectable = true;
                    reason = "Setup 安裝備份, 現行檔案與較新同名備份均存在".into()
                }
                Err(e) => {
                    reason = e.to_string();
                }
            }
        } else if protected {
            reason = "工具資料目錄或工作樹根目錄受保護".into()
        }
        let stamp = safety::snapshot(p)?;
        self.items.insert(p.into(),json!({"path":p,"relative":p.strip_prefix(tree).unwrap_or(p),"tree":tree,"project":project,"kind":kind,"rule":rule,"rule_version":1,"status":if protected{"受保護"}else if selectable{"可選取"}else{"待確認"},"reason":reason,"selectable":selectable,"size":size,"stamp":stamp,"members":members}));
        Ok(())
    }
}
fn local_home(a: &Value, key: &str, var: &str, default: &str) -> Result<PathBuf> {
    let p = a[key]
        .as_str()
        .map(PathBuf::from)
        .or_else(|| env::var_os(var).map(PathBuf::from))
        .unwrap_or(home()?.join(default));
    Ok(std::path::absolute(p)?)
}
pub fn run(a: &Value) -> Result<Value> {
    let requested = list(a, "workspace")?;
    if requested.is_empty() {
        return Err("Select a workspace".into());
    }
    let homes = vec![
        local_home(a, "codex_home", "CODEX_HOME", ".codex")?,
        local_home(a, "claude_home", "CLAUDE_CONFIG_DIR", ".claude")?,
    ];
    let id = batch();
    let out = run_dir(required(a, "out")?, &id)?;
    let local = state()?;
    let mut scan = Scan {
        sizes: BTreeMap::new(),
        trees: BTreeMap::new(),
        pending: BTreeSet::new(),
        homes: homes.clone(),
        excluded: vec![out.parent().unwrap().into(), local.clone()],
        items: BTreeMap::new(),
        gaps: vec![],
    };
    for v in requested {
        scan.pending
            .insert(std::path::absolute(v.as_str().ok_or("Invalid workspace")?)?);
    }
    scan.pending.extend(homes);
    let mut roots = BTreeSet::new();
    while let Some(root) = scan.pending.pop_first() {
        if !roots.insert(root.clone()) {
            continue;
        }
        if root.parent().is_none() || scan.excluded.iter().any(|p| root.starts_with(p)) {
            scan.gaps.push(format!("Excluded root: {}", root.display()));
            continue;
        }
        if let Err(e) = scan.visit(&root, &root, &root.display().to_string()) {
            scan.gaps.push(format!("{}: {e}", root.display()))
        }
    }
    let mut rows = vec![];
    for (i, (path, mut row)) in scan.items.into_iter().enumerate() {
        if roots.contains(&path) {
            row["selectable"] = json!(false);
            row["status"] = json!("受保護");
            row["reason"] = json!("掃描根目錄受保護");
        }
        row["id"] = json!(format!("A-{}", i + 1));
        rows.push(row)
    }
    let report = json!({"version":VERSION,"mode":"scan","batch":id,"roots":roots,"trees":scan.trees,"gaps":scan.gaps,"items":rows});
    write_new(
        &local.join(format!("{id}.json")),
        &serde_json::to_vec(&report)?,
    )?;
    reports::save(&out, "scan", &report)?;
    Ok(
        json!({"batch":id,"partial":!scan.gaps.is_empty(),"gaps":scan.gaps,"count":rows.len(),"run":out,"html":out.join("scan.html"),"json":out.join("scan.json")}),
    )
}
