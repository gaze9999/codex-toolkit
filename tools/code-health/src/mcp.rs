use code_health::{markdown, report_data, scan, summary, Check, Options, RetainedRange};
use report_html::output::{write, Emit, Rendered};
use serde_json::{json, Value};
use std::io::{self, BufRead, Read, Write};
use std::path::Path;
use std::path::PathBuf;

// Large enough for 5000 evidence items with their locations
const MESSAGE_LIMIT: u64 = 8 * 1024 * 1024;

fn schema() -> Value {
    let path = json!({"type":"string","minLength":1});
    let paths = json!({"type":"array","items":path,"maxItems":500});
    let line = json!({"type":"integer","minimum":1});
    let location =
        json!({"type":"object","required":["path","line"],"properties":{"path":path,"line":line}});
    let item = json!({"type":"object","required":["id","status"],"properties":{"id":path,"status":{"enum":["confirmed","refuted","unsupported","timeout","error"]},
        "provider":{"type":"string"},"provider_version":{"type":"string"},"coverage":{"type":"string"},"references":{"type":"integer","minimum":0},
        "note":{"type":"string"},"locations":{"type":"array","maxItems":50,"items":location}}});
    let evidence = json!({"type":"object","description":"Semantic evidence (schema code-health-evidence/1) merged into candidates by id",
        "required":["schema","items"],"properties":{"schema":{"const":"code-health-evidence/1"},"root":path,"items":{"type":"array","maxItems":5000,"items":item}}});
    json!({"name":"code_health","description":"Syntax-level code maintainability scan of an approved local root; the project is only read. Returns a short summary, counts and the first 40 unused candidates with stable ids and positions, and writes the full report (report.md, report.json) to a new folder in the system temporary directory. Read the JSON report for remaining candidates; narrow checks or root only when appropriate for the project; optional evidence attaches semantic checks to candidates by id.",
        "annotations":{"readOnlyHint":false,"destructiveHint":false,"idempotentHint":false,"openWorldHint":false},
        "inputSchema":{"type":"object","additionalProperties":false,"required":["root"],"properties":{
            "root":path,"entries":paths,"retained_files":paths,"marker_patterns":paths,
            "checks":{"type":"array","items":{"enum":["unused","duplicates","complexity"]},"minItems":1,"maxItems":3},
            "min_tokens":{"type":"integer","minimum":8,"maximum":1000},
            "evidence":evidence,
            "retained_ranges":{"type":"array","maxItems":500,"items":{"type":"object","additionalProperties":false,
                "required":["path","start_line","end_line"],"properties":{"path":path,"start_line":line,"end_line":line}}}
        }}
    })
}

fn strings<'a>(value: &'a Value, key: &str) -> Result<Vec<&'a str>, String> {
    let Some(value) = value.get(key) else {
        return Ok(Vec::new());
    };
    let values = value
        .as_array()
        .filter(|rows| rows.len() <= 500)
        .ok_or_else(|| format!("{key} must be a bounded array"))?;
    values
        .iter()
        .map(|item| {
            item.as_str()
                .filter(|s| !s.is_empty())
                .ok_or_else(|| format!("{key} requires nonempty strings"))
        })
        .collect()
}

fn integer(value: &Value, key: &str) -> Result<usize, String> {
    value[key]
        .as_u64()
        .and_then(|number| usize::try_from(number).ok())
        .ok_or_else(|| format!("{key} requires an integer"))
}

