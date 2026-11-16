//! Command-line output shared by tools: one result as text, JSON, Markdown and an HTML page.
use crate::{markdown, new_folder, render, Style};
use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};

/// A finished check: `json` is the machine-readable result, `text` the terminal form, `notes`
/// go to standard error and `page` is `report-html/1` data for Markdown and HTML.
pub struct Rendered {
    pub json: Value,
    pub text: String,
    pub notes: Vec<String>,
    pub page: Value,
}

pub struct Emit {
    pub formats: Vec<&'static str>,
    pub out: Option<PathBuf>,
    pub style_dir: Option<PathBuf>,
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
            "text" => "text",
            "json" => "json",
            "md" | "markdown" => "md",
            "html" => "html",
            other => {
                return Err(format!(
                    "Unknown format {other:?}; use text, json, md, html or all"
                ))
            }
        };
        if !formats.contains(&format) {
            formats.push(format);
        }
    }
    Ok(formats)
}

/// Prints one text format, or writes the selected formats into a new folder outside every `scanned` root
/// and prints a summary with the folder path.
pub fn emit(
    tool: &str,
    scanned: &[&Path],
    options: &Emit,
    rendered: &Rendered,
) -> Result<(), String> {
    for note in &rendered.notes {
        eprintln!("{note}");
    }
    let style = match &options.style_dir {
        Some(dir) if options.formats.contains(&"html") => Style::load(dir)?,
        Some(_) => return Err("--style-dir applies to the html format".into()),
        None => Style::builtin(),
    };
    let render = |format: &str| -> Result<String, String> {
        Ok(match format {
            "text" => rendered.text.clone(),
            "md" => markdown(&rendered.page)?,
            "html" => render(&rendered.page, &style)?,
            _ => serde_json::to_string_pretty(&rendered.json).map_err(|e| e.to_string())? + "\n",
        })
    };
    if options.out.is_none() && options.formats.len() == 1 && options.formats[0] != "html" {
        print!("{}", render(options.formats[0])?);
        return Ok(());
    }
    let contents = options
        .formats
        .iter()
        .map(|format| render(format))
        .collect::<Result<Vec<_>, _>>()?;
    let out = new_folder(options.out.as_deref(), scanned, tool)?;
    let mut written = Vec::new();
    for (format, content) in options.formats.iter().zip(contents) {
        let name = format!("report.{}", if *format == "text" { "txt" } else { format });
        fs::write(out.join(&name), content).map_err(|e| e.to_string())?;
        written.push(name);
    }
    println!(
        "{}",
        json!({"out":out,"written":written,"style":if options.formats.contains(&"html") {json!(style.label())} else {Value::Null}})
    );
    Ok(())
}
