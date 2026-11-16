//! Command-line output shared by tools: a short summary on standard output and the full report
//! in files, so a large result never floods the caller.
use crate::{markdown, new_folder, render, Style};
use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};

/// Formats written when the caller selects none.
pub const DEFAULT_FORMATS: [&str; 1] = ["md"];

/// A finished check. `summary` is the few lines printed for the caller, `json` the complete
/// machine-readable result, `page` the `report-html/1` data for Markdown and HTML, `markdown`
/// replaces the Markdown generated from `page`, and `notes` go to standard error.
pub struct Rendered {
    pub json: Value,
    pub summary: Vec<String>,
    pub notes: Vec<String>,
    pub page: Value,
    pub markdown: Option<String>,
}

pub struct Emit {
    pub formats: Vec<&'static str>,
    pub out: Option<PathBuf>,
    pub style_dir: Option<PathBuf>,
}

/// The folder and files one run produced.
pub struct Written {
    pub out: PathBuf,
    pub files: Vec<PathBuf>,
    pub style: Option<String>,
}

pub fn column(key: &str, label: &str, kind: &str) -> Value {
    json!({"key":key,"label":label,"kind":kind})
}

pub fn parse_formats(value: &str) -> Result<Vec<&'static str>, String> {
    if value == "all" {
        return Ok(vec!["json", "md", "html"]);
    }
    let mut formats = Vec::new();
    for name in value.split(',') {
        let format = match name.trim() {
            "json" => "json",
            "md" | "markdown" => "md",
            "html" => "html",
            other => {
                return Err(format!(
                    "Unknown format {other:?}; use json, md, html or all"
                ))
            }
        };
        if !formats.contains(&format) {
            formats.push(format);
        }
    }
    Ok(formats)
}

/// Writes the selected formats as `report.*` into a new folder outside every `scanned` root.
pub fn write(
    tool: &str,
    scanned: &[&Path],
    options: &Emit,
    rendered: &Rendered,
) -> Result<Written, String> {
    if options.formats.is_empty()
        || options
            .formats
            .iter()
            .any(|format| !["json", "md", "html"].contains(format))
    {
        return Err("Select json, md or html report formats".into());
    }
    let html = options.formats.contains(&"html");
    let style = match &options.style_dir {
        Some(dir) if html => Style::load(dir)?,
        Some(_) => return Err("--style-dir applies to the html format".into()),
        None => Style::builtin(),
    };
    // Render everything before creating the folder, so a failed format leaves nothing behind
    let contents = options
        .formats
        .iter()
        .map(|format| {
            Ok(match *format {
                "md" => match &rendered.markdown {
                    Some(text) => text.clone(),
                    None => markdown(&rendered.page)?,
                },
                "html" => render(&rendered.page, &style)?,
                _ => {
                    serde_json::to_string_pretty(&rendered.json).map_err(|e| e.to_string())? + "\n"
                }
            })
        })
        .collect::<Result<Vec<String>, String>>()?;
    let out = new_folder(options.out.as_deref(), scanned, tool)?;
    let mut files = Vec::new();
    for (format, content) in options.formats.iter().zip(contents) {
        let path = out.join(format!("report.{format}"));
        fs::write(&path, content).map_err(|e| e.to_string())?;
        files.push(path);
    }
    Ok(Written {
        out,
        files,
        style: html.then(|| style.label().to_owned()),
    })
}

/// Writes the report files, then prints the summary and one `report:` line per file.
pub fn emit(
    tool: &str,
    scanned: &[&Path],
    options: &Emit,
    rendered: &Rendered,
) -> Result<(), String> {
    for note in &rendered.notes {
        eprintln!("{note}");
    }
    let written = write(tool, scanned, options, rendered)?;
    for line in &rendered.summary {
        println!("{line}");
    }
    for file in &written.files {
        println!("report: {}", file.display());
    }
    Ok(())
}
