use code_health::{html, markdown, scan, Check, Options, RetainedRange, Style};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};

static NEXT: AtomicUsize = AtomicUsize::new(0);

struct Fixture(PathBuf);
impl Fixture {
    fn new() -> Self {
        let root = std::env::temp_dir().join(format!(
            "code-health-test-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        Self(root)
    }
    fn put(&self, name: &str, contents: &str) {
        let path = self.0.join(name);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, contents).unwrap();
    }
    fn options(&self) -> Options {
        Options::new(&self.0)
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn rows<'a>(report: &'a Value, section: &str) -> &'a Vec<Value> {
    report[section].as_array().unwrap()
}

#[test]
fn resolves_entries_aliases_barrels_and_file_local_exports() {
    let fixture = Fixture::new();
    fixture.put(
        "tsconfig.base.json",
        r#"{"compilerOptions":{"baseUrl":".","paths":{"@lib/*":["missing/*","lib/*",],},},}"#,
    );
    fixture.put(
        "tsconfig.json",
        r#"{// Read the shared aliases.
        "extends": "./tsconfig.base.json", "files": ["src/main.ts",], }"#,
    );
    fixture.put(
        "apps/panel/project.json",
        r#"{"targets":{"build":{"options":{"main":"apps/panel/bootstrap.ts"}}}}"#,
    );
    fixture.put("apps/panel/bootstrap.ts", "import '../../side';");
    fixture.put("side.ts", "export const side = 1;");
    fixture.put("src/main.ts", "import { used as alias } from '@lib/index';\nimport type { Row } from '@lib/index';\nconsole.log(alias);\nlet row: Row;");
    fixture.put(
        "lib/index.ts",
        "export * from './inner'; export { Row } from './types';",
    );
    fixture.put("lib/inner/index.ts", "export * from './model';");
    fixture.put("lib/inner/model.ts", "export const used = 1;\nexport const local = used + 1;\nconst result = local + 1;\nexport default function unusedDefault() {}");
    fixture.put(
        "lib/types.ts",
        "export interface Row { id: number }\nexport interface Unused { id: number }",
    );
    fixture.put("orphan.ts", "export const absent = 2;");
    let report = scan(&fixture.options()).unwrap();
    assert_eq!(
        report["entry_points"],
        json!(["apps/panel/bootstrap.ts", "src/main.ts"])
    );
    assert_eq!(report["partial"], false, "{report}");
    let unused = rows(&report, "unused");
    assert!(unused
        .iter()
        .any(|row| row["kind"] == "file" && row["path"] == "orphan.ts"));
    assert!(unused
        .iter()
        .any(|row| row["kind"] == "export" && row["name"] == "local" && row["local_use"] == true));
    assert!(unused
        .iter()
        .any(|row| row["kind"] == "export" && row["name"] == "default"));
    assert!(unused
        .iter()
        .any(|row| row["kind"] == "export" && row["name"] == "Unused"));
    assert!(
        !unused.iter().any(|row| row["name"] == "used"
            || row["name"] == "Row"
            || (row["kind"] == "file" && row["path"] == "side.ts")),
        "{unused:?}"
    );
}

#[test]
fn uses_template_references_and_retains_uncertain_runtime_consumers() {
    let fixture = Fixture::new();
    fixture.put("main.ts", "import { Panel } from './panel';\nconsole.log(Panel);\nimport('./lazy');\nimport('./' + key);\n");
    fixture.put("lazy.ts", "export function load() { return 1; }");
    fixture.put("panel.ts", "@Component({ templateUrl: './view.html' })\nexport class Panel {\n  public select() {}\n  public mode = true;\n  public decoratedCallback() {}\n  @Input() public source = '';\n  private active() {}\n  private spare() {}\n  public start() { this.active(); }\n}\n");
    fixture.put(
        "view.html",
        "<button (click)=\"select()\" [disabled]=\"mode\">{{ mode }}</button>",
    );
    fixture.put("dynamic.ts", "export class Uncertain { public command() {} private unknown() {} run(key: string) { this[key](); } }");
    let mut options = fixture.options();
    options.entries.push("main.ts".into());
    let report = scan(&options).unwrap();
    let unused = rows(&report, "unused");
    assert!(
        unused
            .iter()
            .any(|row| row["name"] == "spare" && row["visibility"] == "private"),
        "{report}"
    );
    assert!(!unused.iter().any(|row| [
        "select",
        "mode",
        "active",
        "load",
        "decoratedCallback",
        "unknown",
        "source"
    ]
    .contains(&row["name"].as_str().unwrap_or(""))));
    let review = rows(&report, "needs_review");
    assert!(review
        .iter()
        .any(|row| row["path"] == "main.ts" && row["line"] == 4));
    assert!(review
        .iter()
        .any(|row| row["symbol"] == "decoratedCallback"));
    assert!(review.iter().any(|row| row["symbol"] == "unknown"));
}

