//! Synthetic fixtures only; never import application code or install dependencies.
//! Review cases need TYPESCRIPT_PATH (an approved installed TypeScript JS API); the template case
//! also needs ANGULAR_COMPILER_PATH. Without them those cases report a skip and pass.
use angular_checks::maintainability::bounded;
use serde_json::Value;
use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;
use std::process::Command;

const BIN: &str = env!("CARGO_BIN_EXE_angular-checks");

struct Fixture {
    _temp: tempfile::TempDir,
    home: PathBuf,
    root: PathBuf,
    report: PathBuf,
}

fn typescript() -> Option<String> {
    let value = std::env::var("TYPESCRIPT_PATH")
        .ok()
        .filter(|value| !value.is_empty());
    if value.is_none() {
        eprintln!("skipped: set TYPESCRIPT_PATH to an approved installed dependency");
    }
    value
}

impl Fixture {
    fn new() -> Self {
        let temp = tempfile::tempdir().unwrap();
        let home = fs::canonicalize(temp.path()).unwrap();
        let root = home.join("input");
        fs::create_dir(&root).unwrap();
        let report = home.join("report.json");
        Self {
            _temp: temp,
            home,
            root,
            report,
        }
    }

    fn write(&self, name: &str, text: &str) -> PathBuf {
        let path = self.root.join(name);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(&path, text).unwrap();
        path
    }

    fn snapshot(&self) -> BTreeMap<PathBuf, Vec<u8>> {
        let mut files = BTreeMap::new();
        let mut pending = vec![self.root.clone()];
        while let Some(current) = pending.pop() {
            for entry in fs::read_dir(&current).unwrap().flatten() {
                if entry.file_type().unwrap().is_dir() {
                    pending.push(entry.path());
                } else {
                    files.insert(entry.path(), fs::read(entry.path()).unwrap());
                }
            }
        }
        files
    }

    fn command(&self, typescript: &str, mode: &str, extra: &[&str]) -> (i32, String) {
        let output = Command::new(BIN)
            .args(["maintainability", "--root"])
            .arg(&self.root)
            .args([
                "--scope",
                ".",
                "--mode",
                mode,
                "--typescript",
                typescript,
                "--report",
            ])
            .arg(&self.report)
            .args(extra)
            .output()
            .unwrap();
        (
            output.status.code().unwrap(),
            String::from_utf8_lossy(&output.stderr).into_owned(),
        )
    }

    /// Runs a files-mode review; later options override earlier ones only where the CLI allows it.
    fn review(
        &self,
        typescript: &str,
        files: &[&str],
        extra: &[&str],
        profile: Option<&str>,
    ) -> Value {
        let mut args: Vec<String> = Vec::new();
        for name in files {
            args.extend(["--file".into(), name.to_string()]);
        }
        if let Some(fields) = profile {
            let config = self.home.join("profile.json");
            fs::write(
                &config,
                format!(r#"{{"id": "synthetic", "version": "1"{fields}}}"#),
            )
            .unwrap();
            args.extend(["--profile".into(), config.to_string_lossy().into_owned()]);
        }
        args.extend(extra.iter().map(|arg| arg.to_string()));
        let before = self.snapshot();
        let output = Command::new(BIN)
            .args(["maintainability", "--root"])
            .arg(&self.root)
            .args(["--mode", "files", "--report"])
            .arg(&self.report)
            .args(if extra.contains(&"--scope") {
                vec![]
            } else {
                vec!["--scope", "."]
            })
            .args(if extra.contains(&"--typescript") {
                vec![]
            } else {
                vec!["--typescript", typescript]
            })
            .args(&args)
            .output()
            .unwrap();
        assert_eq!(before, self.snapshot(), "sources must stay unchanged");
        assert!(
            self.report.exists(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let report: Value =
            serde_json::from_str(&fs::read_to_string(&self.report).unwrap()).unwrap();
        assert_eq!(
            Some(output.status.code().unwrap() as i64),
            report["exitCode"].as_i64()
        );
        report
    }
}

fn rows(report: &Value) -> &Vec<Value> {
    report["results"].as_array().unwrap()
}

fn rule<'a>(report: &'a Value, id: &str) -> Option<&'a Value> {
    rows(report).iter().find(|row| row["ruleId"] == id)
}

fn has(report: &Value, id: &str, status: &str) -> bool {
    rows(report)
        .iter()
        .any(|row| row["ruleId"] == id && row["status"] == status)
}

#[test]
fn boundaries() {
    let fixture = Fixture::new();
    assert!(bounded(&fixture.root, "../outside.ts").is_err());
    assert_eq!(
        bounded(&fixture.root, "inside.ts").unwrap(),
        fixture.root.join("inside.ts")
    );
}

#[test]
fn static_candidates_do_not_copy_literals_or_infer_orphans() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write("a.ts", r#"import {A} from "./dep"; import type {B} from "./dep"; class Item { ngOnInit() {} run(x: any) { return this.other(x); } other(x: unknown) { return x; } } const secret = "PRIVATE_SENTINEL";"#);
    let report = fixture.review(&ts, &["a.ts"], &[], None);
    for id in ["IMPORT.DUPLICATE", "TYPE.EXPLICIT_ANY", "CHAIN.FORWARD"] {
        assert!(rule(&report, id).is_some(), "{id}");
    }
    assert!(!fs::read_to_string(&fixture.report)
        .unwrap()
        .contains("PRIVATE_SENTINEL"));
    assert_eq!(report["complete"], false);
    assert_eq!(
        rule(&report, "ORPHAN.CONSUMERS").unwrap()["status"],
        "MANUAL"
    );
    assert!(rule(&report, "MEMBER.VISIBILITY").is_none());
}

#[test]
fn parse_failure_keeps_independent_files() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write("broken.ts", "class Broken { constructor(");
    fixture.write("valid.ts", "const data: any = 0;");
    let report = fixture.review(&ts, &["broken.ts", "valid.ts"], &[], None);
    assert_eq!(report["exitCode"], 1);
    assert!(rows(&report)
        .iter()
        .any(|row| row["path"] == "valid.ts" && row["ruleId"] == "TYPE.EXPLICIT_ANY"));
}

