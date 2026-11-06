use super::*;
use std::collections::BTreeMap;
pub fn save(dir: &Path, name: &str, v: &Value) -> Result<()> {
    let raw = serde_json::to_string(v)?
        .replace('<', "\\u003c")
        .replace('>', "\\u003e")
        .replace('&', "\\u0026");
    let html = include_str!("report.html").replace("__AUDIT_JSON__", &raw);
    write_new(
        &dir.join(format!("{name}.json")),
        &serde_json::to_vec_pretty(v)?,
    )?;
    write_new(&dir.join(format!("{name}.html")), html.as_bytes())
}
pub fn recover(dir: &Path) -> Result<Value> {
    let plan = read_json(&dir.join("plan.json"))?;
    let log = fs::read(dir.join("events.jsonl"))?;
    let mut records = vec![];
    for line in log.split_inclusive(|b| *b == b'\n') {
        if line.ends_with(b"\n") {
            records.push(serde_json::from_slice::<Value>(line)?)
        }
    }
    let finished = records.last().is_some_and(|v| v["status"] == "finished");
    let mut items = vec![];
    let mut bytes = 0u64;
    let mut counts = BTreeMap::new();
    for row in list(&plan, "items")? {
        let mut members = BTreeMap::new();
        let mut skip = None;
        for e in records.iter().filter(|v| v["id"] == row["id"]) {
            if e["status"] == "skipped" {
                skip = e["reason"].as_str();
                continue;
            }
            if let Some(p) = e["path"].as_str() {
                members.insert(p, e.clone());
            }
        }
        let mut details = vec![];
        for path in list(row, "members")?
            .iter()
            .map(|v| &v["path"])
            .chain(std::iter::once(&row["path"]))
        {
            let mut m=members.remove(path.as_str().ok_or("Invalid member")?).unwrap_or_else(||json!({"path":path,"status":if skip.is_some(){"skipped"}else{"not_started"}}));
            if m["status"] == "started" {
                m["status"] = json!("unknown")
            }
            bytes += m["size"].as_u64().unwrap_or(0);
            details.push(m)
        }
        let n = details.iter().filter(|v| v["status"] == "deleted").count();
        let status = if skip.is_some() {
            "skipped"
        } else if details
            .iter()
            .any(|v| v["status"] == "unknown" || v["status"] == "not_started")
        {
            "unknown"
        } else if n == details.len() {
            "deleted"
        } else if n > 0 {
            "partial"
        } else {
            "failed"
        };
        *counts.entry(status).or_insert(0usize) += 1;
        items.push(json!({"id":row["id"],"path":row["path"],"relative":row["relative"],"tree":row["tree"],"project":row["project"],"rule":row["rule"],"rule_version":row["rule_version"],"action":"permanent_delete","status":status,"reason":skip,"members":details}));
    }
    let partial = !finished || items.iter().any(|v| v["status"] != "deleted");
    let v = json!({"version":VERSION,"mode":"apply","batch":plan["batch"],"source":plan["source"],"finished":finished,"partial":partial,"counts":counts,"deleted_bytes":bytes,"items":items});
    let name = format!("changes-{}", batch());
    save(dir, &name, &v)?;
    Ok(
        json!({"batch":plan["batch"],"source":plan["source"],"run":dir,"counts":counts,"deleted_bytes":bytes,"partial":partial,"html":dir.join(format!("{name}.html")),"json":dir.join(format!("{name}.json"))}),
    )
}
