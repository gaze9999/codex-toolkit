use code_health::{scan, Check, Options, RetainedRange};
use serde_json::{json, Value};
use std::io::{self, BufRead, Read, Write};
use std::path::PathBuf;

const MESSAGE_LIMIT: u64 = 256 * 1024;

fn schema() -> Value {
    let path = json!({"type":"string","minLength":1});
    let paths = json!({"type":"array","items":path,"maxItems":500});
    let line = json!({"type":"integer","minimum":1});
    json!({"name":"code_health","description":"Read-only syntax-level code maintainability scan of an approved local root. Returns candidates, retained scopes and areas requiring manual review.",
        "annotations":{"readOnlyHint":true,"destructiveHint":false,"idempotentHint":true,"openWorldHint":false},
        "inputSchema":{"type":"object","additionalProperties":false,"required":["root"],"properties":{
            "root":path,"entries":paths,"retained_files":paths,"marker_patterns":paths,
            "checks":{"type":"array","items":{"enum":["unused","duplicates","complexity"]},"minItems":1,"maxItems":3},
            "min_tokens":{"type":"integer","minimum":8,"maximum":1000},
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
        "initialize" => json!({"protocolVersion":match params["protocolVersion"].as_str() {
            Some(value @ ("2025-11-25" | "2025-06-18" | "2025-03-26" | "2024-11-05")) => value,
            _ => "2025-06-18",
        },"serverInfo":{"name":"code-health","version":env!("CARGO_PKG_VERSION")},"capabilities":{"tools":{}}}),
        "ping" => json!({}),
        "tools/list" => json!({"tools":[schema()]}),
        "tools/call" => match execute(params, roots) {
            Ok(report) => {
                json!({"structuredContent":report,"content":[{"type":"text","text":report.to_string()}],"isError":false})
            }
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
        if size as u64 > MESSAGE_LIMIT {
            return Err("MCP message size limit exceeded".into());
        }
        if let Some(response) = reply(&message, &roots) {
            writeln!(output, "{response}")
                .and_then(|_| output.flush())
                .map_err(|e| e.to_string())?;
        }
    }
}
