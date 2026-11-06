use super::*;
use std::io::BufRead;
fn tools() -> Vec<Value> {
    let string = json!({"type":"string","minLength":1});
    [("scan_artifacts","Inventory explicit local workspaces and write offline reports",json!({"workspace":{"type":"array","items":string,"minItems":1},"out":string,"codex_home":string,"claude_home":string}),vec!["workspace","out"]),
 ("apply_artifacts","Permanently delete only explicitly selected items after a user requests execution. Never retry an uncertain operation.",json!({"report":string,"selection":string,"out":string}),vec!["report","selection","out"]),
 ("report_artifacts","Rebuild a change report from its existing local journal",json!({"run":string}),vec!["run"])]
 .into_iter().map(|(n,d,p,r)|json!({"name":n,"description":d,"inputSchema":{"type":"object","properties":p,"required":r,"additionalProperties":false},"annotations":{"destructiveHint":n=="apply_artifacts","openWorldHint":false}})).collect()
}
pub fn serve() -> Result<()> {
    for line in io::stdin().lock().lines() {
        let line = line?;
        let req: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(_) => {
                println!(
                    "{}",
                    json!({"jsonrpc":"2.0","id":null,"error":{"code":-32700,"message":"Parse error"}})
                );
                continue;
            }
        };
        if req.get("id").is_none() {
            continue;
        }
        let result = match req["method"].as_str() {
            Some("initialize") => {
                json!({"protocolVersion":match req["params"]["protocolVersion"].as_str(){Some(v @ ("2025-11-25"|"2025-06-18"|"2025-03-26"|"2024-11-05"))=>v,_=>"2025-06-18"},"serverInfo":{"name":"agent-artifact-audit","version":env!("CARGO_PKG_VERSION")},"capabilities":{"tools":{}}})
            }
            Some("ping") => json!({}),
            Some("tools/list") => json!({"tools":tools()}),
            Some("tools/call") => {
                let args = &req["params"]["arguments"];
                let name = req["params"]["name"].as_str().unwrap_or("");
                let result = match name {
                    "scan_artifacts" => dispatch("scan", args),
                    "apply_artifacts" => dispatch("apply", args),
                    "report_artifacts" => dispatch("report", args),
                    _ => Err("Unknown tool".into()),
                };
                match result {
                    Ok(v) => {
                        json!({"content":[{"type":"text","text":v.to_string()}],"isError":false})
                    }
                    Err(e) => {
                        json!({"content":[{"type":"text","text":e.to_string()}],"isError":true})
                    }
                }
            }
            _ => {
                println!(
                    "{}",
                    json!({"jsonrpc":"2.0","id":req["id"],"error":{"code":-32601,"message":"Method not found"}})
                );
                continue;
            }
        };
        println!(
            "{}",
            json!({"jsonrpc":"2.0","id":req["id"],"result":result})
        );
        io::stdout().flush()?;
    }
    Ok(())
}