#[test]
fn finds_renamed_duplicates_and_counts_functions_outside_retained_scopes() {
    let fixture = Fixture::new();
    let first = "export function sum(items) {\n  let total = 0;\n  for (const value of items) {\n    if (value && value.ok) total += value.count;\n  }\n  return total;\n}\n";
    let second = "export function gather(records) {\n  let result = 0;\n  for (const row of records) {\n    if (row && row.ready) result += row.size;\n  }\n  return result;\n}\n";
    fixture.put("first.ts", first);
    fixture.put("second.js", second);
    fixture.put("third.ts", &format!("/** retain-this-fixture */\n{second}"));
    fixture.put(
        "first.html",
        "<section class=\"example\"><p>{{ value }}</p></section>",
    );
    fixture.put(
        "second.html",
        "<section class=\"different\"><p>{{ value }}</p></section>",
    );
    fixture.put(
        "first.scss",
        ".example { color: red; padding: 12px; margin: 0; }",
    );
    fixture.put(
        "second.scss",
        ".example { color: red; padding: 18px; margin: 2; }",
    );
    fixture.put(
        "spans.ts",
        "function kept() { return false; }\nfunction other() { return !!true; }\n",
    );
    let mut options = fixture.options();
    options.entries.push("first.ts".into());
    options
        .marker_patterns
        .push("(?m)^/\\*\\* retain-this-fixture \\*/$".into());
    options.retained_ranges.push(RetainedRange {
        path: "spans.ts".into(),
        start_line: 1,
        end_line: 1,
    });
    options.min_tokens = 12;
    let report = scan(&options).unwrap();
    let duplicates = rows(&report, "duplicates");
    for (left, right) in [
        ("first.ts", "second.js"),
        ("first.html", "second.html"),
        ("first.scss", "second.scss"),
    ] {
        assert!(
            duplicates
                .iter()
                .any(|group| group["left"] == left && group["right"] == right),
            "{report}"
        );
    }
    assert!(!duplicates
        .iter()
        .any(|group| group["left"] == "third.ts" || group["right"] == "third.ts"));
    assert_eq!(rows(&report, "retained").len(), 2);
    assert!(rows(&report, "complexity")
        .iter()
        .any(|row| row["name"] == "sum" && row["branches"] == 3 && row["lines"] == 7));
    assert!(!rows(&report, "complexity")
        .iter()
        .any(|row| row["name"] == "kept" || row["path"] == "third.ts"));
    assert!(!rows(&report, "unused").iter().any(
        |row| row["path"] == "third.ts" || (row["path"] == "spans.ts" && row["kind"] == "file")
    ));
    assert!(markdown(&report).contains("first.ts:1-7"));
}

#[test]
fn reports_missing_entry_points_and_nested_function_counts() {
    let fixture = Fixture::new();
    fixture.put("file.ts", "export function outer() {\n  if (true) return () => a ? b : c;\n  const inner = () => { if (false) return; };\n  return inner;\n}\n");
    let report = scan(&fixture.options()).unwrap();
    assert!(!rows(&report, "unused")
        .iter()
        .any(|row| row["kind"] == "file" || row["kind"] == "export"));
    let functions = rows(&report, "complexity");
    assert_eq!(functions.len(), 3, "{functions:?}");
    assert!(
        functions.iter().all(|function| function["branches"] == 1),
        "{functions:?}"
    );
}

fn request(id: u32, method: &str, params: Value) -> String {
    json!({"jsonrpc":"2.0","id":id,"method":method,"params":params}).to_string()
}

