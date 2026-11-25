use std::io::Write;
use std::path::Path;
use std::process::{Command, Output, Stdio};

fn run(cwd: &Path, args: &[&str], stdin: Option<&[u8]>) -> Output {
    let mut child = Command::new(env!("CARGO_BIN_EXE_token-count"))
        .args(args)
        .current_dir(cwd)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(stdin.unwrap_or_default())
        .unwrap();
    child.wait_with_output().unwrap()
}

fn json(output: &Output) -> serde_json::Value {
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).unwrap()
}

#[test]
fn counts_files_independently_and_keeps_crlf() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("a.txt"), b"\xEF\xBB\xBFhello world").unwrap();
    std::fs::write(dir.path().join("b.txt"), "x\r\n").unwrap();
    let report = json(&run(
        dir.path(),
        &["--input", "a.txt", "b.txt", "--json"],
        None,
    ));
    assert_eq!(report["results"][0]["tokens"], 2);
    assert_eq!(report["results"][0]["chars"], 11);
    assert_eq!(report["results"][1]["utf8_bytes"], 3);
    let total = report["results"][0]["tokens"].as_u64().unwrap()
        + report["results"][1]["tokens"].as_u64().unwrap();
    assert_eq!(report["total_tokens"], total);
}

#[test]
fn reads_stdin_and_reports_empty_ratio() {
    let dir = tempfile::tempdir().unwrap();
    let report = json(&run(dir.path(), &["--json"], Some(b"")));
    assert_eq!(report["results"][0]["source"], "stdin");
    assert!(report["results"][0]["chars_per_token"].is_null());
    let text = run(
        dir.path(),
        &["--text", "", "--encoding", "cl100k_base"],
        None,
    );
    assert!(String::from_utf8_lossy(&text.stdout).contains("字元/Token: 無 (空文字)"));
}

#[test]
fn writes_new_outputs_only() {
    let dir = tempfile::tempdir().unwrap();
    let ok = run(
        dir.path(),
        &[
            "--text",
            "繁體 👩‍💻",
            "--output",
            "r.json",
            "--html",
            "t.html",
        ],
        None,
    );
    assert!(ok.status.success());
    let saved: serde_json::Value =
        serde_json::from_slice(&std::fs::read(dir.path().join("r.json")).unwrap()).unwrap();
    assert_eq!(saved["results"][0]["source"], "inline");
    let page = std::fs::read_to_string(dir.path().join("t.html")).unwrap();
    assert!(page.contains("Token 彩色檢視") && page.contains("data-tokens"));

    let again = run(dir.path(), &["--text", "x", "--output", "r.json"], None);
    assert_eq!(again.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&again.stderr).contains("輸出檔已存在"));
}

#[test]
fn rejects_invalid_arguments() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("a.txt"), "a").unwrap();
    for args in [
        &["--input", "a.txt", "--text", "x"][..],
        &["--text", "x", "--encoding", "nope"],
        &["--text", "x", "--max-display-tokens", "0"],
        &["--input", "a.txt", "--output", "a.txt"],
        &["--unknown"],
    ] {
        assert_eq!(
            run(dir.path(), args, None).status.code(),
            Some(2),
            "{args:?}"
        );
    }
    std::fs::write(dir.path().join("bad.txt"), [0xff, 0xfe]).unwrap();
    assert_eq!(
        run(dir.path(), &["--input", "bad.txt"], None).status.code(),
        Some(2)
    );
}

#[test]
fn estimates_context_from_selected_sources() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let home = root.join("home");
    std::fs::create_dir_all(home.join("skills/demo")).unwrap();
    std::fs::create_dir_all(root.join("repo/.git")).unwrap();
    std::fs::create_dir_all(root.join("repo/.codex")).unwrap();
    std::fs::write(home.join("AGENTS.md"), "global").unwrap();
    std::fs::write(
        home.join("skills/demo/SKILL.md"),
        "---\nname: demo\ndescription: Demo skill\n---\n",
    )
    .unwrap();
    std::fs::write(
        home.join("config.toml"),
        "[mcp_servers.one]\ncommand = \"x\"\n",
    )
    .unwrap();
    std::fs::write(root.join("repo/AGENTS.md"), "project").unwrap();
    std::fs::write(
        root.join("repo/.codex/config.toml"),
        "[mcp_servers.one]\nenabled = false\n[mcp_servers.two]\ncommand = \"y\"\n",
    )
    .unwrap();
    let report = json(&run(
        root,
        &[
            "context",
            "--project",
            "repo",
            "--codex-home",
            "home",
            "--mcp-tools",
            "2",
            "--json",
        ],
        None,
    ));
    let categories: Vec<&str> = report["components"]
        .as_array()
        .unwrap()
        .iter()
        .map(|row| row["category"].as_str().unwrap())
        .collect();
    assert_eq!(
        categories,
        [
            "Global Agent",
            "Project Agent",
            "Skills 探索清單",
            "系統基礎預估",
            "內建工具預估 (10 項)",
            "MCP Server 預估 (1 個)",
            "MCP 工具預估 (2 項)"
        ]
    );
    assert_eq!(report["mcp_servers"], serde_json::json!(["two"]));
    assert_eq!(report["skill_count"], 1);
    assert!(report["total"]["low"].as_u64().unwrap() < report["total"]["high"].as_u64().unwrap());

    let missing = run(
        root,
        &["context", "--project", "nope", "--codex-home", "home"],
        None,
    );
    assert_eq!(missing.status.code(), Some(2));
}
