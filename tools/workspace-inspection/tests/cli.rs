use serde_json::{json, Value};
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};
use workspace_inspection::environment::{compare_trees, DEFAULT_EXCLUDES};
use workspace_inspection::validation::{assess_evidence, index_evidence};

static NEXT: AtomicUsize = AtomicUsize::new(0);

struct Fixture(PathBuf);
impl Fixture {
    fn new() -> Self {
        let root = std::env::temp_dir().join(format!(
            "workspace-inspection-test-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        Self(fs::canonicalize(root).unwrap())
    }
    fn put(&self, name: &str, contents: &str) {
        let path = self.0.join(name);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, contents).unwrap();
    }
    fn path(&self, name: &str) -> String {
        self.0.join(name).to_string_lossy().into_owned()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

/// The full result from the `report.json` a run names; removes that run's folder when it is temporary.
fn report_json(output: &Output) -> Value {
    let text = String::from_utf8_lossy(&output.stdout).into_owned();
    let path = text
        .lines()
        .filter_map(|line| line.strip_prefix("report: "))
        .find(|path| path.ends_with("report.json"))
        .unwrap_or_else(|| {
            panic!(
                "no report.json in {text} {}",
                String::from_utf8_lossy(&output.stderr)
            )
        });
    let value = serde_json::from_slice(&fs::read(path).unwrap()).unwrap();
    let folder = std::path::Path::new(path).parent().unwrap();
    if folder.starts_with(fs::canonicalize(std::env::temp_dir()).unwrap()) {
        let _ = fs::remove_dir_all(folder);
    }
    value
}

fn cli(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_workspace-inspection"))
        .args(args)
        .output()
        .unwrap()
}
fn sha(ch: char) -> String {
    ch.to_string().repeat(64)
}

#[test]
fn validity_follows_supplied_provenance_only() {
    let verdict = |recorded: Value, current: Value| assess_evidence(&recorded, &current).unwrap();
    let recorded = json!({"source_revision":"abcdef1","source_diff_sha256":sha('a'),"covered_paths":["src/a.ts"]});
    let current = json!({"source_revision":"ABCDEF1","source_diff_sha256":sha('A'),"affected_paths":["src/a.ts"]});
    assert_eq!(
        verdict(recorded.clone(), current.clone())["status"],
        "current"
    );
    // A path outside the recorded coverage keeps the evidence partial
    let wider = json!({"source_revision":"abcdef1","source_diff_sha256":sha('a'),"affected_paths":["src/a.ts","src/b.ts"]});
    let partial = verdict(recorded.clone(), wider);
    assert_eq!(partial["status"], "partial");
    assert_eq!(partial["uncovered_paths"], json!(["src/b.ts"]));
    assert_eq!(partial["reasons"], json!(["affected_paths_not_covered"]));
    // A changed revision without file hashes cannot establish the source
    let moved = verdict(
        recorded.clone(),
        json!({"source_revision":"1234567","source_diff_sha256":sha('a')}),
    );
    assert_eq!(moved["status"], "outdated");
    assert_eq!(
        moved["reasons"],
        json!([
            "source_revision_changed",
            "current_source_identity_not_established",
            "affected_path_coverage_unknown"
        ])
    );
    // File hashes decide when the revision differs
    let files = json!({"source_files":{"src/z.ts":sha('1'),"src/a.ts":sha('2')},"artifact_sha256":sha('c'),"covered_paths":[]});
    let same_files = verdict(
        files.clone(),
        json!({"source_files":{"src/a.ts":sha('2'),"src/z.ts":sha('1')},"affected_paths":[]}),
    );
    assert_eq!(same_files["status"], "partial");
    assert_eq!(same_files["reasons"], json!(["artifact_hash_missing"]));
    let edited = verdict(
        files,
        json!({"source_files":{"src/z.ts":sha('9')},"artifact_sha256":sha('d')}),
    );
    assert_eq!(edited["status"], "outdated");
    assert_eq!(
        edited["reasons"],
        json!([
            "source_file_changed:src/z.ts",
            "source_file_hash_missing:src/a.ts",
            "artifact_changed",
            "affected_path_coverage_unknown"
        ])
    );
    assert_eq!(
        verdict(json!("text"), json!({}))["reasons"],
        json!(["recorded_baseline_missing_or_unstructured"])
    );
    assert_eq!(
        verdict(json!({"source_revision":"zz"}), json!({}))["reasons"],
        json!(["recorded_baseline_malformed"])
    );
    for bad in [
        json!([1]),
        json!({"source_revision":"nothex"}),
        json!({"affected_paths":[""]}),
        json!({"source_files":{"a":"1"}}),
    ] {
        assert!(
            assess_evidence(&Value::Null, &bad).is_err(),
            "{bad} accepted"
        );
    }
}

fn evidence_fixture() -> Fixture {
    let fixture = Fixture::new();
    fixture.put(
        "run-0002/results.json",
        &json!({"started":"2026-11-02","baseline":{"source_revision":"abcdef1","source_diff_sha256":sha('a'),"covered_paths":["src/a.ts"]},
            "results":[{"name":"unit","status":"PASS","command":"cargo test","extra":1},
                {"name":"e2e","status":"FAIL","reason":"timeout","baseline":{"source_revision":"1234567"}}],"unverified":["deploy"]})
        .to_string(),
    );
    fixture.put("run-0001/results.json", "\u{feff}{\"results\":[]}");
    fixture.put("run-0003/results.json", "{\"results\":{}}");
    fixture.put("other/results.json", "{}");
    fs::create_dir(fixture.0.join("run-empty")).unwrap();
    fixture
}

#[test]
fn evidence_index_orders_runs_and_reports_unreadable_ones() {
    let fixture = evidence_fixture();
    let index = index_evidence(&fixture.0, 20, None).unwrap();
    let runs: Vec<&str> = index["runs"]
        .as_array()
        .unwrap()
        .iter()
        .map(|run| run["run"].as_str().unwrap())
        .collect();
    assert_eq!(runs, ["run-0002", "run-0001"]);
    let first = &index["runs"][0];
    assert_eq!(first["unverified"], json!(["deploy"]));
    assert_eq!(
        first["results"][0],
        json!({"name":"unit","status":"PASS","reason":null,"command":"cargo test","log":null,"source":null,"baseline":null})
    );
    assert_eq!(index["runs"][1]["unverified"], json!([]));
    assert_eq!(index["errors"][0]["run"], "run-0003");
    assert_eq!(index["errors"][0]["error"], "results must be an array");
    assert_eq!(
        index_evidence(&fixture.0, 1, None).unwrap()["runs"]
            .as_array()
            .unwrap()
            .len(),
        0
    );
    assert!(index_evidence(&fixture.0, 0, None).is_err());
    assert!(index_evidence(&fixture.0.join("missing"), 20, None).is_err());

    let current = json!({"source_revision":"abcdef1","source_diff_sha256":sha('a'),"affected_paths":["src/a.ts"]});
    let assessed = index_evidence(&fixture.0, 20, Some(&current)).unwrap();
    let run = &assessed["runs"][0];
    assert_eq!(run["validity"]["status"], "current");
    // A result without its own baseline inherits the run baseline
    assert_eq!(run["results"][0]["validity"]["status"], "current");
    assert_eq!(run["results"][1]["validity"]["status"], "outdated");
    assert_eq!(assessed["runs"][1]["validity"]["status"], "unverified");
    assert!(index_evidence(&fixture.0, 20, Some(&json!({"source_revision":"x"}))).is_err());
}

fn trees() -> (Fixture, Fixture) {
    let (source, target) = (Fixture::new(), Fixture::new());
    for (name, left, right) in [
        ("same.txt", Some("x"), Some("x")),
        ("diff.txt", Some("1"), Some("22")),
        ("sub/only_a.ts", Some("a"), None),
        ("only_b.ts", None, Some("b")),
        (".env", Some("s"), Some("t")),
        ("keys/id.pem", Some("p"), Some("q")),
        (".git/HEAD", Some("1"), Some("2")),
        ("pkg/__pycache__/m.pyc", Some("1"), Some("2")),
    ] {
        if let Some(text) = left {
            source.put(name, text);
        }
        if let Some(text) = right {
            target.put(name, text);
        }
    }
    (source, target)
}

#[test]
fn tree_comparison_reports_differences_and_honors_patterns() {
    let (source, target) = trees();
    let defaults: Vec<&str> = DEFAULT_EXCLUDES.to_vec();
    let none: [&str; 0] = [];
    let result = compare_trees(&source.0, &target.0, &none, &defaults, 20_000).unwrap();
    assert_eq!(result["status"], "different");
    assert_eq!(result["missing_in_target"], json!(["sub/only_a.ts"]));
    assert_eq!(result["extra_in_target"], json!(["only_b.ts"]));
    assert_eq!(result["changed"][0]["path"], "diff.txt");
    assert_eq!(result["changed"][0]["source"]["size"], 1);
    assert_eq!(result["changed"][0]["target"]["size"], 2);
    assert_eq!(
        (&result["source_files"], &result["target_files"]),
        (&json!(3), &json!(3))
    );
    // Secrets, keys, caches and VCS data are skipped by default and counted
    assert_eq!(result["excluded"], json!({"source":4,"target":4}));
    let everything = compare_trees(&source.0, &target.0, &none, &none, 20_000).unwrap();
    assert_eq!(everything["source_files"], 7);
    assert_eq!(everything["changed"].as_array().unwrap().len(), 5);
    let only_same = compare_trees(&source.0, &target.0, &["same.*"], &defaults, 20_000).unwrap();
    assert_eq!(only_same["status"], "match");
    let negated = compare_trees(&source.0, &target.0, &["[!d]*.txt"], &defaults, 20_000).unwrap();
    assert_eq!(
        (&negated["status"], &negated["source_files"]),
        (&json!("match"), &json!(1))
    );
    for (max, nested) in [(2, false), (0, false), (200_001, false), (10, true)] {
        let other = if nested {
            source.0.join("sub")
        } else {
            target.0.clone()
        };
        assert!(compare_trees(&source.0, &other, &none, &defaults, max).is_err());
    }
    assert!(compare_trees(&source.0, &source.0, &none, &defaults, 10).is_err());
}

#[test]
fn cli_prints_json_and_writes_reports_outside_the_inspected_folders() {
    let fixture = evidence_fixture();
    let printed = cli(&["evidence", "--root", &fixture.path(""), "--format", "json"]);
    assert_eq!(printed.status.code(), Some(1));
    // A short summary on standard output, the complete index in the report file
    let text = String::from_utf8_lossy(&printed.stdout).into_owned();
    assert!(text.starts_with("validation evidence: 2 runs read, 1 unreadable\nresults: FAIL 1, PASS 1\nlatest run-0002: FAIL 1, PASS 1\nvalidity not assessed: no current baseline given\nreport: "));
    let index = report_json(&printed);
    assert_eq!(index["runs"].as_array().unwrap().len(), 2);
    let outputs = Fixture::new();
    let report = cli(&[
        "evidence",
        "--root",
        &fixture.path(""),
        "--format",
        "all",
        "--out",
        &outputs.path("evidence"),
    ]);
    assert_eq!(report.status.code(), Some(1));
    let page = fs::read_to_string(outputs.0.join("evidence/report.html")).unwrap();
    assert!(
        page.contains("驗證證據彙總")
            && page.contains("1 次執行無法讀取")
            && page.contains("<code>cargo test</code>")
    );
    assert!(fs::read_to_string(outputs.0.join("evidence/report.md"))
        .unwrap()
        .contains("| run-0002 | unit | PASS |"));
    assert_eq!(
        cli(&[
            "evidence",
            "--root",
            &fixture.path(""),
            "--format",
            "html",
            "--out",
            &fixture.path("inside")
        ])
        .status
        .code(),
        Some(2)
    );

    let (source, target) = trees();
    let compared = cli(&[
        "compare",
        "--format",
        "json",
        "--source",
        &source.path(""),
        "--target",
        &target.path(""),
        "--exclude",
        "*.ts",
    ]);
    assert_eq!(compared.status.code(), Some(1));
    let text = String::from_utf8_lossy(&compared.stdout).into_owned();
    assert!(text.starts_with("environment compare: different; source 2 files, target 2 files\nmissing in target 0, extra in target 0, changed 1, read errors 0\nmost differences in . (1)\nreport: "), "{text}");
    let result = report_json(&compared);
    assert_eq!(result["missing_in_target"], json!([]));
    let matched = cli(&[
        "compare",
        "--source",
        &source.path(""),
        "--target",
        &target.path(""),
        "--include",
        "same.txt",
    ]);
    assert_eq!(matched.status.code(), Some(0));
    // Neither side may receive the report
    assert_eq!(
        cli(&[
            "compare",
            "--source",
            &source.path(""),
            "--target",
            &target.path(""),
            "--format",
            "html",
            "--out",
            &target.path("report")
        ])
        .status
        .code(),
        Some(2)
    );
    let html = cli(&[
        "compare",
        "--source",
        &source.path(""),
        "--target",
        &target.path(""),
        "--format",
        "html",
        "--out",
        &outputs.path("compare"),
    ]);
    assert_eq!(html.status.code(), Some(1));
    assert!(fs::read_to_string(outputs.0.join("compare/report.html"))
        .unwrap()
        .contains("環境比對"));
    assert_eq!(
        cli(&["compare", "--source", &source.path("")])
            .status
            .code(),
        Some(2)
    );
    assert_eq!(cli(&["evidence", "--unknown", "x"]).status.code(), Some(2));
}

#[test]
fn mcp_serves_three_read_only_tools_within_read_roots() {
    let fixture = evidence_fixture();
    let (source, target) = trees();
    let outside = Fixture::new();
    let mut child = Command::new(env!("CARGO_BIN_EXE_workspace-inspection"))
        .args([
            "mcp",
            "--read-root",
            &fixture.path(""),
            "--read-root",
            &source.path(""),
            "--read-root",
            &target.path(""),
        ])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();
    let call = |id: u32, name: &str, arguments: Value| json!({"jsonrpc":"2.0","id":id,"method":"tools/call","params":{"name":name,"arguments":arguments}});
    let requests = [
        json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}),
        json!({"jsonrpc":"2.0","method":"notifications/initialized"}),
        json!({"jsonrpc":"2.0","id":2,"method":"tools/list"}),
        call(3, "workspace_status", json!({})),
        call(
            4,
            "validation_evidence",
            json!({"root":fixture.path(""),"limit":1,"current":{"source_revision":"abcdef1"}}),
        ),
        call(
            5,
            "compare_environment",
            json!({"source":source.path(""),"target":target.path(""),"excludes":["*.ts"],"use_default_excludes":false}),
        ),
        call(6, "validation_evidence", json!({"root":outside.path("")})),
        call(
            7,
            "compare_environment",
            json!({"source":source.path(""),"target":target.path(""),"use_default_excludes":"yes"}),
        ),
        call(8, "validation_evidence", json!({"root":"relative"})),
        call(9, "write_files", json!({})),
        call(10, "workspace_status", json!({"extra":1})),
    ];
    let mut input = child.stdin.take().unwrap();
    for request in &requests {
        writeln!(input, "{request}").unwrap();
    }
    drop(input);
    let output = child.wait_with_output().unwrap();
    let replies: Vec<Value> = String::from_utf8(output.stdout)
        .unwrap()
        .lines()
        .map(|line| serde_json::from_str(line).unwrap())
        .collect();
    assert_eq!(replies.len(), requests.len() - 1);
    let reply = |id: u32| &replies.iter().find(|reply| reply["id"] == id).unwrap()["result"];
    assert_eq!(reply(1)["serverInfo"]["name"], "Workspace Inspection");
    let names: Vec<&str> = reply(2)["tools"]
        .as_array()
        .unwrap()
        .iter()
        .map(|tool| tool["name"].as_str().unwrap())
        .collect();
    assert_eq!(
        names,
        [
            "workspace_status",
            "validation_evidence",
            "compare_environment"
        ]
    );
    assert!(reply(2)["tools"]
        .as_array()
        .unwrap()
        .iter()
        .all(|tool| tool["annotations"]["readOnlyHint"] == (tool["name"] == "workspace_status")));
    assert_eq!(reply(3)["structuredContent"]["read_only"], true);
    assert_eq!(
        reply(3)["structuredContent"]["read_roots"]
            .as_array()
            .unwrap()
            .len(),
        3
    );
    assert_eq!(
        reply(4)["structuredContent"]["errors"][0]["run"],
        "run-0003"
    );
    assert_eq!(reply(5)["structuredContent"]["source_files"], 6);
    // Both tools answer with a summary and write the complete result to report files
    for id in [4, 5] {
        let short = &reply(id)["structuredContent"];
        let text = reply(id)["content"][0]["text"].as_str().unwrap();
        assert!(
            text.contains("\nreport: ") && text.lines().count() <= 8,
            "{text}"
        );
        assert_eq!(short["summary"][0], text.lines().next().unwrap());
        let saved = PathBuf::from(short["reports"]["json"].as_str().unwrap());
        assert!(
            saved.is_file() && PathBuf::from(short["reports"]["md"].as_str().unwrap()).is_file()
        );
        let full: Value = serde_json::from_slice(&fs::read(&saved).unwrap()).unwrap();
        if id == 4 {
            assert_eq!(short["run_count"], full["runs"].as_array().unwrap().len());
            // limit 1 selects the newest folder, which is the unreadable run
            assert_eq!(short["runs"], json!([]));
            assert_eq!(short["errors"][0]["run"], "run-0003");
        } else {
            assert_eq!(
                short["counts"]["changed"],
                full["changed"].as_array().unwrap().len()
            );
            assert_eq!(short["status"], full["status"]);
        }
        fs::remove_dir_all(saved.parent().unwrap()).unwrap();
    }
    assert_eq!(reply(5)["isError"], false);
    for (id, text) in [
        (6, "outside the configured read roots"),
        (7, "must be a boolean"),
        (8, "absolute path"),
        (9, "Unknown tool"),
        (10, "Unknown argument"),
    ] {
        assert_eq!(reply(id)["isError"], true);
        assert!(
            reply(id)["content"][0]["text"]
                .as_str()
                .unwrap()
                .contains(text),
            "{id}"
        );
    }
    assert_eq!(cli(&["mcp"]).status.code(), Some(2));
    assert_eq!(
        cli(&["mcp", "--read-root", "relative"]).status.code(),
        Some(2)
    );
}

#[test]
fn a_comparison_without_files_is_not_a_match() {
    let (source, target) = trees();
    let defaults: Vec<&str> = DEFAULT_EXCLUDES.to_vec();
    let nothing = compare_trees(&source.0, &target.0, &["*.nomatch"], &defaults, 20_000).unwrap();
    assert_eq!(nothing["status"], "empty");
    assert_eq!(
        (&nothing["source_files"], &nothing["target_files"]),
        (&json!(0), &json!(0))
    );
    let output = cli(&[
        "compare",
        "--source",
        &source.path(""),
        "--target",
        &target.path(""),
        "--include",
        "*.nomatch",
    ]);
    assert_eq!(output.status.code(), Some(1));
    let outputs = Fixture::new();
    cli(&[
        "compare",
        "--source",
        &source.path(""),
        "--target",
        &target.path(""),
        "--include",
        "*.nomatch",
        "--format",
        "html",
        "--out",
        &outputs.path("r"),
    ]);
    assert!(fs::read_to_string(outputs.0.join("r/report.html"))
        .unwrap()
        .contains("沒有比對到任何檔案"));
    let twice = cli(&[
        "compare",
        "--source",
        &source.path(""),
        "--source",
        &target.path(""),
        "--target",
        &target.path(""),
    ]);
    assert_eq!(twice.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&twice.stderr).contains("--source is given more than once"));
    assert_eq!(
        cli(&["evidence", "--limit", "5", "--limit", "6"])
            .status
            .code(),
        Some(2)
    );
}