#[test]
fn cli_and_stdio_share_the_same_scan_and_reject_outside_roots() {
    let fixture = Fixture::new();
    fixture.put("main.ts", "export const count = () => 1;");
    let outside = Fixture::new();
    let executable = env!("CARGO_BIN_EXE_code-health");
    let cli = Command::new(executable)
        .args(["scan", "--root"])
        .arg(&fixture.0)
        .args(["--checks", "complexity"])
        .output()
        .unwrap();
    assert!(
        cli.status.success(),
        "{}",
        String::from_utf8_lossy(&cli.stderr)
    );
    let cli: Value = serde_json::from_slice(&cli.stdout).unwrap();
    let mut process = Command::new(executable)
        .args(["mcp", "--allow-root"])
        .arg(&fixture.0)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();
    let mut input = process.stdin.take().unwrap();
    let calls = [
        request(1, "initialize", json!({"protocolVersion":"2025-06-18"})),
        request(2, "tools/list", json!({})),
        request(
            3,
            "tools/call",
            json!({"name":"code_health","arguments":{"root":fixture.0,"checks":["complexity"]}}),
        ),
        request(
            4,
            "tools/call",
            json!({"name":"code_health","arguments":{"root":outside.0}}),
        ),
    ];
    writeln!(input, "{}", calls.join("\n")).unwrap();
    drop(input);
    let output = process.wait_with_output().unwrap();
    assert!(output.status.success());
    let responses: Vec<Value> = String::from_utf8(output.stdout)
        .unwrap()
        .lines()
        .map(|line| serde_json::from_str(line).unwrap())
        .collect();
    assert_eq!(
        responses[1]["result"]["tools"][0]["annotations"]["readOnlyHint"],
        true
    );
    assert_eq!(responses[2]["result"]["structuredContent"], cli);
    assert_eq!(responses[3]["result"]["isError"], true);
    let mut invalid = fixture.options();
    invalid.checks = [Check::Unused].into();
    invalid.entries.push(Path::new("../outside.ts").into());
    assert!(scan(&invalid).is_err());
}

#[test]
fn writes_report_formats_with_builtin_or_packaged_styles() {
    let fixture = Fixture::new();
    fixture.put("main.ts", "export const unused = '<b>&</b>';");
    let outputs = Fixture::new();
    let run = |args: &[&str], out: Option<&Path>| {
        let mut command = Command::new(env!("CARGO_BIN_EXE_code-health"));
        command.args(["scan", "--root"]).arg(&fixture.0).args(args);
        if let Some(out) = out {
            command.arg("--out").arg(out);
        }
        command.output().unwrap()
    };
    let result = |output: &std::process::Output| -> Value {
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        serde_json::from_slice(&output.stdout).unwrap()
    };
    // All formats land in one new folder; the page uses the built-in styles and escapes source text
    let all = outputs.0.join("all");
    let summary = result(&run(&["--format", "all"], Some(&all)));
    assert_eq!(
        summary["written"],
        json!(["report.json", "report.md", "report.html"])
    );
    assert_eq!(summary["style"], "內建樣式");
    let saved: Value = serde_json::from_slice(&fs::read(all.join("report.json")).unwrap()).unwrap();
    assert_eq!(saved["schema_version"], 1);
    assert!(fs::read_to_string(all.join("report.md"))
        .unwrap()
        .starts_with("# Code health"));
    let page = fs::read_to_string(all.join("report.html")).unwrap();
    assert!(page.contains("wb-workbench") && page.contains("<code>main.ts</code>"));
    assert!(!page.contains("<b>&</b>"));
    assert_eq!(run(&["--format", "all"], Some(&all)).status.code(), Some(2));
    // An appearance package replaces the built-in styles
    let package = outputs.0.join("package");
    fs::create_dir(&package).unwrap();
    let css = ".wb-card{--packaged:1}";
    let digest: String = Sha256::digest(css.as_bytes())
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect();
    fs::write(
        package.join("manifest.json"),
        json!({"format":"static","version":"9.9.9","classes":code_health::REQUIRED_CLASSES,
            "entry":{"styles":"styles.css"},"assets":{"styles.css":{"sha256":digest}}})
        .to_string(),
    )
    .unwrap();
    fs::write(package.join("styles.css"), css).unwrap();
    let styled = outputs.0.join("styled");
    let package_arg = package.to_string_lossy().into_owned();
    let summary = result(&run(
        &["--format", "html", "--style-dir", &package_arg],
        Some(&styled),
    ));
    assert!(summary["style"]
        .as_str()
        .unwrap()
        .starts_with("外觀套件 9.9.9 (SHA-256 "));
    let page = fs::read_to_string(styled.join("report.html")).unwrap();
    assert!(page.contains("--packaged:1") && !page.contains("--wb-page-width:1180px"));
    fs::write(package.join("styles.css"), "</style><script>").unwrap();
    assert_eq!(
        run(
            &["--format", "html", "--style-dir", &package_arg],
            Some(&outputs.0.join("unsafe"))
        )
        .status
        .code(),
        Some(2)
    );
    // Reports stay outside the scanned root; without --out they go to the system temporary directory
    assert_eq!(
        run(&["--format", "html"], Some(&fixture.0.join("inside")))
            .status
            .code(),
        Some(2)
    );
    let summary = result(&run(&["--format", "json,html"], None));
    let out = PathBuf::from(summary["out"].as_str().unwrap());
    assert!(out.starts_with(fs::canonicalize(std::env::temp_dir()).unwrap()));
    assert!(out.join("report.html").is_file() && out.join("report.json").is_file());
    fs::remove_dir_all(out).unwrap();
    // One text format without --out still prints the report
    let printed = run(&["--format", "markdown"], None);
    assert!(String::from_utf8_lossy(&printed.stdout).starts_with("# Code health"));
}

