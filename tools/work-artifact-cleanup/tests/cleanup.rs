use serde_json::Value;
use std::fs;
use std::path::Path;
use std::time::{Duration, SystemTime};
use work_artifact_cleanup::{run, utc_iso, QUARANTINE_MARKER};

fn invoke(args: &[&str]) -> (i32, String, String) {
    let args: Vec<String> = args.iter().map(|arg| arg.to_string()).collect();
    let (mut out, mut err) = (Vec::new(), Vec::new());
    let code = run(&args, &mut out, &mut err);
    (
        code,
        String::from_utf8(out).unwrap(),
        String::from_utf8(err).unwrap(),
    )
}

fn text(path: &Path) -> &str {
    path.to_str().unwrap()
}

fn summary(stdout: &str) -> Value {
    serde_json::from_str(stdout.split("Manifest:").next().unwrap()).unwrap()
}

#[test]
fn preview_lists_cache_without_moving_it() {
    let root = tempfile::tempdir().unwrap();
    let cache = root.path().join("project/__pycache__");
    fs::create_dir_all(&cache).unwrap();
    fs::write(cache.join("sample.pyc"), b"cache").unwrap();
    let output = root.path().join("cleanup-output");
    let (code, stdout, _) = invoke(&[
        "--root",
        text(&root.path().join("project")),
        "--min-age-days",
        "0",
        "--output-dir",
        text(&output),
    ]);
    assert_eq!(code, 0);
    let value = summary(&stdout);
    assert_eq!(value["mode"], "preview");
    assert_eq!(value["candidate_count"], 1);
    assert_eq!(value["candidate_bytes"], 5);
    assert!(cache.is_dir());
}

#[test]
fn unowned_quarantine_and_nested_worktree_are_preserved() {
    let root = tempfile::tempdir().unwrap();
    let output = root.path().join("cleanup-output");
    let unrelated = output.join("quarantine/personal-backup");
    fs::create_dir_all(&unrelated).unwrap();
    fs::write(unrelated.join("keep.txt"), "keep").unwrap();
    let (code, _, _) = invoke(&[
        "--output-dir",
        text(&output),
        "--purge-quarantine",
        "--older-than-days",
        "0",
    ]);
    assert_eq!(code, 0);
    assert!(unrelated.is_dir());

    let nested = root.path().join("project/tmp");
    fs::create_dir_all(&nested).unwrap();
    fs::write(nested.join(".git"), "gitdir: elsewhere").unwrap();
    let (code, stdout, _) = invoke(&[
        "--root",
        text(&root.path().join("project")),
        "--include-work-dirs",
        "--min-age-days",
        "0",
        "--output-dir",
        text(&output),
    ]);
    assert_eq!(code, 0);
    assert_eq!(summary(&stdout)["candidate_count"], 0);
}

#[test]
fn purge_removes_only_owned_runs() {
    let root = tempfile::tempdir().unwrap();
    let project = root.path().join("project");
    fs::create_dir_all(project.join("__pycache__")).unwrap();
    fs::write(project.join("__pycache__/sample.pyc"), b"cache").unwrap();
    let output = root.path().join("cleanup-output");
    let (code, stdout, _) = invoke(&[
        "--root",
        text(&project),
        "--min-age-days",
        "0",
        "--output-dir",
        text(&output),
        "--apply",
    ]);
    assert_eq!(code, 0, "{stdout}");
    let runs: Vec<_> = fs::read_dir(output.join("quarantine"))
        .unwrap()
        .flatten()
        .map(|entry| entry.path())
        .collect();
    assert_eq!(runs.len(), 1);
    assert!(runs[0]
        .file_name()
        .unwrap()
        .to_str()
        .unwrap()
        .starts_with("cache-cleanup-"));
    assert!(runs[0].join(QUARANTINE_MARKER).is_file());
    assert!(!project.join("__pycache__").exists());

    let (code, stdout, _) = invoke(&[
        "--output-dir",
        text(&output),
        "--purge-quarantine",
        "--older-than-days",
        "0",
    ]);
    assert_eq!(code, 0);
    assert_eq!(
        serde_json::from_str::<Value>(&stdout).unwrap()["removed_runs"],
        1
    );
    assert!(!runs[0].exists());
}

#[test]
fn batches_from_the_python_tool_stay_purgeable() {
    let root = tempfile::tempdir().unwrap();
    let run_directory = root.path().join("quarantine/cache-cleanup-legacy");
    fs::create_dir_all(&run_directory).unwrap();
    fs::write(
        run_directory.join(QUARANTINE_MARKER),
        r#"{"schema_version": 1, "tool": "my-py-tools.cleanup_work_artifacts"}"#,
    )
    .unwrap();
    let (code, stdout, _) = invoke(&[
        "--output-dir",
        text(root.path()),
        "--purge-quarantine",
        "--older-than-days",
        "0",
    ]);
    assert_eq!(code, 0);
    assert_eq!(
        serde_json::from_str::<Value>(&stdout).unwrap()["removed_runs"],
        1
    );
}

#[test]
fn invalid_days_and_filesystem_roots_exit_2() {
    assert_eq!(invoke(&["--min-age-days", "nan"]).0, 2);
    assert_eq!(invoke(&["--older-than-days", "365001"]).0, 2);
    let output = tempfile::tempdir().unwrap();
    let (code, _, stderr) = invoke(&["--root", "/", "--output-dir", text(output.path())]);
    assert_eq!(code, 2);
    assert!(stderr.contains("filesystem root"), "{stderr}");
}

#[test]
fn timestamps_match_python_isoformat() {
    let whole = SystemTime::UNIX_EPOCH + Duration::from_secs(1_600_000_000);
    assert_eq!(utc_iso(whole), "2020-09-13T12:26:40+00:00");
    assert_eq!(
        utc_iso(whole + Duration::from_micros(42)),
        "2020-09-13T12:26:40.000042+00:00"
    );
}
