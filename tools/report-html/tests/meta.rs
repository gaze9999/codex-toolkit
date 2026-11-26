use report_html::{markdown, meta, render, Style, SCHEMA};
use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn temp(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("report-html-meta-{}-{name}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir(&dir).unwrap();
    dir
}

fn report(meta: Value) -> Value {
    json!({"schema":SCHEMA,"title":"Meta","meta":meta,"info":[["Own <row>","value"]]})
}

#[test]
fn common_fields_come_first_in_a_fixed_order_and_absent_ones_show_as_not_provided() {
    let data = report(json!({
        "environment":"macos aarch64","tool":"demo <1.0>",
        "target":{"value":"checked by hand","by":"ai"},"inputs":["a.json 0123456789ab","b.json fedcba987654"]
    }));
    let page = render(&data, &Style::builtin()).unwrap();
    let labels: Vec<usize> = meta::FIELDS
        .iter()
        .map(|(_, label)| {
            page.find(&format!("<th scope=\"row\">{label}</th>"))
                .unwrap()
        })
        .collect();
    assert!(labels.windows(2).all(|pair| pair[0] < pair[1]));
    assert!(labels[6] < page.find("Own &lt;row&gt;").unwrap());
    assert!(page.contains("demo &lt;1.0&gt;") && page.contains("checked by hand (AI 補充)"));
    assert!(page.contains("<span class=\"rh-text rh-missing\">未提供</span>"));
    assert!(page.contains("a.json 0123456789ab\nb.json fedcba987654"));
    assert_eq!(
        meta::missing(&data).unwrap(),
        ["format", "revision", "generated"]
    );
    let text = markdown(&data).unwrap();
    assert!(text.contains("| 工具 | demo <1.0> |\n| 報告格式 | 未提供 |"));
    assert!(text.find("| 輸入檔案 |").unwrap() < text.find("| Own <row> |").unwrap());
}

#[test]
fn reports_without_meta_keep_their_info_rows_only() {
    let mut data = report(Value::Null);
    data.as_object_mut().unwrap().remove("meta");
    let page = render(&data, &Style::builtin()).unwrap();
    assert!(!page.contains("未提供") && page.contains("Own &lt;row&gt;"));
    assert!(meta::missing(&data).unwrap().is_empty());
}

#[test]
fn unknown_fields_and_unmarked_objects_are_rejected() {
    for bad in [
        json!({"owner":"x"}),
        json!({"tool":{"value":"x"}}),
        json!({"tool":true}),
        json!("tool"),
    ] {
        assert!(
            render(&report(bad.clone()), &Style::builtin()).is_err(),
            "{bad}"
        );
        assert!(markdown(&report(bad)).is_err());
    }
}

#[test]
fn collect_reads_the_checkout_time_environment_and_input_hashes() {
    let dir = temp("collect");
    let git = |args: &[&str]| {
        assert!(Command::new("git")
            .args(args)
            .current_dir(&dir)
            .output()
            .unwrap()
            .status
            .success());
    };
    git(&["init", "-q"]);
    fs::write(dir.join("a.txt"), "a").unwrap();
    git(&["add", "a.txt"]);
    git(&[
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.invalid",
        "commit",
        "-qm",
        "init",
    ]);
    fs::write(dir.join("b.txt"), "b").unwrap();
    let inputs = [dir.join("a.txt"), dir.join("missing.txt")];
    let facts = meta::Facts {
        tool: "demo",
        version: "1.2.3",
        format: "demo-report/v1",
        target: Some(&dir),
        scope: Some("src"),
        runtime: Some("Node v24"),
        inputs: &inputs,
        at: None,
    };
    let out = meta::collect(&facts);
    let m = &out["meta"];
    assert_eq!(m["tool"], "demo 1.2.3");
    assert_eq!(m["format"], "demo-report/v1");
    assert!(m["target"].as_str().unwrap().ends_with("\n範圍: src"));
    assert!(m["revision"]
        .as_str()
        .unwrap()
        .ends_with(", 未提交檔案 1 個"));
    let generated = m["generated"].as_str().unwrap();
    assert!(
        generated.contains(" UTC+") || generated.contains(" UTC-"),
        "{generated}"
    );
    assert!(m["environment"].as_str().unwrap().ends_with(", Node v24"));
    assert!(m["inputs"][0]
        .as_str()
        .unwrap()
        .ends_with("a.txt ca978112ca1b"));
    assert!(m["inputs"][1]
        .as_str()
        .unwrap()
        .ends_with("missing.txt (無法讀取)"));
    assert_eq!(out["missing"], json!([]));
    let outside = meta::collect(&meta::Facts {
        tool: "demo",
        format: "demo-report/v1",
        target: Some(&std::env::temp_dir()),
        ..Default::default()
    });
    assert!(outside["meta"]["revision"].is_null());
    assert_eq!(outside["missing"], json!(["revision", "inputs"]));
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn cli_collects_meta_and_names_missing_fields_on_render() {
    let executable = env!("CARGO_BIN_EXE_report-html");
    let out = Command::new(executable)
        .args(["meta", "--tool", "demo", "--format", "demo/v1"])
        .output()
        .unwrap();
    assert!(out.status.success());
    let value: Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(value["meta"]["tool"], "demo");
    assert_eq!(value["missing"], json!(["target", "revision", "inputs"]));
    assert_eq!(
        Command::new(executable)
            .args(["meta", "--format", "x"])
            .output()
            .unwrap()
            .status
            .code(),
        Some(2)
    );
    let dir = temp("cli");
    let input = dir.join("report.json");
    fs::write(&input, report(value["meta"].clone()).to_string()).unwrap();
    let rendered = Command::new(executable)
        .args(["render", "--input"])
        .arg(&input)
        .output()
        .unwrap();
    assert!(rendered.status.success());
    assert_eq!(
        String::from_utf8(rendered.stderr).unwrap(),
        "report-html: meta fields without a value: target, revision, inputs\n"
    );
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn rfc3339_times_convert_to_unix_seconds() {
    assert_eq!(meta::parse_time("1970-01-01T00:00:00Z"), Some(0));
    assert_eq!(
        meta::parse_time("2026-11-26T09:00:00.000Z"),
        Some(1_795_683_600)
    );
    assert_eq!(
        meta::parse_time("2026-11-26T17:00:00+08:00"),
        Some(1_795_683_600)
    );
    assert_eq!(
        meta::parse_time("2000-02-29T00:00:00-05:30"),
        Some(951_802_200)
    );
    for bad in ["", "now", "2026-13-01T00:00:00Z", "2026-11-26T09:00:00"] {
        assert_eq!(meta::parse_time(bad), None, "{bad}");
    }
}

#[test]
fn cli_formats_a_recorded_time_and_prints_rows() {
    let executable = env!("CARGO_BIN_EXE_report-html");
    let out = Command::new(executable)
        .args([
            "meta",
            "--tool",
            "demo",
            "--format",
            "f",
            "--at",
            "2026-11-26T09:00:00Z",
        ])
        .output()
        .unwrap();
    assert!(out.status.success());
    let value: Value = serde_json::from_slice(&out.stdout).unwrap();
    let at = meta::parse_time("2026-11-26T09:00:00Z");
    assert_eq!(value["meta"]["generated"], json!(meta::local_time_at(at)));
    let mut child = Command::new(executable)
        .args(["meta", "--rows", "-"])
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .spawn()
        .unwrap();
    use std::io::Write;
    child
        .stdin
        .take()
        .unwrap()
        .write_all(br#"{"tool":"x","inputs":["a","b"],"target":{"value":"v","by":"ai"}}"#)
        .unwrap();
    let rows: Value = serde_json::from_slice(&child.wait_with_output().unwrap().stdout).unwrap();
    assert_eq!(rows[0], json!(["工具", "x"]));
    assert_eq!(rows[1], json!(["報告格式", "未提供"]));
    assert_eq!(rows[2], json!(["檢查對象", "v (AI 補充)"]));
    assert_eq!(rows[6], json!(["輸入檔案", "a\nb"]));
    for args in [
        &["meta", "--tool", "d", "--format", "f", "--at", "soon"][..],
        &["meta", "--rows", "-", "--tool", "d"][..],
    ] {
        assert_eq!(
            Command::new(executable)
                .args(args)
                .output()
                .unwrap()
                .status
                .code(),
            Some(2)
        );
    }
}
