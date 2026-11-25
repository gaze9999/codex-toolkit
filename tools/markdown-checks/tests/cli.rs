//! Synthetic fixtures only.
use serde_json::Value;
use std::fs;
use std::path::Path;
use std::process::Command;

const BIN: &str = env!("CARGO_BIN_EXE_markdown-checks");

fn run(dir: &Path, args: &[&str]) -> (i32, String, String) {
    let output = Command::new(BIN)
        .args(args)
        .current_dir(dir)
        .output()
        .unwrap();
    (
        output.status.code().unwrap(),
        String::from_utf8(output.stdout).unwrap(),
        String::from_utf8(output.stderr).unwrap(),
    )
}

fn json(text: &str) -> Value {
    serde_json::from_str(text).unwrap()
}

#[test]
fn diff_ignores_fences_and_reports_duplicate_or_order_changes() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(
        dir.path().join("left.md"),
        "# A\n\n- first\n- second\n- second\n```md\n# ignored\n```\n",
    )
    .unwrap();
    fs::write(
        dir.path().join("right.md"),
        "# A\n\n- second\n- first\n```md\n# different ignored\n```\n",
    )
    .unwrap();
    let (code, out, _) = run(
        dir.path(),
        &["diff", "--left", "left.md", "--right", "right.md"],
    );
    assert_eq!(code, 0);
    let changes = &json(&out)["changes"];
    assert_eq!(changes["headings"]["only_left"], serde_json::json!([]));
    assert_eq!(
        changes["list_items"]["only_left"],
        serde_json::json!(["- second"])
    );
    assert_eq!(changes["list_items"]["order_changed"], false);
}

#[test]
fn diff_reports_pure_reordering_and_missing_inputs() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(dir.path().join("a.md"), "| x |\n| y |\n").unwrap();
    fs::write(dir.path().join("b.md"), "| y |\n| x |\n").unwrap();
    let (_, out, _) = run(dir.path(), &["diff", "--left", "a.md", "--right", "b.md"]);
    assert_eq!(json(&out)["changes"]["table_rows"]["order_changed"], true);
    let (code, _, err) = run(
        dir.path(),
        &["diff", "--left", "a.md", "--right", "absent.md"],
    );
    assert_eq!(code, 2);
    assert!(err.contains("Both inputs must be existing Markdown files"));
}

#[test]
fn context_brief_checks_structure_traceability_and_secrets() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(
        dir.path().join("good.md"),
        "# Brief\n\n## Scope\n\nsource: spec.pdf page 3\n",
    )
    .unwrap();
    let (code, out, _) = run(
        dir.path(),
        &["context-brief", "good.md", "--required-heading", "SCOPE"],
    );
    assert_eq!(code, 0, "{out}");
    assert!(out.ends_with("SUMMARY: PASS\n"));

    fs::write(
        dir.path().join("bad.md"),
        "## Brief\n#### Deep\n```\nopen\n",
    )
    .unwrap();
    let (code, out, _) = run(dir.path(), &["context-brief", "bad.md", "--json"]);
    assert_eq!(code, 1);
    let report = json(&out);
    assert_eq!(report["status"], "fail");
    let status = |name: &str| {
        report["checks"]
            .as_array()
            .unwrap()
            .iter()
            .find(|check| check["name"] == name)
            .unwrap()["status"]
            .clone()
    };
    assert_eq!(status("title"), "WARN");
    assert_eq!(status("code_fences"), "FAIL");

    fs::write(
        dir.path().join("secret.md"),
        "# Brief\nhttps://example.com\napi_key = abcdefghijklmnopqrstu\n",
    )
    .unwrap();
    let (code, out, _) = run(dir.path(), &["context-brief", "secret.md", "--json"]);
    assert_eq!(code, 1);
    assert!(out.contains("possible secret or credential pattern found"));
    assert!(!out.contains("abcdefghijklmnopqrstu"));
}

#[test]
fn context_brief_strict_turns_warnings_into_failures() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(dir.path().join("brief.md"), "# Brief\n").unwrap();
    assert_eq!(run(dir.path(), &["context-brief", "brief.md"]).0, 0);
    assert_eq!(
        run(dir.path(), &["context-brief", "brief.md", "--strict"]).0,
        1
    );
}

#[test]
fn scan_changes_classifies_diff_files_and_limits_output() {
    let dir = tempfile::tempdir().unwrap();
    let patch = "diff --git a/README.md b/README.md\ndiff --git a/src/api/routes.ts b/src/api/routes.ts\ndiff --git a/tests/x.py b/tests/x.py\ndiff --git a/a.bin b/a.bin\n";
    fs::write(dir.path().join("d.patch"), patch).unwrap();
    let (code, out, _) = run(
        dir.path(),
        &[
            "scan-changes",
            "--diff-file",
            "d.patch",
            "--json",
            "--max-files",
            "2",
        ],
    );
    assert_eq!(code, 0);
    let report = json(&out);
    assert_eq!(
        report["counts"],
        serde_json::json!({ "yes": 2, "maybe": 0, "no": 2 })
    );
    assert_eq!(report["omitted"], 2);
    assert_eq!(report["files"][1]["category"], "public-contract");
    let (code, out, _) = run(dir.path(), &["scan-changes", "--max-files", "-1"]);
    assert_eq!(
        (code, out.trim()),
        (2, "ERROR: --max-files must be 0 or greater")
    );
}

