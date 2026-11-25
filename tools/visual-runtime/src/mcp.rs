//! Stdio MCP server around process-owned previews and per-call project roots.
use crate::{Previews, Workspace};
use serde_json::{json, Value};
use std::io::{self, BufRead, Read, Write};

const MESSAGE_LIMIT: u64 = 1024 * 1024;
const INSTRUCTIONS: &str = "Provide an authorized project root for each inspection, artifact or preview-start call. Preview jobs keep their own file snapshots and are controlled by job_id. No shell execution, framework migration or engine installation. Preview HTML runs in the browser; approve its source and network behavior. Main selects the project toolchain.";

fn tools() -> Value {
    let read = json!({"readOnlyHint":true,"destructiveHint":false,"idempotentHint":true,"openWorldHint":false});
    let write = json!({"readOnlyHint":false,"destructiveHint":false,"idempotentHint":false,"openWorldHint":false});
    let strings = json!({"type":"array","items":{"type":"string"}});
    json!([
        {"name":"visual_inspect","description":"Read framework/dependency declarations in this call's authorized project root; never run scripts.",
            "annotations":read,"inputSchema":{"type":"object","additionalProperties":false,"required":["root"],"properties":{"root":{"type":"string"}}}},
        {"name":"visual_artifacts","description":"Hash explicit files relative to this call's authorized root; no file contents returned.",
            "annotations":read,"inputSchema":{"type":"object","additionalProperties":false,"required":["root","paths"],
                "properties":{"root":{"type":"string"},"paths":strings}}},
        {"name":"visual_preview_start","description":"Snapshot explicit files within this call's authorized root into an owned loopback preview. Select only authorized public browser assets, never secrets. No directory listing or arbitrary commands.",
            "annotations":write,"inputSchema":{"type":"object","additionalProperties":false,"required":["root","entry","files"],
                "properties":{"root":{"type":"string"},"entry":{"type":"string"},"files":strings}}},
        {"name":"visual_preview_status","description":"Inspect a preview owned by this MCP process.",
            "annotations":read,"inputSchema":{"type":"object","additionalProperties":false,"required":["job_id"],"properties":{"job_id":{"type":"string"}}}},
        {"name":"visual_preview_stop","description":"Stop only this process's preview job and release its listener.",
            "annotations":write,"inputSchema":{"type":"object","additionalProperties":false,"required":["job_id"],"properties":{"job_id":{"type":"string"}}}}
    ])
}

fn local_error() -> Value {
    json!({"status": "local_error"})
}

/// Tool result, or an argument error for malformed calls.
pub fn call(previews: &Previews, name: &str, args: &Value) -> Result<Value, String> {
    let empty = serde_json::Map::new();
    let fields = match args {
        Value::Null => &empty,
        Value::Object(fields) => fields,
        _ => return Err("arguments must be an object".into()),
    };
    let allowed: &[&str] = match name {
        "visual_inspect" => &["root"],
        "visual_artifacts" => &["root", "paths"],
        "visual_preview_start" => &["root", "entry", "files"],
        "visual_preview_status" | "visual_preview_stop" => &["job_id"],
        _ => return Err("Unknown tool".into()),
    };
    if let Some(key) = fields.keys().find(|key| !allowed.contains(&key.as_str())) {
        return Err(format!("Unknown argument {key}"));
    }
    if let Some(key) = allowed.iter().find(|key| !fields.contains_key(**key)) {
        return Err(format!("{key} is required"));
    }
    let text = |key: &str| {
        fields[key]
            .as_str()
            .map(str::to_string)
            .ok_or(format!("{key} must be a string"))
    };
    let list = |key: &str| -> Result<Vec<String>, String> {
        fields[key]
            .as_array()
            .ok_or(format!("{key} must be a list of strings"))?
            .iter()
            .map(|item| {
                item.as_str()
                    .map(str::to_string)
                    .ok_or(format!("{key} must be a list of strings"))
            })
            .collect()
    };
    let result = match name {
        "visual_preview_status" => previews.status(&text("job_id")?),
        "visual_preview_stop" => previews.stop(&text("job_id")?),
        _ => {
            let root = text("root")?;
            let outcome = match name {
                "visual_inspect" => Workspace::new(&root).and_then(|workspace| workspace.inspect()),
                "visual_artifacts" => {
                    let paths = list("paths")?;
                    Workspace::new(&root).and_then(|workspace| workspace.artifacts(&paths))
                }
                _ => {
                    let (entry, files) = (text("entry")?, list("files")?);
                    Workspace::new(&root)
                        .and_then(|workspace| previews.start(&workspace, &entry, &files))
                }
            };
            outcome.unwrap_or_else(|_| local_error())
        }
    };
    Ok(result)
}