#[test]
fn profile_visibility_includes_parameter_properties() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write(
        "a.ts",
        "class Model { constructor(readonly value: string) {} }",
    );
    let report = fixture.review(&ts, &["a.ts"], &[], Some(r#", "explicitPublic": true"#));
    assert_eq!(
        rows(&report)
            .iter()
            .filter(|row| row["ruleId"] == "MEMBER.VISIBILITY")
            .count(),
        2
    );
}

#[test]
fn symbol_reference_and_index_only_keys() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write("a.ts", r#"export {}; const item: {title: string} = {title:"x"}; console.log(item["title"]); const data: Record<string,string> = {}; console.log(data["key"], data["99"]); function run(arg) { return arg; }"#);
    let profile =
        r#", "compilerOptions": {"noPropertyAccessFromIndexSignature": true, "target": "ES2022"}"#;
    let report = fixture.review(&ts, &["a.ts"], &["--depth", "semantic"], Some(profile));
    assert_eq!(
        rows(&report)
            .iter()
            .filter(|row| row["ruleId"] == "TYPE.DOT_CANDIDATE")
            .count(),
        1
    );
    assert!(rule(&report, "TYPE.INFERRED_ANY").is_some());
}

#[test]
fn missing_dependency_is_not_semantic_pass() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write(
        "a.ts",
        r#"import { missing } from "./absent"; export const value = missing();"#,
    );
    let report = fixture.review(&ts, &["a.ts"], &["--depth", "semantic"], None);
    assert_eq!(rule(&report, "TYPE.COVERAGE").unwrap()["status"], "SKIP");
}

#[test]
fn approved_dependency_is_read_not_report_scope() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write(
        "a.ts",
        r#"import {value} from "./dep"; export const result = value;"#,
    );
    fixture.write("dep.ts", "export const value: any = 1;");
    let report = fixture.review(
        &ts,
        &["a.ts"],
        &["--depth", "semantic", "--dependency", "dep.ts"],
        None,
    );
    assert!(report["inputs"].get("dep.ts").is_some());
    assert!(!rows(&report).iter().any(|row| row["path"] == "dep.ts"));
}

#[test]
fn missing_typescript_and_html_continue_independently() {
    let Some(_) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write("a.ts", "export const value = 1;");
    fixture.write("a.html", "<p>{{ value }}</p>");
    let absent = fixture
        .home
        .join("absent.cjs")
        .to_string_lossy()
        .into_owned();
    let report = fixture.review(&absent, &["a.ts", "a.html"], &[], None);
    assert_eq!(report["exitCode"], 2);
    assert!(has(&report, "HTML.PARSE", "SKIP"));
}

#[test]
fn runtime_does_not_execute_target() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write("a.ts", r#"throw new Error("do not execute");"#);
    let report = fixture.review(&ts, &["a.ts"], &["--depth", "runtime"], None);
    assert_eq!(report["coverage"]["runtimeExecuted"], false);
    assert!(has(&report, "PERF.RUNTIME", "SKIP"));
}

#[test]
fn scope_escape_fails_closed() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write("a.ts", "");
    let report = fixture.review(&ts, &["a.ts"], &["--scope", "../"], None);
    assert_eq!(report["exitCode"], 2);
    assert!(report.get("coverage").is_none());
}

#[test]
fn report_overwrite_is_rejected() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write("a.ts", "");
    fixture.review(&ts, &["a.ts"], &[], None);
    let original = fs::read(&fixture.report).unwrap();
    assert_eq!(fixture.command(&ts, "module", &[]).0, 2);
    assert_eq!(original, fs::read(&fixture.report).unwrap());
}

