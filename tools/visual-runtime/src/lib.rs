//! Explicit project roots, immutable preview manifests and process-owned loopback preview jobs.

pub mod mcp;

use base64::Engine;
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Component, Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::JoinHandle;
use std::time::Duration;

pub const VERSION: &str = env!("CARGO_PKG_VERSION");
const ALLOWED: [&str; 14] = [
    ".html", ".css", ".js", ".mjs", ".json", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".woff2",
    ".gltf", ".glb", ".bin",
];
const MAX_FILE: usize = 32 * 1024 * 1024;
const MAX_MANIFEST: usize = 64 * 1024 * 1024;
const MAX_JOBS: usize = 8;

/// Machine-readable error code.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Problem(pub &'static str);

type Checked<T = ()> = Result<T, Problem>;

fn suffix(name: &str) -> String {
    let base = name.rsplit('/').next().unwrap_or(name);
    match base.rfind('.') {
        Some(0) | None => String::new(),
        Some(index) if index + 1 == base.len() => String::new(),
        Some(index) => base[index..].to_lowercase(),
    }
}

/// Components of a relative path as Python `PurePath.parts` reports them.
fn parts(relative: &str) -> Vec<String> {
    Path::new(relative)
        .components()
        .filter(|part| !matches!(part, Component::CurDir))
        .map(|part| part.as_os_str().to_string_lossy().into_owned())
        .collect()
}

pub struct Workspace {
    pub root: PathBuf,
}

impl Workspace {
    pub fn new(root: &str) -> Checked<Self> {
        if root.trim().is_empty() {
            return Err(Problem("invalid_root"));
        }
        let root = std::fs::canonicalize(root).map_err(|_| Problem("invalid_root"))?;
        if !root.is_dir() {
            return Err(Problem("invalid_root"));
        }
        Ok(Self { root })
    }

    /// Existing regular file inside the root, reached without links.
    pub fn file(&self, relative: &str) -> Checked<PathBuf> {
        if relative.is_empty() || relative.contains('\\') || relative.contains(':') {
            return Err(Problem("invalid_relative_path"));
        }
        let candidate = Path::new(relative);
        if candidate.is_absolute()
            || candidate
                .components()
                .any(|part| matches!(part, Component::ParentDir))
        {
            return Err(Problem("invalid_relative_path"));
        }
        let path = self.root.join(relative);
        let mut item = path.as_path();
        while item != self.root {
            if item
                .symlink_metadata()
                .is_ok_and(|meta| meta.file_type().is_symlink() || is_junction(&meta))
            {
                return Err(Problem("linked_path"));
            }
            match item.parent() {
                Some(parent) => item = parent,
                None => break,
            }
        }
        let resolved = std::fs::canonicalize(&path).map_err(|_| Problem("invalid_file"))?;
        if !resolved.starts_with(&self.root) || !resolved.is_file() {
            return Err(Problem("invalid_file"));
        }
        Ok(resolved)
    }

    pub fn read(&self, relative: &str, limit: usize) -> Checked<Vec<u8>> {
        let path = self.file(relative)?;
        let mut raw = Vec::new();
        std::fs::File::open(&path)
            .and_then(|file| file.take(limit as u64 + 1).read_to_end(&mut raw))
            .map_err(|_| Problem("invalid_file"))?;
        if raw.len() > limit {
            return Err(Problem("file_too_large"));
        }
        Ok(raw)
    }

