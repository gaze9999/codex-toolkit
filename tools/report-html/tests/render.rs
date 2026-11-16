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
        "stats":[{"label":"Unused","value":2,"tone":"warning","bar":true},{"label":"Kept","value":0,"bar":true},{"label":"Score","value":"A"}],
        "sections":[
            {"label":"Unused","columns":[{"key":"path","label":"File","kind":"code"},{"key":"line","label":"Line","kind":"number"},{"key":"why"}],
             "rows":[{"path":"src/a.ts","line":4,"why":"<script>alert(1)</script>"},{"path":"src/b.ts","line":9}]},
            {"label":"Kept","empty":"Nothing kept","columns":[{"key":"path"}],"rows":[]}
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
    assert!(page.contains("<b data-tone=\"warning\">2</b><span>Unused</span>"));
    assert!(page.contains("style=\"flex:2\"") && !page.contains("style=\"flex:0\""));
    assert!(page.contains("Unused<span class=\"rh-count\">2</span>"));
    assert!(page.contains("<td><code>src/a.ts</code></td><td class=\"rh-num\">4</td>"));
    assert!(page.contains("<th scope=\"col\">why</th>") && page.contains("Nothing kept"));
    assert!(page.contains("內建樣式") && page.contains("--wb-page-width:1180px"));
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
        text: String::new(),
        notes: vec![],
        page: json!({}),
    };
    assert!(emit("test", &[], &options, &data).is_err());
    assert!(!out.exists());
    fs::remove_dir_all(dir).unwrap();
}