#[test]
fn report_inside_root_is_rejected_before_writing() {
    let fixture = Fixture::new();
    let inside = fixture.root.join("report.json");
    let output = Command::new(BIN)
        .args(["maintainability", "--root"])
        .arg(&fixture.root)
        .args([
            "--scope",
            ".",
            "--mode",
            "module",
            "--typescript",
            "absent.js",
            "--report",
        ])
        .arg(&inside)
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(!inside.exists());
}

#[test]
fn selected_cycle_is_candidate_not_runtime_failure() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write(
        "a.ts",
        r#"import type {B} from "./b"; export interface A { b?: B; }"#,
    );
    fixture.write(
        "b.ts",
        r#"import type {A} from "./a"; export interface B { a?: A; }"#,
    );
    let report = fixture.review(&ts, &["a.ts", "b.ts"], &["--depth", "semantic"], None);
    assert!(has(&report, "IMPORT.CYCLE", "WARN"));
}

#[test]
fn formatter_noop_is_pass() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write("a.ts", "const value = 1;\n");
    let report = fixture.review(
        &ts,
        &["a.ts"],
        &[],
        Some(r#", "format": {"indentSize": 2, "semicolons": "insert"}"#),
    );
    assert_eq!(rule(&report, "FORMAT.EFFECTIVE").unwrap()["status"], "PASS");
}

#[test]
fn diff_literal_scope_never_scans_sibling() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write("selected/a.ts", "const value = 1;");
    fixture.write("sibling/secret.ts", "const value: any = 1;");
    assert!(Command::new("git")
        .args(["init", "-q"])
        .arg(&fixture.root)
        .status()
        .unwrap()
        .success());
    let output = Command::new(BIN)
        .args(["maintainability", "--root"])
        .arg(&fixture.root)
        .args([
            "--scope",
            "selected",
            "--mode",
            "diff",
            "--untracked",
            "--typescript",
            &ts,
            "--report",
        ])
        .arg(&fixture.report)
        .output()
        .unwrap();
    assert_eq!(
        output.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let report: Value =
        serde_json::from_str(&fs::read_to_string(&fixture.report).unwrap()).unwrap();
    assert_eq!(
        report["inputs"]
            .as_object()
            .unwrap()
            .keys()
            .collect::<Vec<_>>(),
        ["selected/a.ts"]
    );
}

#[test]
fn module_selection_excludes_dependencies_and_outputs() {
    let Some(ts) = typescript() else { return };
    let fixture = Fixture::new();
    fixture.write("a.ts", "export {};");
    fixture.write("node_modules/secret.ts", "const hidden: any = 1;");
    fixture.write("dist/output.ts", "const hidden: any = 1;");
    assert_eq!(fixture.command(&ts, "module", &[]).0, 0);
    let report: Value =
        serde_json::from_str(&fs::read_to_string(&fixture.report).unwrap()).unwrap();
    assert_eq!(
        report["inputs"]
            .as_object()
            .unwrap()
            .keys()
            .collect::<Vec<_>>(),
        ["a.ts"]
    );
}

/// A stand-in worker changes the reviewed file, so the receipt must be invalidated.
#[cfg(unix)]
#[test]
fn stale_snapshot_detected_without_executing_target() {
    use std::os::unix::fs::PermissionsExt;
    let fixture = Fixture::new();
    let target = fixture.write("a.ts", "export {};");
    let node = fixture.home.join("fake-node");
    let script = format!("#!/bin/sh\ncat >/dev/null\nprintf 'export const changed = true;' > '{}'\nprintf '{{\"results\": []}}'\n", target.display());
    fs::write(&node, script).unwrap();
    fs::set_permissions(&node, fs::Permissions::from_mode(0o755)).unwrap();
    let (code, stderr) = fixture.command(
        "unused.js",
        "files",
        &["--file", "a.ts", "--node", node.to_str().unwrap()],
    );
    assert_eq!(code, 2, "{stderr}");
    let report: Value =
        serde_json::from_str(&fs::read_to_string(&fixture.report).unwrap()).unwrap();
    assert_ne!(report["inputsUnchanged"], true);
    assert!(rule(&report, "TOOL.INPUT").unwrap()["evidence"]
        .as_str()
        .unwrap()
        .contains("Inputs changed"));
}

#[test]
fn template_ast_any_and_dynamic_event_are_candidates() {
    let Some(ts) = typescript() else { return };
    let Some(compiler) = std::env::var("ANGULAR_COMPILER_PATH")
        .ok()
        .filter(|value| !value.is_empty())
    else {
        eprintln!("skipped: optional approved Angular compiler required");
        return;
    };
    let fixture = Fixture::new();
    fixture.write(
        "a.html",
        r#"<button (click)="open()">{{ $any(value).name }}</button>"#,
    );
    let report = fixture.review(&ts, &["a.html"], &["--angular-compiler", &compiler], None);
    assert!(rule(&report, "HTML.ANY").is_some());
    assert!(rule(&report, "PERF.TEMPLATE_CALL").is_some());
    assert_eq!(report["coverage"]["templateTypeCheck"], false);
}