    /// Framework and version declarations only; scripts are listed by name and never run.
    pub fn inspect(&self) -> Checked<Value> {
        let mut frameworks: Vec<Value> = Vec::new();
        let mut dependencies = Map::new();
        let mut versions = Map::new();
        let mut scripts: Vec<String> = Vec::new();
        if self.root.join("package.json").exists() {
            let raw = self.read("package.json", 262_144)?;
            let body = raw.strip_prefix(b"\xEF\xBB\xBF").unwrap_or(&raw);
            let data: Value =
                serde_json::from_slice(body).map_err(|_| Problem("invalid_package"))?;
            let data = data.as_object().ok_or(Problem("invalid_package"))?;
            let section = |name: &str| -> Checked<Map<String, Value>> {
                match data.get(name) {
                    None => Ok(Map::new()),
                    Some(Value::Object(map)) => Ok(map.clone()),
                    Some(_) => Err(Problem("invalid_package")),
                }
            };
            let mut declared = section("dependencies")?;
            declared.extend(section("devDependencies")?);
            let candidates = [
                ("@angular/core", "angular"),
                ("vue", "vue"),
                ("nuxt", "nuxt"),
                ("react", "react"),
                ("three", "three"),
                ("echarts", "echarts"),
                ("remotion", "remotion"),
                ("@react-three/fiber", "react-three-fiber"),
            ];
            for (name, framework) in candidates {
                if let Some(version) = declared.get(name) {
                    dependencies.insert(name.into(), version.clone());
                    frameworks.push(framework.into());
                }
            }
            scripts = section("scripts")?.keys().cloned().collect();
            scripts.sort();
        }
        let unity = "ProjectSettings/ProjectVersion.txt";
        if self.root.join(unity).exists() {
            frameworks.push("unity".into());
            let raw = self.read(unity, 4096)?;
            let text = String::from_utf8(raw).map_err(|_| Problem("invalid_file"))?;
            versions.insert("unity".into(), text.trim().into());
        }
        Ok(
            json!({"status": "ok", "root": self.root.to_string_lossy(), "frameworks": frameworks,
            "dependencies": dependencies, "versions": versions, "scripts": scripts,
            "available_operations": ["inspect", "artifacts", "preview_start", "preview_status", "preview_stop"]}),
        )
    }

    pub fn artifacts(&self, paths: &[String]) -> Checked<Value> {
        if !(1..=128).contains(&paths.len()) {
            return Err(Problem("invalid_paths"));
        }
        let mut rows = Vec::new();
        for relative in paths {
            let raw = self.read(relative, MAX_FILE)?;
            rows.push(json!({"path": relative, "bytes": raw.len(), "sha256": format!("{:x}", Sha256::digest(&raw))}));
        }
        Ok(json!({"status": "ok", "artifacts": rows}))
    }
}

#[cfg(windows)]
fn is_junction(meta: &std::fs::Metadata) -> bool {
    use std::os::windows::fs::MetadataExt;
    // FILE_ATTRIBUTE_REPARSE_POINT covers junctions and other links
    meta.file_attributes() & 0x400 != 0
}

#[cfg(not(windows))]
fn is_junction(_: &std::fs::Metadata) -> bool {
    false
}

fn random(bytes: usize) -> Checked<Vec<u8>> {
    let mut buffer = vec![0; bytes];
    getrandom::fill(&mut buffer).map_err(|_| Problem("random_unavailable"))?;
    Ok(buffer)
}

fn mime(name: &str) -> &'static str {
    match suffix(name).as_str() {
        ".js" | ".mjs" => "text/javascript",
        ".html" => "text/html",
        ".css" => "text/css",
        ".json" => "application/json",
        ".svg" => "image/svg+xml",
        ".png" => "image/png",
        ".jpg" | ".jpeg" => "image/jpeg",
        ".webp" => "image/webp",
        ".woff2" => "font/woff2",
        ".gltf" => "model/gltf+json",
        ".glb" => "model/gltf-binary",
        _ => "application/octet-stream",
    }
}

fn unquote(text: &str) -> String {
    let bytes = text.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] == b'%' && index + 2 < bytes.len() {
            if let Some(value) = std::str::from_utf8(&bytes[index + 1..index + 3])
                .ok()
                .and_then(|hex| u8::from_str_radix(hex, 16).ok())
            {
                out.push(value);
                index += 3;
                continue;
            }
        }
        out.push(bytes[index]);
        index += 1;
    }
    String::from_utf8_lossy(&out).into_owned()
}

struct Job {
    port: u16,
    entry: String,
    files: Vec<String>,
    prefix: String,
    running: Arc<AtomicBool>,
    stop: Arc<AtomicBool>,
    thread: Option<JoinHandle<()>>,
}

fn respond(
    stream: &mut TcpStream,
    code: u16,
    reason: &str,
    headers: &[(&str, String)],
    body: &[u8],
    head: bool,
) {
    let mut out = format!("HTTP/1.0 {code} {reason}\r\n");
    for (name, value) in headers {
        out.push_str(&format!("{name}: {value}\r\n"));
    }
    out.push_str("Connection: close\r\n\r\n");
    let _ = stream.write_all(out.as_bytes());
    if !head {
        let _ = stream.write_all(body);
    }
    let _ = stream.flush();
}

