use code_health::{html, report_data, scan, Check, Options, RetainedRange, Style};

/// The Markdown report the CLI and MCP write: report-html's rendering of the page data.
fn page_markdown(report: &Value) -> String {
    report_html::markdown(&report_data(report)).unwrap()
}
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

/// Paths named on the `report:` lines a command prints after its summary.
fn report_files(stdout: &[u8]) -> Vec<PathBuf> {
    String::from_utf8_lossy(stdout)
        .lines()
        .filter_map(|line| line.strip_prefix("report: "))
        .map(PathBuf::from)
        .collect()
}
fn read_json(path: &Path) -> Value {
    serde_json::from_slice(&fs::read(path).unwrap()).unwrap()
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
    assert!(page_markdown(&report).contains("first.ts:1-7"));
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
        .args(["--checks", "complexity", "--format", "json"])
        .output()
        .unwrap();
    assert!(
        cli.status.success(),
        "{}",
        String::from_utf8_lossy(&cli.stderr)
    );
    // The command prints a short summary; the complete result is the report file
    let printed = String::from_utf8_lossy(&cli.stdout).into_owned();
    assert!(printed.starts_with("code-health: 1 files, coverage complete\n"));
    assert!(printed.lines().count() <= 8);
    let files = report_files(&cli.stdout);
    let cli = read_json(&files[0]);
    fs::remove_dir_all(files[0].parent().unwrap()).unwrap();
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
        false
    );
    // The tool answers with the same summary and writes the same full result to a report file
    let short = &responses[2]["result"]["structuredContent"];
    let text = responses[2]["result"]["content"][0]["text"]
        .as_str()
        .unwrap();
    assert!(
        text.starts_with("code-health: 1 files, coverage complete\n")
            && text.contains("\nreport: ")
    );
    assert_eq!(short["counts"]["complexity"], 1);
    assert_eq!(short["candidates"], json!([]));
    let saved = PathBuf::from(short["reports"]["json"].as_str().unwrap());
    assert_eq!(read_json(&saved), cli);
    assert!(PathBuf::from(short["reports"]["md"].as_str().unwrap()).is_file());
    assert!(!saved.starts_with(&fixture.0));
    fs::remove_dir_all(saved.parent().unwrap()).unwrap();
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
    let names = |output: &std::process::Output| -> Vec<String> {
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        report_files(&output.stdout)
            .iter()
            .map(|file| file.file_name().unwrap().to_string_lossy().into_owned())
            .collect()
    };
    // All formats land in one new folder; the page uses the built-in styles and escapes source text
    let all = outputs.0.join("all");
    assert_eq!(
        names(&run(&["--format", "all"], Some(&all))),
        ["report.json", "report.md", "report.html"]
    );
    assert_eq!(read_json(&all.join("report.json"))["schema_version"], 1);
    assert!(fs::read_to_string(all.join("report.md"))
        .unwrap()
        .starts_with("# Code health"));
    let page = fs::read_to_string(all.join("report.html")).unwrap();
    assert!(page.contains("wb-workbench") && page.contains("<code>main.ts</code>"));
    assert!(page.contains("內建樣式") && !page.contains("<b>&</b>"));
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
    assert_eq!(
        names(&run(
            &["--format", "html", "--style-dir", &package_arg],
            Some(&styled)
        )),
        ["report.html"]
    );
    let page = fs::read_to_string(styled.join("report.html")).unwrap();
    assert!(page.contains("外觀套件 9.9.9 (SHA-256 "));
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
    // Reports stay outside the scanned root
    assert_eq!(
        run(&["--format", "html"], Some(&fixture.0.join("inside")))
            .status
            .code(),
        Some(2)
    );
    // Without options the run prints a short summary and writes only report.md to a temporary folder
    let default = run(&[], None);
    assert_eq!(names(&default), ["report.md"]);
    let printed = String::from_utf8_lossy(&default.stdout).into_owned();
    assert!(printed.starts_with("code-health: 1 files, coverage "));
    assert!(printed.contains("\nneeds_review ") && printed.lines().count() <= 8);
    assert!(!printed.contains('{') && !printed.contains("| "));
    let file = &report_files(&default.stdout)[0];
    assert!(file.starts_with(fs::canonicalize(std::env::temp_dir()).unwrap()));
    assert!(fs::read_to_string(file)
        .unwrap()
        .starts_with("# Code health"));
    fs::remove_dir_all(file.parent().unwrap()).unwrap();
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
        json!({"schema":"code-health-evidence/v1","root":fixture.0,"items":[
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
    assert!(page_markdown(&merged).contains("語意確認"));
    assert!(!page_markdown(&report).contains("語意確認"));
    let mut bound = options.evidence.clone().unwrap();
    bound["schema"] = json!("code-health-evidence/v2");
    bound["source_files"] = moved["source_files"].clone();
    for item in bound["items"].as_array_mut().unwrap() {
        if let Some(row) = rows(&moved, "unused")
            .iter()
            .find(|row| row["id"] == item["id"])
        {
            item["position"] =
                json!({"path":row["path"],"line":row["line"],"column":row["column"]});
        } else {
            item["status"] = json!("unsupported");
        }
    }
    options.evidence = Some(bound.clone());
    assert_eq!(scan(&options).unwrap()["semantic"]["freshness"], "partial");
    // The earlier schema name code-health-evidence/2 is still read with the same source binding
    bound["schema"] = json!("code-health-evidence/2");
    options.evidence = Some(bound);
    assert_eq!(scan(&options).unwrap()["semantic"]["freshness"], "partial");
    let source = options.root.join("main.ts");
    let mut bytes = fs::read(&source).unwrap();
    bytes.extend_from_slice(b"\n// Changed after the evidence was captured\n");
    fs::write(source, bytes).unwrap();
    assert!(scan(&options)
        .unwrap_err()
        .contains("Evidence sources differ"));
    let page = html(&merged, &Style::builtin()).unwrap();
    assert!(page.contains("語意確認 2 / ") && page.contains("找到使用端 (2 處, typescript)"));
    assert!(page.contains("&lt;dynamic import&gt;") && page.contains("1 筆佐證找不到對應候選"));

    for bad in [
        json!({"schema":"other/1","items":[]}),
        json!({"schema":"code-health-evidence/v1","items":[{"id":"x","status":"maybe"}]}),
        json!({"schema":"code-health-evidence/v1","items":[{"id":"x","status":"confirmed"},{"id":"x","status":"refuted"}]}),
        json!({"schema":"code-health-evidence/v1","root":std::env::temp_dir(),"items":[]}),
        json!({"schema":"code-health-evidence/v1","items":[{"id":"x","status":"confirmed","locations":[{"path":"a.ts","line":0}]}]}),
    ] {
        options.evidence = Some(bad.clone());
        assert!(scan(&options).is_err(), "{bad} was accepted");
    }
}

#[test]
fn mcp_answers_an_oversized_message_and_keeps_serving() {
    let fixture = Fixture::new();
    fixture.put("main.ts", "export const count = () => 1;");
    let run = |messages: &[String]| -> Vec<Value> {
        let mut process = Command::new(env!("CARGO_BIN_EXE_code-health"))
            .args(["mcp", "--allow-root"])
            .arg(&fixture.0)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .spawn()
            .unwrap();
        let mut input = process.stdin.take().unwrap();
        for message in messages {
            writeln!(input, "{message}").unwrap();
        }
        drop(input);
        let output = process.wait_with_output().unwrap();
        assert!(output.status.success());
        String::from_utf8(output.stdout)
            .unwrap()
            .lines()
            .map(|line| serde_json::from_str(line).unwrap())
            .collect()
    };
    // 5000 evidence items fit in one message
    let items: Vec<Value> = (0..5000)
        .map(|i| json!({"id":format!("export:src/file{i}.ts#name{i}"),"status":"confirmed","provider":"typescript-language-server"}))
        .collect();
    let call = request(
        1,
        "tools/call",
        json!({"name":"code_health","arguments":{"root":fixture.0,"checks":["unused"],
            "evidence":{"schema":"code-health-evidence/1","items":items}}}),
    );
    assert!(call.len() > 256 * 1024);
    let replies = run(&[call, request(2, "ping", json!({}))]);
    assert_eq!(replies.len(), 2);
    assert_eq!(replies[0]["result"]["isError"], false);
    assert_eq!(
        replies[0]["result"]["structuredContent"]["semantic"]["unmatched"]
            .as_array()
            .unwrap()
            .len(),
        5000
    );
    // A message over the limit gets an error and the next request still works
    let oversized = format!("{{\"padding\":\"{}\"}}", "x".repeat(9 * 1024 * 1024));
    let replies = run(&[oversized, request(3, "ping", json!({}))]);
    assert_eq!(replies.len(), 2);
    assert_eq!(replies[0]["error"]["code"], -32600);
    assert_eq!(replies[1]["id"], 3);
}

#[test]
fn scan_wide_notes_and_repeated_options_are_explicit() {
    let fixture = Fixture::new();
    fixture.put("lonely.ts", "export const value = 1;");
    let mut options = fixture.options();
    options.checks = [Check::Unused].into();
    let report = scan(&options).unwrap();
    // Without a resolved entry point the note covers the whole scan
    assert!(rows(&report, "needs_review")
        .iter()
        .any(|row| row["id"] == "review:scan"));
    let cli = |args: &[&str]| {
        Command::new(env!("CARGO_BIN_EXE_code-health"))
            .args(["scan", "--root"])
            .arg(&fixture.0)
            .args(args)
            .output()
            .unwrap()
    };
    let twice = cli(&["--format", "json", "--format", "md"]);
    assert_eq!(twice.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&twice.stderr).contains("more than once"));
    assert!(cli(&[
        "--checks",
        "unused",
        "--retain-file",
        "lonely.ts",
        "--retain-file",
        "lonely.ts"
    ])
    .status
    .success());
}

#[test]
fn candidates_point_at_the_symbol_name_for_position_queries() {
    let fixture = Fixture::new();
    fixture.put("main.ts", "import { used } from './lib';\nused();\n");
    fixture.put(
        "lib.ts",
        "export const used = () => 1;\n  export   function   spare測試(a: number) { return a; }\nconst inner = 2;\nexport { inner as renamed };\nexport class Svc {\n  private cache = 1;\n    helper() { return 1; }\n}\nnew Svc();\n/* 註解 */ export const after = 1;\n",
    );
    let mut options = fixture.options();
    options.entries = vec!["main.ts".into()];
    options.checks = [Check::Unused].into();
    let report = scan(&options).unwrap();
    let position = |id: &str| {
        let row = rows(&report, "unused")
            .iter()
            .find(|row| row["id"] == id)
            .unwrap_or_else(|| panic!("{id} missing"));
        (
            row["line"].as_u64().unwrap(),
            row["column"].as_u64().unwrap(),
        )
    };
    // 1-based line and column of the declared name, counted in UTF-16 units
    assert_eq!(position("export:lib.ts#spare測試"), (2, 23));
    assert_eq!(position("export:lib.ts#renamed"), (4, 10));
    assert_eq!(position("export:lib.ts#Svc"), (5, 14));
    assert_eq!(position("member:lib.ts#Svc.cache"), (6, 11));
    assert_eq!(position("member:lib.ts#Svc.helper"), (7, 5));
    assert_eq!(position("export:lib.ts#after"), (10, 23));
}

#[test]
fn members_used_inside_template_literal_interpolations_are_not_candidates() {
    let fixture = Fixture::new();
    fixture.put(
        "main.ts",
        "export class Svc {\n  private static next = 0;\n  private readonly id = 1;\n  private spare = 2;\n  private escape(value: string) { return value; }\n  private nested = 3;\n  readonly name = `a-${Svc.next++}-${this.id}`;\n  find(key: string) { return `#${this.escape(key)} ${[1].map(n => `${n}${this.nested}`).join('}')}`; }\n  text = 'not ${this.spare}';\n}\nnew Svc().find('x');\n",
    );
    let mut options = fixture.options();
    options.entries = vec!["main.ts".into()];
    options.checks = [Check::Unused].into();
    let report = scan(&options).unwrap();
    let members: Vec<&str> = rows(&report, "unused")
        .iter()
        .filter(|row| row["kind"] == "member")
        .map(|row| row["name"].as_str().unwrap())
        .collect();
    // `name` and `text` are public fields nothing reads; the interpolated members are in use
    assert_eq!(members, ["spare", "name", "text"]);
}