fn error(id: &Value, code: i32, message: &str) -> Value {
    json!({"jsonrpc":"2.0","id":id,"error":{"code":code,"message":message}})
}

pub fn reply(message: &str, previews: &Previews) -> Option<Value> {
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
    // Notifications carry no id and get no reply
    request.get("id")?;
    let params = &request["params"];
    let result = match method {
        "initialize" => {
            let version = params["protocolVersion"]
                .as_str()
                .filter(|value| {
                    ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"].contains(value)
                })
                .unwrap_or("2025-06-18");
            json!({"protocolVersion":version,"serverInfo":{"name":"Visual Runtime","version":crate::VERSION},
                "capabilities":{"tools":{}},"instructions":INSTRUCTIONS})
        }
        "ping" => json!({}),
        "tools/list" => json!({"tools":tools()}),
        "tools/call" => match params["name"]
            .as_str()
            .ok_or("Tool name is required".to_owned())
            .and_then(|name| call(previews, name, &params["arguments"]))
        {
            Ok(result) => {
                json!({"structuredContent":result,"content":[{"type":"text","text":result.to_string()}],"isError":false})
            }
            Err(message) => json!({"content":[{"type":"text","text":message}],"isError":true}),
        },
        _ => return Some(error(id, -32601, "Method not found")),
    };
    Some(json!({"jsonrpc":"2.0","id":id,"result":result}))
}

/// Serves newline-delimited JSON-RPC until input ends, then closes owned previews.
pub fn serve() -> Result<(), String> {
    let previews = Previews::default();
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    let result = loop {
        let mut message = String::new();
        let size = match input
            .by_ref()
            .take(MESSAGE_LIMIT + 1)
            .read_line(&mut message)
        {
            Ok(size) => size,
            Err(error) => break Err(error.to_string()),
        };
        if size == 0 {
            break Ok(());
        }
        let response = if size as u64 > MESSAGE_LIMIT {
            let mut rest = Vec::new();
            let _ = input.read_until(b'\n', &mut rest);
            Some(error(&Value::Null, -32600, "Message too large"))
        } else if message.trim().is_empty() {
            None
        } else {
            reply(message.trim_end(), &previews)
        };
        if let Some(response) = response {
            if writeln!(output, "{response}")
                .and_then(|()| output.flush())
                .is_err()
            {
                break Ok(());
            }
        }
    };
    previews.close();
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tools_take_roots_per_call() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("index.html"), "<h1>x</h1>").unwrap();
        let previews = Previews::default();
        let root = dir.path().to_string_lossy().to_string();
        let listed = reply(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/list"}"#,
            &previews,
        )
        .unwrap();
        assert_eq!(listed["result"]["tools"].as_array().unwrap().len(), 5);
        assert_eq!(
            call(&previews, "visual_inspect", &json!({"root": root})).unwrap()["status"],
            "ok"
        );
        assert_eq!(
            call(&previews, "visual_inspect", &json!({"root": "  "})).unwrap()["status"],
            "local_error"
        );
        assert!(call(&previews, "visual_inspect", &json!({})).is_err());
        let job = call(
            &previews,
            "visual_preview_start",
            &json!({"root": root, "entry": "index.html", "files": ["index.html"]}),
        )
        .unwrap();
        assert_eq!(job["status"], "ready");
        let id = job["job_id"].clone();
        assert_eq!(
            call(&previews, "visual_preview_status", &json!({"job_id": id})).unwrap()["status"],
            "ready"
        );
        assert_eq!(
            call(&previews, "visual_preview_stop", &json!({"job_id": id})).unwrap()["status"],
            "stopped"
        );
    }
}
