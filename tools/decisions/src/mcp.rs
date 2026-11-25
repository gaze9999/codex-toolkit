//! Stdio MCP server exposing status, validate and evaluate over the same core.
use crate::{evaluate, preview, status, Config, Https};
use serde_json::{json, Value};
use std::io::{self, BufRead, Read, Write};

const MESSAGE_LIMIT: u64 = 4 * 1024 * 1024;
const INSTRUCTIONS: &str = "Optional bounded evaluation of authorized evidence. Main chooses tools and delegation; answers never authorize actions. No ChatGPT credential reuse or provider fallback.";

fn tools() -> Value {
    let local = json!({"readOnlyHint":true,"destructiveHint":false,"idempotentHint":true,"openWorldHint":false});
    let remote = json!({"readOnlyHint":true,"destructiveHint":false,"idempotentHint":false,"openWorldHint":true});
    json!([
        {"name":"decisions_status","description":"Check selected credential variable presence, without network or secret output.",
            "annotations":local,"inputSchema":{"type":"object","additionalProperties":false,"properties":{}}},
        {"name":"decisions_validate","description":"Validate bounded request JSON locally; return byte size/hash, never echo evidence.",
            "annotations":local,"inputSchema":{"type":"object","additionalProperties":false,"required":["request"],
                "properties":{"request":{"type":"object"}}}},
        {"name":"decisions_evaluate","description":"Send evidence and rubric to OpenAI only with scoped user authorization. Predicate, choice, score and per-question refusals retain provider meaning. approved is an assertion of existing authority, not a permission grant.",
            "annotations":remote,"inputSchema":{"type":"object","additionalProperties":false,"required":["request"],
                "properties":{"request":{"type":"object"},"approved":{"type":"boolean","default":false}}}}
    ])
}

/// Tool result as structured JSON, or an argument error message.
pub fn call(config: &Config, name: &str, args: &Value) -> Result<Value, String> {
    let empty = serde_json::Map::new();
    let fields = match args {
        Value::Null => &empty,
        Value::Object(fields) => fields,
        _ => return Err("arguments must be an object".into()),
    };
    let allowed: &[&str] = match name {
        "decisions_status" => &[],
        "decisions_validate" => &["request"],
        "decisions_evaluate" => &["request", "approved"],
        _ => return Err("Unknown tool".into()),
    };
    if let Some(key) = fields.keys().find(|key| !allowed.contains(&key.as_str())) {
        return Err(format!("Unknown argument {key}"));
    }
    if name == "decisions_status" {
        return Ok(status(config));
    }
    let request = fields
        .get("request")
        .filter(|value| value.is_object())
        .ok_or("request must be an object")?;
    let invalid = |problem: crate::Problem| json!({"status": "invalid_input", "reason": problem.0});
    if name == "decisions_validate" {
        return Ok(preview(request, config).unwrap_or_else(invalid));
    }
    let approved = match fields.get("approved") {
        None => false,
        Some(Value::Bool(value)) => *value,
        Some(_) => return Err("approved must be a boolean".into()),
    };
    Ok(evaluate(request, config, approved, &Https).unwrap_or_else(invalid))
}

fn error(id: &Value, code: i32, message: &str) -> Value {
    json!({"jsonrpc":"2.0","id":id,"error":{"code":code,"message":message}})
}

pub fn reply(message: &str, config: &Config) -> Option<Value> {
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
            json!({"protocolVersion":version,"serverInfo":{"name":"Decisions","version":crate::VERSION},
                "capabilities":{"tools":{}},"instructions":INSTRUCTIONS})
        }
        "ping" => json!({}),
        "tools/list" => json!({"tools":tools()}),
        "tools/call" => match params["name"]
            .as_str()
            .ok_or("Tool name is required".to_owned())
            .and_then(|name| call(config, name, &params["arguments"]))
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

/// Serves newline-delimited JSON-RPC on standard input and output until input ends.
pub fn serve(config: &Config) -> Result<(), String> {
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
            // Drain the oversized line before answering
            let mut rest = Vec::new();
            input
                .read_until(b'\n', &mut rest)
                .map_err(|e| e.to_string())?;
            Some(error(&Value::Null, -32600, "Message too large"))
        } else if message.trim().is_empty() {
            None
        } else {
            reply(message.trim_end(), config)
        };
        if let Some(response) = response {
            writeln!(output, "{response}").map_err(|e| e.to_string())?;
            output.flush().map_err(|e| e.to_string())?;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lists_and_gates_tools() {
        let config = Config {
            credential_env: "DECISIONS_TEST_KEY_MCP".into(),
            ..Config::default()
        };
        std::env::remove_var("DECISIONS_TEST_KEY_MCP");
        let listed = reply(r#"{"jsonrpc":"2.0","id":1,"method":"tools/list"}"#, &config).unwrap();
        let mut names: Vec<&str> = listed["result"]["tools"]
            .as_array()
            .unwrap()
            .iter()
            .map(|t| t["name"].as_str().unwrap())
            .collect();
        names.sort();
        assert_eq!(
            names,
            [
                "decisions_evaluate",
                "decisions_status",
                "decisions_validate"
            ]
        );
        let request = json!({"input": "public synthetic evidence", "questions": [{"type": "predicate", "name": "check", "instructions": "Is evidence present?"}]});
        assert_eq!(
            call(&config, "decisions_validate", &json!({"request": request})).unwrap()["status"],
            "validated"
        );
        assert_eq!(
            call(&config, "decisions_evaluate", &json!({"request": request})).unwrap()["status"],
            "approval_required"
        );
        assert_eq!(
            call(
                &config,
                "decisions_evaluate",
                &json!({"request": request, "approved": true})
            )
            .unwrap()["status"],
            "needs_credentials"
        );
        assert!(call(
            &config,
            "decisions_evaluate",
            &json!({"request": request, "approved": "true"})
        )
        .is_err());
        assert_eq!(
            call(&config, "decisions_status", &json!({})).unwrap()["status"],
            "needs_credentials"
        );
        assert!(reply(
            r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#,
            &config
        )
        .is_none());
    }
}
