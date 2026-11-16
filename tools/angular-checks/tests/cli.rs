use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicUsize, Ordering};

static NEXT: AtomicUsize = AtomicUsize::new(0);

struct Fixture(PathBuf);
impl Fixture {
    fn new() -> Self {
        let root = std::env::temp_dir().join(format!(
            "angular-checks-test-{}-{}",
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
    fn run(&self, args: &[&str]) -> Output {
        Command::new(env!("CARGO_BIN_EXE_angular-checks"))
            .args(args)
            .arg("--root")
            .arg(&self.0)
            .output()
            .unwrap()
    }
    /// Runs with `--format json` into a new folder and returns the full result with the exit code.
    fn json(&self, args: &[&str]) -> (Value, i32) {
        let out = std::env::temp_dir().join(format!(
            "angular-checks-out-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        let mut command = Command::new(env!("CARGO_BIN_EXE_angular-checks"));
        command.args(args);
        if !args.contains(&"--json") {
            command.arg("--json");
        }
        let output = command
            .arg("--root")
            .arg(&self.0)
            .arg("--out")
            .arg(&out)
            .output()
            .unwrap();
        let value = serde_json::from_slice(&fs::read(out.join("report.json")).unwrap_or_default())
            .unwrap_or_else(|_| {
                panic!(
                    "no report: {} {}",
                    String::from_utf8_lossy(&output.stdout),
                    String::from_utf8_lossy(&output.stderr)
                )
            });
        let _ = fs::remove_dir_all(out);
        (value, output.status.code().unwrap())
    }
}
/// Removes the folder a default run created and returns what it printed.
fn printed(output: &Output) -> String {
    let text = String::from_utf8_lossy(&output.stdout).into_owned();
    for line in text.lines() {
        if let Some(path) = line.strip_prefix("report: ") {
            let _ = fs::remove_dir_all(Path::new(path).parent().unwrap());
        }
    }
    text
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn workspace() -> Fixture {
    let fixture = Fixture::new();
    fixture.put("nx.json", "{}");
    fixture.put(
        "apps/demo/project.json",
        r#"{"name":"demo","sourceRoot":"apps/demo/src"}"#,
    );
    fixture.put(
        "apps/demo/src/demo.component.ts",
        "/** License header */\nimport { Component } from '@angular/core';\n\n/**\n * Shows the demo form\n * @deprecated\n */\n@Component({\n  selector: 'app-demo',\n  standalone: true,\n  templateUrl: './demo.component.html',\n  styleUrls: ['./demo.component.scss', \"../shared.scss\"],\n})\nexport class DemoComponent {\n  form = this.fb.group({ customerId: [''], 'note': new FormControl<string>(''), amount: this.fb.control(0) });\n}\n",
    );
    fixture.put(
        "apps/demo/src/demo.component.html",
        r#"<input formControlName="customerId"><input formControlName='extra'>"#,
    );
    fixture.put(
        "packages/widgets/project.json",
        r#"{"sourceRoot":"packages/widgets"}"#,
    );
    fixture.put(
        "packages/widgets/widgets.ts",
        "@Component({selector: \"app-one\", styleUrl: './one.css'})\nexport class OneComponent {}\n\n@Component({selector: 'app-two'})\nexport class HTTPStatus2PanelComponent {}\n",
    );
    fixture.put(
        "apps/demo/src/component-mapping.ts",
        "import { OneComponent, HTTPStatus2PanelComponent as Panel } from '../../../packages/widgets/widgets';\nexport const mapping = [{ selector: 'ce-one', component: OneComponent }, { selector: \"ce-panel\", component: Panel }];\n",
    );
    fixture.put(
        "packages/widgets/skip.spec.ts",
        "@Component({}) export class SpecComponent {}",
    );
    fixture.put(
        "node_modules/x/x.ts",
        "@Component({}) export class VendorComponent {}",
    );
    fixture.put("packages/project.json", "not json");
    fixture
}

fn by_class<'a>(payload: &'a Value, class: &str) -> &'a Value {
    payload["components"]
        .as_array()
        .unwrap()
        .iter()
        .find(|item| item["class_name"] == class)
        .unwrap_or_else(|| panic!("{class} missing"))
}

#[test]
fn inventory_maps_components_to_companions_projects_and_custom_elements() {
    let fixture = workspace();
    let (payload, code) = fixture.json(&["components", "--json"]);
    assert_eq!(code, 0);
    assert_eq!(payload["count"], 3);
    assert_eq!(payload["warnings"].as_array().unwrap().len(), 1);
    let demo = by_class(&payload, "DemoComponent");
    assert_eq!(demo["project"], "demo");
    assert_eq!(demo["selector"], "app-demo");
    assert_eq!(demo["source"], "apps/demo/src/demo.component.ts");
    assert_eq!(demo["project_relative"], "src/demo.component.ts");
    assert_eq!(demo["template"], "apps/demo/src/demo.component.html");
    assert_eq!(
        demo["styles"],
        json!(["apps/demo/src/demo.component.scss", "apps/demo/shared.scss"])
    );
    assert_eq!(demo["standalone"], true);
    // Only the block directly above the decorator describes the component
    assert_eq!(demo["description"], "Shows the demo form");
    let one = by_class(&payload, "OneComponent");
    assert_eq!(one["project"], "widgets");
    assert_eq!(one["custom_elements"], json!(["ce-one"]));
    assert_eq!(one["styles"], json!(["packages/widgets/one.css"]));
    assert_eq!(one["template"], Value::Null);
    let panel = by_class(&payload, "HTTPStatus2PanelComponent");
    assert_eq!(panel["custom_elements"], json!(["ce-panel"]));
    assert_eq!(panel["description"], "HTTPStatus2 Panel");

    // Query terms, project filter and limit narrow the list; no result exits with 1
    let (filtered, _) = fixture.json(&["components", "app-", "--project", "WIDGETS", "--json"]);
    assert_eq!(filtered["count"], 2);
    let limited = fixture.run(&["components", "--limit", "1"]);
    let text = printed(&limited);
    // One summary line and the report path, whatever the number of components
    assert!(text.starts_with("components: 3 found in 2 projects, 1 in the report; standalone 1, custom elements 2, warnings 1\nreport: "));
    assert_eq!(text.lines().count(), 2);
    assert!(String::from_utf8_lossy(&limited.stderr).contains("2 more result(s)"));
    assert_eq!(
        fixture
            .run(&["components", "nothing-matches"])
            .status
            .code(),
        Some(1)
    );
    assert_eq!(
        fixture.run(&["components", "--limit", "-1"]).status.code(),
        Some(2)
    );
    let not_nx = Fixture::new();
    let output = not_nx.run(&["components"]);
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("not an Nx workspace root"));
}

fn git(root: &Path, args: &[&str]) {
    assert!(Command::new("git")
        .arg("-C")
        .arg(root)
        .args(args)
        .output()
        .unwrap()
        .status
        .success());
}

#[test]
fn changed_filter_and_change_impact_read_git_state() {
    let fixture = workspace();
    git(&fixture.0, &["init", "--quiet"]);
    git(
        &fixture.0,
        &[
            "add",
            "nx.json",
            "apps/demo/project.json",
            "apps/demo/src/demo.component.ts",
        ],
    );
    git(
        &fixture.0,
        &[
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "init",
        ],
    );
    // Untracked template and mapping: the demo component and the registered elements count as changed
    let (payload, _) = fixture.json(&["components", "--changed", "--json", "--limit", "0"]);
    assert_eq!(payload["count"], 3);
    git(&fixture.0, &["add", "-A"]);
    git(
        &fixture.0,
        &[
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "all",
        ],
    );
    assert_eq!(
        fixture.run(&["components", "--changed"]).status.code(),
        Some(1)
    );

    fixture.put(
        "apps/demo/src/demo.component.ts",
        "@Input() value = '';\n@Component({selector: 'x'})\nexport class DemoComponent {}\n",
    );
    fixture.put("notes.txt", "selector: ignored for this extension");
    fs::remove_file(fixture.0.join("packages/widgets/widgets.ts")).unwrap();
    let (impact, code) = fixture.json(&["change-impact"]);
    assert_eq!(code, 0);
    let files = impact["changed_files"].as_array().unwrap();
    let row = |path: &str| files.iter().find(|row| row["path"] == path).unwrap();
    assert_eq!(
        row("apps/demo/src/demo.component.ts")["public_contract_markers"],
        json!(["selector:", "@Input"])
    );
    assert_eq!(row("notes.txt")["public_contract_markers"], json!([]));
    assert_eq!(row("packages/widgets/widgets.ts")["exists"], false);
}

#[test]
fn form_contract_reports_each_mismatch() {
    let fixture = workspace();
    fixture.put(
        "contract.json",
        "\u{feff}{\"components\":[{\"source\":\"apps/demo/src/demo.component.ts\",\"template\":\"apps/demo/src/demo.component.html\",\"controls\":[\"customerId\",\"note\",\"amount\",\"missing\"]},{\"source\":\"nope.ts\",\"controls\":[\"a\"]},{\"source\":\"packages/widgets/widgets.ts\",\"template\":\"gone.html\"}]}",
    );
    let (payload, code) = fixture.json(&[
        "form-contract",
        "--contract",
        fixture.0.join("contract.json").to_str().unwrap(),
        "--json",
    ]);
    assert_eq!(code, 1);
    assert_eq!(payload["checked_components"], 3);
    let found: Vec<(String, String)> = payload["findings"]
        .as_array()
        .unwrap()
        .iter()
        .map(|item| {
            (
                item["kind"].as_str().unwrap().to_owned(),
                item["control"].as_str().unwrap().to_owned(),
            )
        })
        .collect();
    let expect = |kind: &str, control: &str| (kind.to_owned(), control.to_owned());
    assert_eq!(
        found,
        vec![
            expect("missing-template-control", "note"),
            expect("missing-template-control", "amount"),
            expect("missing-source-control", "missing"),
            expect("missing-template-control", "missing"),
            expect("template-control-without-source", "extra"),
            expect("missing-source", ""),
            expect("missing-template", ""),
        ]
    );
    fixture.put(
        "ok.json",
        r#"{"components":[{"source":"apps/demo/src/demo.component.ts","controls":["customerId","note","amount"]}]}"#,
    );
    let ok = fixture.run(&[
        "form-contract",
        "--contract",
        fixture.0.join("ok.json").to_str().unwrap(),
    ]);
    assert_eq!(ok.status.code(), Some(0));
    assert!(printed(&ok).starts_with("form contract: OK, 1 components checked\nreport: "));
    let failing = fixture.run(&[
        "form-contract",
        "--contract",
        fixture.0.join("contract.json").to_str().unwrap(),
    ]);
    assert_eq!(failing.status.code(), Some(1));
    let text = printed(&failing);
    assert!(text.starts_with("form contract: 7 findings in 3 components\n"));
    assert!(
        text.contains("missing-template-control 3; first apps/demo/src/demo.component.ts note\n")
    );
    fixture.put("bad.json", r#"{"components":[{"controls":[]}]}"#);
    let bad = fixture.run(&[
        "form-contract",
        "--contract",
        fixture.0.join("bad.json").to_str().unwrap(),
    ]);
    assert_eq!(bad.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&bad.stderr).contains("needs a source path"));
}

#[test]
fn generator_preflight_finds_existing_names() {
    let fixture = workspace();
    let (payload, code) = fixture.json(&[
        "generator-preflight",
        "--identifier",
        " onecomponent ",
        "--selector",
        "app-demo",
    ]);
    assert_eq!(code, 1);
    assert_eq!(
        payload["collisions"]["identifier"],
        json!([
            "apps/demo/src/component-mapping.ts",
            "packages/widgets/widgets.ts"
        ])
    );
    assert_eq!(
        payload["collisions"]["selector"],
        json!(["apps/demo/src/demo.component.ts"])
    );
    assert_eq!(payload["proposed"]["identifier"], "onecomponent");
    let allowed = fixture.run(&[
        "generator-preflight",
        "--identifier",
        "OneComponent",
        "--allow-existing",
    ]);
    assert_eq!(allowed.status.code(), Some(0));
    assert!(printed(&allowed).starts_with(
        "generator preflight: names already exist\nidentifier \"OneComponent\" in 2 files\nselector not checked\nreport: "
    ));
    let (clear, code) = fixture.json(&["generator-preflight", "--identifier", "ZZZ9"]);
    assert_eq!((code, &clear["collisions"]), (0, &json!({})));
    assert_eq!(clear["proposed"]["selector"], Value::Null);
    let empty = fixture.run(&["generator-preflight", "--identifier", " "]);
    assert_eq!(empty.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&empty.stderr).contains("must not be empty"));
    assert_eq!(
        fixture
            .run(&["generator-preflight", "--identifier", "x", "--selector", ""])
            .status
            .code(),
        Some(2)
    );
}

#[test]
fn report_formats_go_to_a_new_folder_outside_the_root() {
    let fixture = workspace();
    let outputs = Fixture::new();
    let out = outputs.0.join("components");
    let output = fixture.run(&[
        "components",
        "--format",
        "all",
        "--out",
        out.to_str().unwrap(),
    ]);
    assert_eq!(output.status.code(), Some(0));
    let text = String::from_utf8_lossy(&output.stdout).into_owned();
    let files: Vec<&str> = text
        .lines()
        .filter_map(|line| line.strip_prefix("report: "))
        .map(|path| {
            std::path::Path::new(path)
                .file_name()
                .unwrap()
                .to_str()
                .unwrap()
        })
        .collect();
    assert_eq!(files, ["report.json", "report.md", "report.html"]);
    let saved: Value = serde_json::from_slice(&fs::read(out.join("report.json")).unwrap()).unwrap();
    assert_eq!(saved["count"], 3);
    let markdown = fs::read_to_string(out.join("report.md")).unwrap();
    assert!(
        markdown.starts_with("# Angular 元件盤點")
            && markdown.contains("| demo | DemoComponent | app-demo |")
    );
    let page = fs::read_to_string(out.join("report.html")).unwrap();
    assert!(
        page.contains("wb-workbench") && page.contains("<code>HTTPStatus2PanelComponent</code>")
    );
    // The exit code still reports the check result when files are written
    let contract = fixture.0.join("contract.json");
    fs::write(&contract, r#"{"components":[{"source":"nope.ts"}]}"#).unwrap();
    let failing = fixture.run(&[
        "form-contract",
        "--contract",
        contract.to_str().unwrap(),
        "--format",
        "html",
        "--out",
        outputs.0.join("form").to_str().unwrap(),
    ]);
    assert_eq!(failing.status.code(), Some(1));
    assert!(fs::read_to_string(outputs.0.join("form/report.html"))
        .unwrap()
        .contains("找不到原始檔"));
    assert_eq!(
        fixture
            .run(&[
                "change-impact",
                "--format",
                "html",
                "--out",
                fixture.0.join("inside").to_str().unwrap()
            ])
            .status
            .code(),
        Some(2)
    );
    assert_eq!(
        fixture
            .run(&["components", "--format", "pdf"])
            .status
            .code(),
        Some(2)
    );
    assert_eq!(
        fixture
            .run(&["components", "--json", "--format", "md"])
            .status
            .code(),
        Some(2)
    );
    assert_eq!(
        fixture.run(&["components", "--unknown"]).status.code(),
        Some(2)
    );
}

#[test]
fn separator_repeated_options_and_missing_repository_are_reported() {
    let fixture = workspace();
    fixture.put(
        "apps/demo/src/dash.component.ts",
        "/** Shows --wide layout */\n@Component({selector: 'app-dash'})\nexport class DashComponent {}\n",
    );
    // After the separator a term may start with dashes
    let found = fixture.0.join("separator-out");
    let output = Command::new(env!("CARGO_BIN_EXE_angular-checks"))
        .args(["components", "--json", "--root"])
        .arg(&fixture.0)
        .arg("--out")
        .arg(std::env::temp_dir().join(format!("angular-checks-sep-{}", std::process::id())))
        .args(["--", "--wide"])
        .output()
        .unwrap();
    let _ = found;
    let folder = std::env::temp_dir().join(format!("angular-checks-sep-{}", std::process::id()));
    let payload: Value =
        serde_json::from_slice(&fs::read(folder.join("report.json")).unwrap()).unwrap();
    fs::remove_dir_all(folder).unwrap();
    assert_eq!(
        (output.status.code(), &payload["count"]),
        (Some(0), &json!(1))
    );
    assert_eq!(payload["components"][0]["class_name"], "DashComponent");
    let twice = fixture.run(&["components", "--project", "demo", "--project", "widgets"]);
    assert_eq!(twice.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&twice.stderr).contains("--project is given more than once"));
    for args in [&["components", "--changed"][..], &["change-impact"][..]] {
        let output = fixture.run(args);
        assert_eq!(output.status.code(), Some(2));
        assert!(String::from_utf8_lossy(&output.stderr).contains("Not a Git repository"));
    }
}