fn error_page(stream: &mut TcpStream, code: u16, reason: &str, head: bool) {
    let body = format!("<!DOCTYPE html><title>Error {code}</title><p>{reason}</p>\n");
    let headers = [
        ("Content-Type", "text/html;charset=utf-8".to_string()),
        ("Content-Length", body.len().to_string()),
    ];
    respond(stream, code, reason, &headers, body.as_bytes(), head);
}

fn serve_connection(
    mut stream: TcpStream,
    port: u16,
    prefix: &str,
    assets: &HashMap<String, Vec<u8>>,
) {
    let _ = stream.set_read_timeout(Some(Duration::from_secs(5)));
    let mut request = Vec::new();
    let mut chunk = [0u8; 4096];
    while !request.windows(4).any(|w| w == b"\r\n\r\n") && request.len() < 65_536 {
        match stream.read(&mut chunk) {
            Ok(0) | Err(_) => break,
            Ok(read) => request.extend_from_slice(&chunk[..read]),
        }
    }
    let text = String::from_utf8_lossy(&request);
    let mut lines = text.split("\r\n");
    let mut first = lines.next().unwrap_or("").split(' ');
    let (method, target) = (first.next().unwrap_or(""), first.next().unwrap_or(""));
    let head = method == "HEAD";
    if method != "GET" && !head {
        error_page(&mut stream, 501, "Unsupported method", false);
        return;
    }
    let host = lines
        .take_while(|line| !line.is_empty())
        .filter_map(|line| line.split_once(':'))
        .find(|(name, _)| name.trim().eq_ignore_ascii_case("host"))
        .map(|(_, value)| value.trim().to_string());
    if host.as_deref() != Some(format!("127.0.0.1:{port}").as_str()) {
        error_page(&mut stream, 403, "Forbidden", head);
        return;
    }
    let path = unquote(target.split(['?', '#']).next().unwrap_or(""));
    let Some(body) = path
        .strip_prefix(prefix)
        .and_then(|name| assets.get(name).map(|body| (name, body)))
    else {
        error_page(&mut stream, 404, "File not found", head);
        return;
    };
    let (name, body) = body;
    let headers = [
        ("Content-Type", mime(name).to_string()),
        ("Content-Length", body.len().to_string()),
        ("Cache-Control", "no-store".to_string()),
        ("X-Content-Type-Options", "nosniff".to_string()),
        ("Referrer-Policy", "no-referrer".to_string()),
    ];
    respond(&mut stream, 200, "OK", &headers, body, head);
}

/// Jobs live in this process only; closing the owner closes its listeners.
#[derive(Default)]
pub struct Previews {
    jobs: Mutex<HashMap<String, Job>>,
}