#[test]
fn scan_changes_reads_staged_unstaged_and_untracked_git_changes() {
    let dir = tempfile::tempdir().unwrap();
    let git = |args: &[&str]| {
        assert!(Command::new("git")
            .args(args)
            .current_dir(dir.path())
            .output()
            .unwrap()
            .status
            .success())
    };
    git(&["init", "-q"]);
    fs::create_dir_all(dir.path().join("docs")).unwrap();
    fs::write(dir.path().join("docs/guide.md"), "a").unwrap();
    git(&["add", "."]);
    git(&[
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.com",
        "commit",
        "-qm",
        "init",
    ]);
    fs::write(dir.path().join("docs/guide.md"), "b").unwrap();
    fs::write(dir.path().join("new.txt"), "c").unwrap();
    let (code, out, _) = run(dir.path(), &["scan-changes", "--json"]);
    assert_eq!(code, 0);
    let files: Vec<(String, String)> = json(&out)["files"]
        .as_array()
        .unwrap()
        .iter()
        .map(|file| {
            (
                file["path"].as_str().unwrap().into(),
                file["change_type"].as_str().unwrap().into(),
            )
        })
        .collect();
    assert_eq!(
        files,
        [
            ("docs/guide.md".into(), "M".into()),
            ("new.txt".into(), "??".into())
        ]
    );
}