#[test]
fn candidates_carry_stable_ids_and_merge_semantic_evidence() {
    let fixture = Fixture::new();
    fixture.put("main.ts", "import { used } from './lib';\nused();\n");
    fixture.put(
        "lib.ts",
        "export const used = () => 1;\nexport const spare = () => 2;\nexport const spare2 = () => 3;\n",
    );
    fixture.put("orphan.ts", "export const lonely = 1;\n");
    let mut options = fixture.options();
    options.entries = vec!["main.ts".into()];
    options.checks = [Check::Unused].into();
    let report = scan(&options).unwrap();
    let ids: Vec<&str> = rows(&report, "unused")
        .iter()
        .map(|row| row["id"].as_str().unwrap())
        .collect();
    for id in [
        "export:lib.ts#spare",
        "export:lib.ts#spare2",
        "file:orphan.ts",
        "export:orphan.ts#lonely",
    ] {
        assert!(ids.contains(&id), "{id} missing from {ids:?}");
    }
    assert!(rows(&report, "needs_review")
        .iter()
        .all(|row| row["id"].as_str().unwrap().starts_with("review:")));
    // Editing above a symbol moves its line but keeps its id
    fixture.put(
        "lib.ts",
        "// note\nexport const used = () => 1;\nexport const spare = () => 2;\nexport const spare2 = () => 3;\n",
    );
    let moved = scan(&options).unwrap();
    let spare = |report: &Value| {
        rows(report, "unused")
            .iter()
            .find(|row| row["id"] == "export:lib.ts#spare")
            .cloned()
            .unwrap()
    };
    assert_eq!(spare(&report)["line"], 2);
    assert_eq!(spare(&moved)["line"], 3);

    options.evidence = Some(
        json!({"schema":"code-health-evidence/1","root":fixture.0,"items":[
            {"id":"export:lib.ts#spare","status":"confirmed","provider":"typescript","references":0,"coverage":"project"},
            {"id":"export:lib.ts#spare2","status":"refuted","provider":"typescript","references":2,
                "locations":[{"path":"main.ts","line":1}],"note":"<dynamic import>"},
            {"id":"export:gone.ts#old","status":"confirmed"}
        ]}),
    );
    let merged = scan(&options).unwrap();
    assert_eq!(spare(&merged)["semantic"]["status"], "confirmed");
    let refuted = rows(&merged, "unused")
        .iter()
        .find(|row| row["id"] == "export:lib.ts#spare2")
        .unwrap()
        .clone();
    assert_eq!(refuted["semantic"]["references"], 2);
    assert_eq!(refuted["semantic"]["locations"][0]["path"], "main.ts");
    let semantic = &merged["semantic"];
    assert_eq!(semantic["counts"]["confirmed"], 1);
    assert_eq!(semantic["counts"]["refuted"], 1);
    assert_eq!(semantic["unmatched"], json!(["export:gone.ts#old"]));
    let total: u64 = ["unused", "needs_review"]
        .iter()
        .map(|key| rows(&merged, key).len() as u64)
        .sum();
    let counted: u64 = semantic["counts"]
        .as_object()
        .unwrap()
        .values()
        .map(|v| v.as_u64().unwrap())
        .sum();
    assert_eq!(counted, total);
    // Markdown and HTML show the result beside each candidate
    assert!(markdown(&merged).contains("| semantic |"));
    assert!(!markdown(&report).contains("semantic"));
    let page = html(&merged, &Style::builtin()).unwrap();
    assert!(page.contains("語意確認 2 / ") && page.contains("找到使用端 (2 處, typescript)"));
    assert!(page.contains("&lt;dynamic import&gt;") && page.contains("1 筆佐證找不到對應候選"));

    for bad in [
        json!({"schema":"other/1","items":[]}),
        json!({"schema":"code-health-evidence/1","items":[{"id":"x","status":"maybe"}]}),
        json!({"schema":"code-health-evidence/1","items":[{"id":"x","status":"confirmed"},{"id":"x","status":"refuted"}]}),
        json!({"schema":"code-health-evidence/1","root":std::env::temp_dir(),"items":[]}),
        json!({"schema":"code-health-evidence/1","items":[{"id":"x","status":"confirmed","locations":[{"path":"a.ts","line":0}]}]}),
    ] {
        options.evidence = Some(bad.clone());
        assert!(scan(&options).is_err(), "{bad} was accepted");
    }
}
