use report_html::{markdown, new_folder, render, Style, REQUIRED_CLASSES, SCHEMA};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};

fn sample() -> Value {
    json!({
        "schema":SCHEMA,"title":"Sample <report>",
        "tags":[{"label":"complete","tone":"success"}],
        "info":[["Root", "/tmp/a&b"], ["Files", 3]],
        "note":"Candidates only",
        "stats":[{"label":"Unused","value":2,"tone":"warning","bar":true,"section":0},{"label":"Kept","value":0,"bar":true},{"label":"Score","value":"A"}],
        "sections":[
            {"label":"Unused","columns":[{"key":"path","label":"File","kind":"code"},{"key":"line","label":"Line","kind":"number"},{"key":"why"}],
             "rows":[{"path":"src/a.ts","line":4,"why":"<script>alert(1)</script>"},{"path":"src/b.ts","line":9}]},
            {"label":"Kept","empty":"Nothing kept","columns":[{"key":"path"}],"rows":[]},
            {"label":"Snippets","columns":[{"key":"code","label":"Code","kind":"source","lang":"ts"}],
             "rows":[{"code":"const a = \"<b>\"; // note"},{"code":null}]}
        ]
    })
}

fn temp(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("report-html-test-{}-{name}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir(&dir).unwrap();
    dir
}

#[test]
fn renders_cards_tables_and_escapes_every_value() {
    let page = render(&sample(), &Style::builtin()).unwrap();
    assert!(page.starts_with("<!doctype html>") && page.contains("<html lang=\"zh-Hant-TW\">"));
    assert!(page.contains("<title>Sample &lt;report&gt;</title>"));
    assert!(
        page.contains("/tmp/a&amp;b") && page.contains("&lt;script&gt;alert(1)&lt;/script&gt;")
    );
    assert!(!page.contains("<script>alert(1)"));
    // Stat cards, a bar from the positive counts marked for it, tabs with row counts and typed cells
    assert!(page.contains("<b data-tone=\"warning\">2</b><a class=\"wb-tag wb-tag-link\" data-tone=\"warning\" data-outlined=\"false\" href=\"#panel0\">Unused</a>"));
    assert!(page.contains("<b>A</b><span>Score</span>") && page.contains("id=\"panel0\""));
    assert!(page.contains("<table class=\"wb-table wb-table-striped\" id=\"t0\">"));
    // Source cells are colored with the WBUI token classes and stay escaped
    assert!(page.contains("<td><pre class=\"rh-code\"><code data-lang=\"typescript\"><span class=\"wb-code-keyword\">const</span> a = <span class=\"wb-code-string\">&quot;&lt;b&gt;&quot;</span>; <span class=\"wb-code-comment\">// note</span></code></pre></td>"));
    assert!(page.contains("<tr><td></td></tr>"));
    assert!(page.contains("style=\"flex:2\"") && !page.contains("style=\"flex:0\""));
    assert!(page.contains("Unused<span class=\"rh-count\">2</span>"));
    assert!(page.contains("<td><code>src/a.ts</code></td><td class=\"rh-num\">4</td>"));
    assert!(page.contains("<th scope=\"col\">why</th>") && page.contains("Nothing kept"));
    assert!(page.contains("內建樣式") && page.contains("--wb-page-width:1180px"));
}

#[test]
fn compact_cells_keep_the_full_escaped_text_and_short_identifiers() {
    let mut data = sample();
    let detail = "<record>".repeat(20);
    data["sections"][0]["rows"][0] = json!({"path":"RULE-123","why":detail});
    let page = render(&data, &Style::builtin()).unwrap();
    assert!(page.contains("<code class=\"rh-id\">RULE-123</code>"));
    assert!(page.contains("<details class=\"rh-long\"><summary>"));
    assert!(page.contains(&format!(
        "</summary>{}</details>",
        "&lt;record&gt;".repeat(20)
    )));
    assert!(!page.contains("<record>"));
}

#[test]
fn rejects_data_that_does_not_match_the_schema() {
    let style = Style::builtin();
    let broken = |change: fn(&mut Value)| {
        let mut data = sample();
        change(&mut data);
        render(&data, &style)
    };
    assert!(broken(|d| d["schema"] = json!("other/1")).is_err());
    assert!(broken(|d| d["title"] = json!(" ")).is_err());
    assert!(broken(|d| d["tags"][0]["tone"] = json!("loud")).is_err());
    assert!(broken(|d| d["info"][0] = json!(["only one"])).is_err());
    assert!(broken(|d| d["sections"][0]["columns"][0]["kind"] = json!("html")).is_err());
    assert!(broken(|d| d["sections"][0]["columns"] = json!([])).is_err());
    assert!(broken(|d| d["sections"][2]["columns"][0]["lang"] = json!("cobol")).is_err());
    assert!(broken(|d| d["sections"][2]["columns"][0]["lang"] = json!(1)).is_err());
    assert!(broken(|d| d["stats"][0]["section"] = json!(3)).is_err());
    assert!(broken(|d| d["stats"][0]["section"] = json!("Unused")).is_err());
    assert!(broken(|d| d["sections"] = json!({})).is_err());
    // Stats and sections are optional
    let minimal = render(&json!({"schema":SCHEMA,"title":"Only info"}), &style).unwrap();
    assert!(!minimal.contains("rh-tabs\" role") && !minimal.contains("class=\"rh-stats\""));
}

fn package(dir: &std::path::Path, css: &str, classes: Value, sha: Option<&str>) {
    let digest = sha.map(str::to_owned).unwrap_or_else(|| {
        Sha256::digest(css.as_bytes())
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect()
    });
    let manifest = json!({"format":"static","version":"1.2.3","classes":classes,
        "entry":{"styles":"look.css"},"assets":{"look.css":{"sha256":digest}}});
    fs::write(dir.join("manifest.json"), manifest.to_string()).unwrap();
    fs::write(dir.join("look.css"), css).unwrap();
}

#[test]
fn page_uses_only_the_required_static_classes() {
    let page = render(&sample(), &Style::builtin()).unwrap();
    let mut classes: Vec<&str> = page
        .split("class=\"")
        .skip(1)
        .filter_map(|rest| rest.split('"').next())
        .flat_map(str::split_whitespace)
        .filter(|name| name.starts_with("wb-"))
        .collect();
    classes.sort_unstable();
    classes.dedup();
    assert!(classes.len() >= 10);
    for class in classes {
        assert!(
            REQUIRED_CLASSES.contains(&class),
            "{class} is missing from REQUIRED_CLASSES"
        );
    }
}

#[test]
fn appearance_package_replaces_builtin_styles() {
    let dir = temp("package");
    let all = json!(REQUIRED_CLASSES);
    package(&dir, ".wb-card{--packaged:1}", all.clone(), None);
    let style = Style::load(&dir).unwrap();
    assert!(style.label().starts_with("外觀套件 1.2.3 (SHA-256 "));
    let page = render(&sample(), &style).unwrap();
    assert!(page.contains("--packaged:1") && !page.contains("--wb-page-width:1180px"));
    // Prefix entries such as wb-card- cover wb-card-head and wb-card-body
    let mut prefixed: Vec<&str> = REQUIRED_CLASSES
        .iter()
        .copied()
        .filter(|c| !c.starts_with("wb-card-"))
        .collect();
    prefixed.push("wb-card-");
    package(&dir, "a{}", json!(prefixed), None);
    assert!(Style::load(&dir).is_ok());
    package(&dir, "a{}", json!(["wb-workbench", "wb-card"]), None);
    let error = Style::load(&dir).err().unwrap();
    assert!(error.contains("wb-page") && error.contains("wb-filter"));
    package(&dir, "a{}", all.clone(), Some("00"));
    assert!(Style::load(&dir).err().unwrap().contains("SHA-256"));
    package(&dir, "a{}</STYLE><script>", all.clone(), None);
    assert!(Style::load(&dir).is_err());
    fs::write(
        dir.join("manifest.json"),
        json!({"format":"static","classes":all,"entry":{"styles":"../look.css"}}).to_string(),
    )
    .unwrap();
    assert!(Style::load(&dir).is_err());
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn cli_reads_a_file_or_stdin_and_keeps_existing_output() {
    let dir = temp("cli");
    let input = dir.join("report.json");
    fs::write(&input, sample().to_string()).unwrap();
    let executable = env!("CARGO_BIN_EXE_report-html");
    let printed = Command::new(executable)
        .args(["render", "--input"])
        .arg(&input)
        .output()
        .unwrap();
    assert!(printed.status.success());
    let expected = render(&sample(), &Style::builtin()).unwrap();
    assert_eq!(String::from_utf8(printed.stdout).unwrap(), expected);
    let out = dir.join("report.html");
    let mut child = Command::new(executable)
        .args(["render", "--input", "-", "--out"])
        .arg(&out)
        .stdin(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(sample().to_string().as_bytes())
        .unwrap();
    assert!(child.wait().unwrap().success());
    assert_eq!(fs::read_to_string(&out).unwrap(), expected);
    let again = Command::new(executable)
        .args(["render", "--input"])
        .arg(&input)
        .arg("--out")
        .arg(&out)
        .output()
        .unwrap();
    assert_eq!(again.status.code(), Some(2));
    fs::write(&input, "{").unwrap();
    let invalid = Command::new(executable)
        .args(["render", "--input"])
        .arg(&input)
        .output()
        .unwrap();
    assert_eq!(invalid.status.code(), Some(2));
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn markdown_and_output_folder_share_the_report_data() {
    let text = markdown(&sample()).unwrap();
    assert!(text.starts_with("# Sample <report>\n\ncomplete\n"));
    assert!(text.contains("| Root | /tmp/a&b |") && text.contains("| Unused | 2 |"));
    assert!(text.contains("| File | Line | why |\n| --- | --- | --- |"));
    assert!(text.contains("| src/a.ts | 4 | <script>alert(1)</script> |"));
    assert!(text.contains("## Kept\n\nNothing kept"));
    assert!(markdown(&json!({"schema":"other/1","title":"x"})).is_err());

    let scanned = temp("scanned");
    let outside = temp("outside");
    let made = new_folder(Some(&outside.join("report")), &[&scanned], "x").unwrap();
    assert!(made.is_dir());
    assert!(new_folder(Some(&outside.join("report")), &[&scanned], "x").is_err());
    assert!(new_folder(Some(&scanned.join("inside")), &[&scanned], "x").is_err());
    assert!(new_folder(Some(&scanned.join("new/nested/report")), &[&scanned], "x").is_err());
    assert!(!scanned.join("new").exists());
    let default = new_folder(None, &[&scanned], "report-html-test").unwrap();
    assert!(default.starts_with(fs::canonicalize(std::env::temp_dir()).unwrap()));
    for dir in [scanned, outside, default] {
        fs::remove_dir_all(dir).unwrap();
    }
}

#[test]
fn invalid_page_does_not_leave_partial_reports() {
    use report_html::output::{emit, Emit, Rendered};
    let dir = temp("invalid-output");
    let out = dir.join("report");
    let options = Emit {
        formats: vec!["json", "html"],
        out: Some(out.clone()),
        style_dir: None,
    };
    let data = Rendered {
        json: json!({}),
        summary: vec![],
        notes: vec![],
        page: json!({}),
        markdown: None,
    };
    assert!(emit("test", &[], &options, &data).is_err());
    assert!(!out.exists());
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn write_puts_every_format_in_one_new_folder_and_reports_the_files() {
    use report_html::output::{parse_formats, write, Emit, Rendered, DEFAULT_FORMATS};
    let dir = temp("write-output");
    let rendered = |markdown: Option<String>| Rendered {
        json: json!({"count":2}),
        summary: vec!["two items".into()],
        notes: vec![],
        page: sample(),
        markdown,
    };
    let options = |formats: Vec<&'static str>, name: &str| Emit {
        formats,
        out: Some(dir.join(name)),
        style_dir: None,
    };
    // Markdown alone is the default
    assert_eq!(DEFAULT_FORMATS.to_vec(), vec!["md"]);
    let only = write(
        "test",
        &[],
        &options(DEFAULT_FORMATS.to_vec(), "default"),
        &rendered(None),
    )
    .unwrap();
    assert_eq!(only.files, vec![only.out.join("report.md")]);
    assert_eq!(only.style, None);
    assert!(fs::read_to_string(&only.files[0])
        .unwrap()
        .starts_with("# Sample <report>"));
    let all = write(
        "test",
        &[],
        &options(parse_formats("all").unwrap(), "all"),
        &rendered(Some("# own\n".into())),
    )
    .unwrap();
    let names: Vec<String> = all
        .files
        .iter()
        .map(|file| file.file_name().unwrap().to_string_lossy().into_owned())
        .collect();
    assert_eq!(names, ["report.json", "report.md", "report.html"]);
    assert_eq!(all.style.as_deref(), Some("內建樣式"));
    // A tool's own Markdown replaces the generated one
    assert_eq!(
        fs::read_to_string(all.out.join("report.md")).unwrap(),
        "# own\n"
    );
    assert_eq!(
        fs::read_to_string(all.out.join("report.json")).unwrap(),
        "{\n  \"count\": 2\n}\n"
    );
    assert!(parse_formats("text").is_err());
    assert_eq!(
        parse_formats("markdown,md,json").unwrap(),
        vec!["md", "json"]
    );
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn repeated_reports_get_distinct_folders() {
    let first = new_folder(None, &[], "report-html-repeat").unwrap();
    let second = new_folder(None, &[], "report-html-repeat").unwrap();
    assert_ne!(first, second);
    assert!(new_folder(None, &[], "../escape").is_err());
    fs::remove_dir_all(first).unwrap();
    fs::remove_dir_all(second).unwrap();
}

fn rich() -> Value {
    json!({
        "schema":SCHEMA,"title":"Rich",
        "panels":[
            {"label":"Features","kind":"cards","tags":[{"label":"overall","tone":"error"}],"note":"by feature",
             "items":[{"value":"3 / 4","label":"Form <a>","note":"1 failed","tone":"error","title":"F-1 failed"},{"value":5,"label":"List"}]},
            {"label":"Flow","kind":"flow","columns":["Screen","API"],
             "nodes":[{"id":"a","column":"Screen","label":"Exception form","detail":"REQ-1\nMSG-1","tone":"warning"},{"id":"b","column":"API","label":"applyException"}],
             "edges":[{"from":"a","to":"b"},{"from":"a","to":"missing"}]}
        ],
        "sections":[
            {"label":"Cases","filters":[{"key":"status","label":"Status"}],"columns":[{"key":"id"},{"key":"status"}],
             "rows":[{"id":"C1","status":"passed"},{"id":"C2","status":"failed"},{"id":"C3","status":"passed"}]},
            {"label":"Conflicts","kind":"matrix","corner":"Rule \\ Source","columns":["spec","SIT"],"hint":"Click a count",
             "rows":[{"label":"R-1","cells":[{"value":2,"tone":"warning","label":"R-1 spec","detail":"spec says <x>"},null]}]},
            {"label":"Coverage","kind":"list","items":["page 3 <unread>"]},
            {"label":"About","kind":"text","text":"line 1\nline 2"}
        ]
    })
}

#[test]
fn only_the_v1_schema_name_is_read() {
    assert_eq!(SCHEMA, "report-html/v1");
    let style = Style::builtin();
    for name in ["report-html/1", "report-html/v2"] {
        let mut other = sample();
        other["schema"] = json!(name);
        assert!(render(&other, &style).is_err() && markdown(&other).is_err());
    }
}

#[test]
fn panels_and_section_kinds_render_escaped() {
    let page = render(&rich(), &Style::builtin()).unwrap();
    // Panels are cards before the tabbed sections
    let (features, cases) = (
        page.find("<h2>Features</h2>").unwrap(),
        page.find("role=\"tablist\"").unwrap(),
    );
    assert!(features < cases);
    assert!(page.contains("<div class=\"wb-card rh-stat\" data-tone=\"error\" title=\"F-1 failed\"><b data-tone=\"error\">3 / 4</b><span>Form &lt;a&gt;</span><small>1 failed</small></div>"));
    assert!(page.contains("<p class=\"rh-tags\"><span class=\"wb-tag\" data-tone=\"error\">overall</span></p><p class=\"rh-meta\">by feature</p>"));
    // Flow nodes keep their detail for the tooltip; edges to unknown nodes are skipped
    assert!(page.contains("class=\"wb-flow-node\" data-tone=\"warning\" tabindex=\"0\" aria-label=\"REQ-1\nMSG-1\" data-detail=\"REQ-1\nMSG-1\""));
    assert_eq!(page.matches("class=\"wb-flow-edge\"").count(), 1);
    // Filters list distinct values in row order and mark each row
    assert!(page.contains("<select data-filter=\"0\"><option value=\"\">全部</option><option>passed</option><option>failed</option></select>"));
    assert!(page.contains("<tr data-f0=\"failed\">"));
    // Matrix cells carry escaped detail, empty cells stay empty, and the tab counts rows
    assert!(page.contains("<button type=\"button\" class=\"wb-count\" data-tone=\"warning\" data-detail=\"spec says &lt;x&gt;\" aria-label=\"R-1 spec\">2</button></td><td></td>"));
    assert!(
        page.contains("<th scope=\"col\">Rule \\ Source</th>")
            && page.contains("Conflicts<span class=\"rh-count\">1</span>")
    );
    assert!(page.contains("<li><span class=\"rh-text\">page 3 &lt;unread&gt;</span></li>"));
    // Text has no count on its tab
    assert!(
        page.contains(">About</button>")
            && page.contains("<p class=\"rh-text\">line 1\nline 2</p>")
    );
}

#[test]
fn rich_page_uses_only_required_classes_and_rejects_bad_kinds() {
    let page = render(&rich(), &Style::builtin()).unwrap();
    for class in page
        .split("class=\"")
        .skip(1)
        .filter_map(|rest| rest.split('"').next())
        .flat_map(str::split_whitespace)
        .filter(|name| name.starts_with("wb-"))
    {
        assert!(
            REQUIRED_CLASSES.contains(&class),
            "{class} is missing from REQUIRED_CLASSES"
        );
    }
    let style = Style::builtin();
    let broken = |change: fn(&mut Value)| {
        let mut data = rich();
        change(&mut data);
        render(&data, &style)
    };
    assert!(broken(|d| d["sections"][1]["kind"] = json!("chart")).is_err());
    assert!(broken(|d| d["panels"][1]["nodes"][0]["column"] = json!("Nowhere")).is_err());
    assert!(broken(|d| d["sections"][0]["filters"][0] = json!({"label":"no key"})).is_err());
    assert!(broken(|d| d["sections"][1]["rows"][0]["cells"][0]["tone"] = json!("loud")).is_err());
    assert!(broken(|d| d["sections"][2]["count"] = json!(-1)).is_err());
}

#[test]
fn markdown_covers_panels_and_every_kind() {
    let text = markdown(&rich()).unwrap();
    for part in [
        "## Features",
        "overall",
        "| Form <a> | 3 / 4 | 1 failed |",
        "- Screen: Exception form",
        "- Exception form → applyException",
        "| C2 | failed |",
        "| Rule \\ Source | spec | SIT |",
        "| R-1 | 2 |  |",
        "- page 3 <unread>",
        "line 1\nline 2",
    ] {
        assert!(text.contains(part), "missing {part:?} in\n{text}");
    }
}