#[test]
fn scan_changes_stat_reports_stage_and_line_counts() {
    let dir = tempfile::tempdir().unwrap();
    let renamed = if cfg!(windows) {
        "new name.txt"
    } else {
        "new|name.txt"
    };
    let git = |args: &[&str]| {
        let output = Command::new("git")
            .args(args)
            .current_dir(dir.path())
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "git {args:?}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    };
    let commit = |message: &str| {
        git(&[
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-qm",
            message,
        ])
    };
    git(&["init", "-q"]);
    fs::write(dir.path().join("both.md"), "1\n2\n3\n").unwrap();
    fs::write(dir.path().join("staged.rs"), "a\n").unwrap();
    fs::write(dir.path().join("old name.txt"), "keep\nthese\nlines\n").unwrap();
    git(&["add", "."]);
    commit("init");
    fs::write(dir.path().join("both.md"), "1\n2\n3\n4\n").unwrap();
    fs::write(dir.path().join("staged.rs"), "b\nc\n").unwrap();
    git(&["mv", "old name.txt", renamed]);
    git(&["add", "."]);
    fs::write(dir.path().join("both.md"), "1\n3\n4\n5\n").unwrap();
    fs::write(dir.path().join("fresh.txt"), "x\ny").unwrap();
    fs::write(dir.path().join("blob.bin"), [0u8, 1, 2]).unwrap();

    let (code, out, _) = run(dir.path(), &["scan-changes", "--stat", "--json"]);
    assert_eq!(code, 0);
    let report = json(&out);
    let fact = |path: &str| {
        let file = report["files"]
            .as_array()
            .unwrap()
            .iter()
            .find(|file| file["path"] == path)
            .unwrap_or_else(|| panic!("{path} missing"));
        (
            file["stage"].as_str().unwrap().to_string(),
            file["added"].clone(),
            file["deleted"].clone(),
        )
    };
    let n = |value: u64| serde_json::json!(value);
    assert_eq!(fact("both.md"), ("staged+unstaged".into(), n(2), n(1)));
    assert_eq!(fact("staged.rs"), ("staged".into(), n(2), n(1)));
    assert_eq!(fact(renamed), ("staged".into(), n(0), n(0)));
    assert_eq!(fact("fresh.txt"), ("untracked".into(), n(2), n(0)));
    assert_eq!(fact("blob.bin"), ("untracked".into(), Value::Null, n(0)));

    let (code, out, _) = run(dir.path(), &["scan-changes", "--table"]);
    assert_eq!(code, 0);
    assert!(out.contains("| File | Stage | Change | Added | Deleted | Category | Doc impact |"));
    assert!(out.contains("| `both.md` | staged+unstaged | M | 2 | 1 | documentation | yes |"));
    let table_name = renamed.replace('|', "\\|");
    assert!(out.contains(&format!("| `{table_name}` | staged | R100 | 0 | 0 |")));
    assert!(out.contains("| `blob.bin` | untracked | ?? | - | 0 |"));

    let (code, out, _) = run(dir.path(), &["scan-changes", "--json"]);
    assert_eq!(code, 0);
    assert!(json(&out)["files"][0].get("stage").is_none());

    git(&["add", "."]);
    commit("second");
    let (_, out, _) = run(dir.path(), &["scan-changes", "--stat", "--json"]);
    let report = json(&out);
    let staged = report["files"]
        .as_array()
        .unwrap()
        .iter()
        .find(|file| file["path"] == "staged.rs")
        .unwrap();
    assert_eq!(staged["stage"], "commit");
    assert_eq!((&staged["added"], &staged["deleted"]), (&n(2), &n(1)));

    let (code, _, err) = run(dir.path(), &["scan-changes", "--table", "--json"]);
    assert_eq!(code, 2);
    assert!(err.contains("--table cannot be combined with --json"));
}

#[test]
fn sync_inspect_reads_metadata_only_when_requested() {
    let dir = tempfile::tempdir().unwrap();
    let text = "---\nnotion_page_id: 0123456789abcdef0123456789abcdef\nsync_mode: push\n---\n# Title ##\nhttps://www.notion.so/Page-1\n";
    fs::write(dir.path().join("t.md"), text).unwrap();
    let (code, out, _) = run(dir.path(), &["sync-inspect", "t.md", "--json"]);
    assert_eq!(code, 0);
    let target = &json(&out)["target"];
    assert_eq!(
        target["headings"],
        serde_json::json!([{ "level": 1, "text": "Title" }])
    );
    assert!(target.get("notion_page_ids").is_none());
    let (_, out, _) = run(
        dir.path(),
        &[
            "sync-inspect",
            "t.md",
            "--json",
            "--include-notion-metadata",
        ],
    );
    let target = &json(&out)["target"];
    assert_eq!(
        target["notion_page_ids"],
        serde_json::json!(["0123456789abcdef0123456789abcdef"])
    );
    assert_eq!(target["sync_mode"], "push");
    let (code, out, _) = run(dir.path(), &["sync-inspect", "t.txt", "--json"]);
    assert_eq!(code, 2);
    assert_eq!(json(&out)["status"], "error");
}

#[test]
fn sync_write_requires_the_inspected_hash() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(dir.path().join("t.md"), "# Old\n").unwrap();
    fs::write(dir.path().join("new.txt"), "# New\n").unwrap();
    let (_, out, _) = run(dir.path(), &["sync-inspect", "t.md", "--json"]);
    let hash = json(&out)["target"]["sha256"].as_str().unwrap().to_string();

    let (code, _, err) = run(
        dir.path(),
        &[
            "sync-write",
            "t.md",
            "--content-file",
            "new.txt",
            "--expected-sha256",
            "0",
        ],
    );
    assert_eq!(code, 3, "{err}");
    let (code, out, _) = run(
        dir.path(),
        &[
            "sync-write",
            "t.md",
            "--content-file",
            "new.txt",
            "--expected-sha256",
            &hash,
            "--dry-run",
        ],
    );
    assert_eq!(code, 0);
    assert!(out.starts_with("DRY-RUN:"));
    assert_eq!(
        fs::read_to_string(dir.path().join("t.md")).unwrap(),
        "# Old\n"
    );

    let (code, out, _) = run(
        dir.path(),
        &[
            "sync-write",
            "t.md",
            "--content-file",
            "new.txt",
            "--expected-sha256",
            &hash.to_uppercase(),
        ],
    );
    assert_eq!(code, 0);
    assert!(out.starts_with("WROTE:"));
    assert_eq!(
        fs::read_to_string(dir.path().join("t.md")).unwrap(),
        "# New\n"
    );
    assert_eq!(
        fs::read_dir(dir.path()).unwrap().count(),
        2,
        "no temporary file is left behind"
    );
}

#[cfg(unix)]
#[test]
fn sync_write_keeps_target_permissions() {
    use std::os::unix::fs::PermissionsExt;
    let dir = tempfile::tempdir().unwrap();
    let target = dir.path().join("t.md");
    fs::write(&target, "# Old\n").unwrap();
    fs::set_permissions(&target, fs::Permissions::from_mode(0o644)).unwrap();
    fs::write(dir.path().join("new.txt"), "# New\n").unwrap();
    let hash = markdown_checks::text::sha256(b"# Old\n");
    assert_eq!(
        run(
            dir.path(),
            &[
                "sync-write",
                "t.md",
                "--content-file",
                "new.txt",
                "--expected-sha256",
                &hash
            ]
        )
        .0,
        0
    );
    assert_eq!(
        fs::metadata(&target).unwrap().permissions().mode() & 0o777,
        0o644
    );
}

#[test]
fn python_compatible_line_splitting_and_suffix() {
    use markdown_checks::text::{split_lines, suffix};
    assert_eq!(split_lines("a\r\nb\rc\u{2028}d\n"), ["a", "b", "c", "d"]);
    assert_eq!(suffix(".env"), "");
    assert_eq!(suffix("docs/Guide.MD"), ".md");
    assert_eq!(suffix(".env.example"), ".example");
}