impl Previews {
    pub fn start(&self, workspace: &Workspace, entry: &str, files: &[String]) -> Checked<Value> {
        let mut unique = files.to_vec();
        unique.sort();
        unique.dedup();
        if !(1..=128).contains(&files.len())
            || !files.iter().any(|file| file == entry)
            || unique.len() != files.len()
        {
            return Err(Problem("invalid_manifest"));
        }
        // Snapshot only explicitly selected files; never serve project directories.
        let mut assets = HashMap::new();
        let mut total = 0;
        for name in files {
            let hidden = parts(name)
                .iter()
                .any(|part| part.starts_with('.') || part == "node_modules" || part == ".git");
            if hidden || !ALLOWED.contains(&suffix(name).as_str()) {
                return Err(Problem("unsupported_asset"));
            }
            let raw = workspace.read(name, MAX_FILE)?;
            total += raw.len();
            if total > MAX_MANIFEST {
                return Err(Problem("manifest_too_large"));
            }
            assets.insert(name.clone(), raw);
        }
        if suffix(entry) != ".html" {
            return Err(Problem("invalid_entry"));
        }
        let mut jobs = self.jobs.lock().map_err(|_| Problem("job_state"))?;
        if jobs.len() >= MAX_JOBS {
            return Err(Problem("job_limit"));
        }
        let token = base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(random(24)?);
        let prefix = format!("/{token}/");
        let id: String = random(12)?.iter().map(|b| format!("{b:02x}")).collect();
        let listener = TcpListener::bind(("127.0.0.1", 0)).map_err(|_| Problem("listen_failed"))?;
        let port = listener
            .local_addr()
            .map_err(|_| Problem("listen_failed"))?
            .port();
        listener
            .set_nonblocking(true)
            .map_err(|_| Problem("listen_failed"))?;
        let running = Arc::new(AtomicBool::new(true));
        let stop = Arc::new(AtomicBool::new(false));
        let assets = Arc::new(assets);
        let thread = {
            let (running, stop, prefix, assets) = (
                running.clone(),
                stop.clone(),
                prefix.clone(),
                assets.clone(),
            );
            std::thread::spawn(move || {
                while !stop.load(Ordering::SeqCst) {
                    match listener.accept() {
                        Ok((stream, _)) => {
                            let _ = stream.set_nonblocking(false);
                            let (prefix, assets) = (prefix.clone(), assets.clone());
                            std::thread::spawn(move || {
                                serve_connection(stream, port, &prefix, &assets)
                            });
                        }
                        Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                            std::thread::sleep(Duration::from_millis(50));
                        }
                        Err(_) => break,
                    }
                }
                running.store(false, Ordering::SeqCst);
            })
        };
        jobs.insert(
            id.clone(),
            Job {
                port,
                entry: entry.to_string(),
                files: files.to_vec(),
                prefix,
                running,
                stop,
                thread: Some(thread),
            },
        );
        drop(jobs);
        Ok(self.status(&id))
    }

    pub fn status(&self, id: &str) -> Value {
        let jobs = match self.jobs.lock() {
            Ok(jobs) => jobs,
            Err(poisoned) => poisoned.into_inner(),
        };
        match jobs.get(id) {
            None => json!({"status": "unknown_job", "job_id": id}),
            Some(job) => {
                json!({"status": if job.running.load(Ordering::SeqCst) { "ready" } else { "stopped" },
                "job_id": id, "url": format!("http://127.0.0.1:{}{}{}", job.port, job.prefix, job.entry),
                "files": job.files, "snapshot": true, "owner": "current_process"})
            }
        }
    }

    pub fn stop(&self, id: &str) -> Value {
        let owned = match self.jobs.lock() {
            Ok(mut jobs) => jobs.remove(id),
            Err(poisoned) => poisoned.into_inner().remove(id),
        };
        let Some(mut job) = owned else {
            return json!({"status": "unknown_job", "job_id": id});
        };
        job.stop.store(true, Ordering::SeqCst);
        if let Some(thread) = job.thread.take() {
            let _ = thread.join();
        }
        json!({"status": "stopped", "job_id": id})
    }

    pub fn close(&self) {
        let ids: Vec<String> = match self.jobs.lock() {
            Ok(jobs) => jobs.keys().cloned().collect(),
            Err(poisoned) => poisoned.into_inner().keys().cloned().collect(),
        };
        for id in ids {
            self.stop(&id);
        }
    }
}

impl Drop for Previews {
    fn drop(&mut self) {
        self.close();
    }
}