fn execute(params: &Value, roots: &[PathBuf]) -> Result<Value, String> {
    if params["name"] != "code_health" {
        return Err("Unknown tool".into());
    }
    let args = &params["arguments"];
    let fields = args.as_object().ok_or("arguments must be an object")?;
    if fields.keys().any(|key| {
        !matches!(
            key.as_str(),
            "root"
                | "entries"
                | "checks"
                | "marker_patterns"
                | "retained_files"
                | "retained_ranges"
                | "min_tokens"
                | "evidence"
        )
    }) {
        return Err("Unknown argument".into());
    }
    let root = args["root"]
        .as_str()
        .map(PathBuf::from)
        .filter(|path| path.is_absolute())
        .ok_or("root must be an absolute directory")?;
    let root = root.canonicalize().map_err(|_| "Scan root unavailable")?;
    if !roots.iter().any(|allowed| root.starts_with(allowed)) {
        return Err("Scan root is outside the server allowlist".into());
    }
    let mut options = Options::new(root);
    options.entries = strings(args, "entries")?
        .into_iter()
        .map(PathBuf::from)
        .collect();
    options.retained_files = strings(args, "retained_files")?
        .into_iter()
        .map(PathBuf::from)
        .collect();
    options.marker_patterns = strings(args, "marker_patterns")?
        .into_iter()
        .map(str::to_owned)
        .collect();
    if args.get("checks").is_some() {
        options.checks = strings(args, "checks")?
            .into_iter()
            .map(Check::parse)
            .collect::<Result<_, _>>()?;
    }
    if let Some(evidence) = args.get("evidence") {
        options.evidence = Some(evidence.clone());
    }
    if args.get("min_tokens").is_some() {
        options.min_tokens = integer(args, "min_tokens")?;
    }
    if let Some(ranges) = args.get("retained_ranges") {
        for row in ranges
            .as_array()
            .filter(|rows| rows.len() <= 500)
            .ok_or("retained_ranges must be a bounded array")?
        {
            if row.as_object().is_none_or(|object| object.len() != 3) {
                return Err("Invalid retained range fields".into());
            }
            options.retained_ranges.push(RetainedRange {
                path: row["path"]
                    .as_str()
                    .ok_or("A retained range needs a path")?
                    .into(),
                start_line: integer(row, "start_line")?,
                end_line: integer(row, "end_line")?,
            });
        }
    }
    scan(&options)
}

/// Candidates returned inline; the complete lists are in the report files.
const INLINE_CANDIDATES: usize = 40;

/// Writes the full report to the system temporary directory and returns the short form: summary,
/// report paths, counts and the first candidates with their IDs and positions.
fn compact(report: Value) -> Result<(Value, String), String> {
    let root = report["root"].as_str().unwrap_or("").to_owned();
    let rendered = Rendered {
        summary: summary(&report),
        page: report_data(&report),
        markdown: Some(markdown(&report)),
        notes: Vec::new(),
        json: report,
    };
    let written = write(
        "code-health",
        &[Path::new(&root)],
        &Emit {
            formats: vec!["md", "json"],
            out: None,
            style_dir: None,
        },
        &rendered,
    )?;
    let report = &rendered.json;
    let count = |key: &str| report[key].as_array().map(Vec::len);
    let unused = report["unused"].as_array().map_or(&[][..], Vec::as_slice);
    let candidates: Vec<Value> = unused
        .iter()
        .take(INLINE_CANDIDATES)
        .map(|row| {
            json!({"id":row["id"],"kind":row["kind"],"path":row["path"],"line":row["line"],"column":row["column"],
                "name":row["name"],"semantic":row.get("semantic")})
        })
        .collect();
    // Review items that name a symbol can be settled by a reference query, so they come inline too
    let review = report["needs_review"]
        .as_array()
        .map_or(&[][..], Vec::as_slice);
    let positioned: Vec<&Value> = review
        .iter()
        .filter(|row| row.get("column").is_some())
        .collect();
    let review_inline: Vec<Value> = positioned
        .iter()
        .take(INLINE_CANDIDATES)
        .map(|row| {
            json!({"id":row["id"],"path":row["path"],"line":row["line"],"column":row["column"],
                "symbol":row["symbol"],"reason":row["reason"],"semantic":row.get("semantic")})
        })
        .collect();
    let mut text = rendered.summary.join("\n");
    for file in &written.files {
        text.push_str(&format!("\nreport: {}", file.display()));
    }
    let result = json!({
        "summary":rendered.summary,
        "reports":{"md":written.files[0],"json":written.files[1]},
        "root":report["root"],"files_scanned":report["files_scanned"],"partial":report["partial"],
        "counts":{"unused":count("unused"),"duplicates":count("duplicates"),"complexity":count("complexity"),
            "needs_review":count("needs_review"),"retained":count("retained")},
        "candidates":candidates,
        "candidates_omitted":unused.len().saturating_sub(INLINE_CANDIDATES),
        "review":review_inline,
        "review_omitted":review.len().saturating_sub(review_inline.len()),
        "semantic":report.get("semantic")
    });
    Ok((result, text))
}