/// JSON with `", "` and `": "` separators, like Python `json.dumps`.
pub fn compact(value: &Value) -> String {
    match value {
        Value::Array(items) => format!(
            "[{}]",
            items.iter().map(compact).collect::<Vec<_>>().join(", ")
        ),
        Value::Object(fields) => format!(
            "{{{}}}",
            fields
                .iter()
                .map(|(key, item)| format!("{}: {}", Value::from(key.as_str()), compact(item)))
                .collect::<Vec<_>>()
                .join(", ")
        ),
        other => other.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn get(url: &str, host: Option<&str>) -> (u16, Vec<u8>) {
        let rest = url.strip_prefix("http://").unwrap();
        let (address, path) = rest.split_once('/').unwrap();
        let mut stream = TcpStream::connect(address).unwrap();
        let host = host.unwrap_or(address);
        write!(stream, "GET /{path} HTTP/1.1\r\nHost: {host}\r\n\r\n").unwrap();
        let mut raw = Vec::new();
        stream.read_to_end(&mut raw).unwrap();
        let split = raw.windows(4).position(|w| w == b"\r\n\r\n").unwrap();
        let status = String::from_utf8_lossy(&raw[9..12]).parse().unwrap();
        (status, raw[split + 4..].to_vec())
    }

    fn setup() -> (tempfile::TempDir, Workspace) {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("index.html"), "<h1>Preview</h1>").unwrap();
        std::fs::write(dir.path().join(".env"), "secret").unwrap();
        let workspace = Workspace::new(&dir.path().to_string_lossy()).unwrap();
        (dir, workspace)
    }

    #[test]
    fn inspection_is_declarative_and_hashes_match() {
        let (dir, workspace) = setup();
        std::fs::write(dir.path().join("package.json"), r#"{"dependencies": {"@angular/core": "^20", "three": "^0.180"}, "scripts": {"dev": "never-run"}}"#).unwrap();
        let result = workspace.inspect().unwrap();
        assert_eq!(result["frameworks"], json!(["angular", "three"]));
        assert_eq!(result["scripts"], json!(["dev"]));
        assert_eq!(
            workspace.artifacts(&["index.html".into()]).unwrap()["artifacts"][0]["bytes"],
            16
        );
        assert!(Workspace::new("").is_err() && Workspace::new("   ").is_err());
    }

    #[test]
    fn previews_snapshot_isolate_and_stop() {
        let (dir, workspace) = setup();
        let other_dir = dir.path().join("專案 with spaces");
        std::fs::create_dir(&other_dir).unwrap();
        std::fs::write(other_dir.join("index.html"), "<h1>Other</h1>").unwrap();
        let other = Workspace::new(&other_dir.to_string_lossy()).unwrap();
        let previews = Previews::default();
        let files = vec!["index.html".to_string()];
        let first = previews.start(&workspace, "index.html", &files).unwrap();
        let second = previews.start(&other, "index.html", &files).unwrap();
        assert_eq!(
            get(first["url"].as_str().unwrap(), None),
            (200, b"<h1>Preview</h1>".to_vec())
        );
        assert_eq!(
            get(second["url"].as_str().unwrap(), None),
            (200, b"<h1>Other</h1>".to_vec())
        );
        std::fs::write(dir.path().join("index.html"), "changed").unwrap();
        assert_eq!(
            get(first["url"].as_str().unwrap(), None).1,
            b"<h1>Preview</h1>".to_vec()
        );
        let url = first["url"].as_str().unwrap();
        let base = url.strip_suffix("index.html").unwrap();
        for path in ["", ".env", "../.env", "%2e%2e/.env"] {
            assert_eq!(get(&format!("{base}{path}"), None).0, 404, "{path}");
        }
        assert_eq!(get(url, Some("untrusted.invalid")).0, 403);
        assert_eq!(previews.stop("someone-else")["status"], "unknown_job");
        assert_eq!(
            previews.stop(first["job_id"].as_str().unwrap())["status"],
            "stopped"
        );
        assert!(TcpStream::connect(
            url.strip_prefix("http://")
                .unwrap()
                .split('/')
                .next()
                .unwrap()
        )
        .is_err());
        assert_eq!(
            previews.status(second["job_id"].as_str().unwrap())["status"],
            "ready"
        );
    }

    #[test]
    fn manifest_limits_and_rejections() {
        let (dir, workspace) = setup();
        let previews = Previews::default();
        let one = vec!["index.html".to_string()];
        assert_eq!(
            previews.start(
                &workspace,
                "index.html",
                &["index.html".into(), "index.html".into()]
            ),
            Err(Problem("invalid_manifest"))
        );
        for name in ["../outside.html", "C:/secret.html", ".env"] {
            assert!(
                previews
                    .start(&workspace, name, &[name.to_string()])
                    .is_err(),
                "{name}"
            );
        }
        #[cfg(unix)]
        {
            std::os::unix::fs::symlink(
                dir.path().join("index.html"),
                dir.path().join("linked.html"),
            )
            .unwrap();
            assert_eq!(
                previews.start(&workspace, "linked.html", &["linked.html".into()]),
                Err(Problem("linked_path"))
            );
        }
        for _ in 0..8 {
            previews.start(&workspace, "index.html", &one).unwrap();
        }
        assert_eq!(
            previews.start(&workspace, "index.html", &one),
            Err(Problem("job_limit"))
        );
        previews.close();
    }
}