fn error(id: &Value, code: i32, message: &str) -> Value {
    json!({"jsonrpc":"2.0","id":id,"error":{"code":code,"message":message}})
}

fn reply(message: &str, roots: &[PathBuf]) -> Option<Value> {
    let request: Value = match serde_json::from_str(message) {
        Ok(value) => value,
        Err(_) => return Some(error(&Value::Null, -32700, "Parse error")),
    };
    let id = &request["id"];
    let Some(method) = request["method"]
        .as_str()
        .filter(|_| request["jsonrpc"] == "2.0")
    else {
        return Some(error(id, -32600, "Invalid request"));
    };
    request.get("id")?;
    let params = &request["params"];
    let result = match method {
        "initialize" => json!({"protocolVersion":params["protocolVersion"].as_str()
            .filter(|value| ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"].contains(value))
            .unwrap_or("2025-06-18"),"serverInfo":{"name":"code-health","version":env!("CARGO_PKG_VERSION")},"capabilities":{"tools":{}}}),
        "ping" => json!({}),
        "tools/list" => json!({"tools":[schema()]}),
        "tools/call" => match execute(params, roots) {
            Ok(report) => match compact(report) {
                Ok((result, text)) => {
                    json!({"structuredContent":result,"content":[{"type":"text","text":text}],"isError":false})
                }
                Err(message) => json!({"content":[{"type":"text","text":message}],"isError":true}),
            },
            Err(message) => json!({"content":[{"type":"text","text":message}],"isError":true}),
        },
        _ => return Some(error(id, -32601, "Method not found")),
    };
    Some(json!({"jsonrpc":"2.0","id":id,"result":result}))
}

pub fn serve(roots: Vec<PathBuf>) -> Result<(), String> {
    if roots.is_empty() {
        return Err("Select at least one --allow-root directory".into());
    }
    let roots = roots
        .into_iter()
        .map(|root| {
            let root = root
                .canonicalize()
                .map_err(|_| "Allowed root unavailable")?;
            if !root.is_dir() || root.parent().is_none() {
                return Err("Allowed root must be a directory below the filesystem root");
            }
            Ok(root)
        })
        .collect::<Result<Vec<_>, _>>()?;
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    loop {
        let mut message = String::new();
        let size = input
            .by_ref()
            .take(MESSAGE_LIMIT + 1)
            .read_line(&mut message)
            .map_err(|e| e.to_string())?;
        if size == 0 {
            return Ok(());
        }
        let response = if size as u64 > MESSAGE_LIMIT {
            // Drop the rest of the oversized line, answer and keep serving
            if !message.ends_with('\n') {
                let mut rest = Vec::new();
                input
                    .read_until(b'\n', &mut rest)
                    .map_err(|e| e.to_string())?;
            }
            Some(error(&Value::Null, -32600, "Message exceeds 8 MiB"))
        } else if message.trim().is_empty() {
            None
        } else {
            reply(&message, &roots)
        };
        if let Some(response) = response {
            writeln!(output, "{response}")
                .and_then(|_| output.flush())
                .map_err(|e| e.to_string())?;
        }
    }
}
