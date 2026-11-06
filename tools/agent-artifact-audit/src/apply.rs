use super::*;
use std::collections::BTreeSet;
fn event(log: &mut fs::File, v: Value) -> Result<()> {
    let mut bytes = serde_json::to_vec(&v)?;
    bytes.push(b'\n');
    log.write_all(&bytes)?;
    log.sync_all()?;
    Ok(())
}
fn preflight(row: &Value) -> Result<()> {
    let path = Path::new(required(row, "path")?);
    let tree = Path::new(required(row, "tree")?);
    if row["rule"] == "setup-rotation" {
        scan::backup_eligible(path)?;
        if safety::snapshot(path)? != row["stamp"] {
            return Err("Backup changed since scan".into());
        }
        return Ok(());
    }
    scan::eligible(path, tree)?;
    if safety::snapshot(path)? != row["stamp"] {
        return Err("Directory changed since scan".into());
    }
    let mut entries = BTreeSet::new();
    for e in fs::read_dir(path)? {
        entries.insert(e?.path());
    }
    for child in list(row, "members")? {
        let file = Path::new(required(child, "path")?);
        if file.parent() != Some(path) || !entries.remove(file) {
            return Err("Member changed".into());
        }
        scan::eligible(file, tree)?;
        if safety::snapshot(file)? != child["stamp"] {
            return Err("File changed since scan".into());
        }
    }
    if !entries.is_empty() {
        return Err("New directory entries".into());
    }
    Ok(())
}
pub fn run(a: &Value) -> Result<Value> {
    let report = read_json(Path::new(required(a, "report")?))?;
    let selection = read_json(Path::new(required(a, "selection")?))?;
    let id = required(&report, "batch")?;
    if id.is_empty()
        || id.len() > 64
        || !id.bytes().all(|b| b.is_ascii_hexdigit() || b == b'-')
        || selection["batch"] != id
        || report["version"] != VERSION
    {
        return Err("Invalid batch or version".into());
    }
    let trusted = read_json(&state()?.join(format!("{id}.json")))?;
    if trusted != report {
        return Err("Report differs from local scan".into());
    }
    let ids = list(&selection, "ids")?
        .iter()
        .map(|v| v.as_str().ok_or("Invalid item ID"))
        .collect::<std::result::Result<BTreeSet<_>, _>>()?;
    if ids.is_empty() {
        return Err("Empty selection".into());
    }
    let rows: Vec<_> = list(&trusted, "items")?
        .iter()
        .filter(|v| ids.contains(v["id"].as_str().unwrap_or("")))
        .collect();
    if rows.len() != ids.len() || rows.iter().any(|r| r["selectable"] != true) {
        return Err("Unknown or protected selection".into());
    }
    let run = batch();
    let out = run_dir(required(a, "out")?, &run)?;
    let header = json!({"version":VERSION,"mode":"apply","batch":run,"source":id,"items":rows});
    write_new(&out.join("plan.json"), &serde_json::to_vec(&header)?)?;
    let mut log = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(out.join("events.jsonl"))?;
    // Reserve the batch once. The receipt points recovery to the original journal.
    let receipt = state()?.join(format!("{id}.applied"));
    if let Err(e) = write_new(
        &receipt,
        out.to_str().ok_or("Invalid output path")?.as_bytes(),
    ) {
        return Err(format!(
            "{e}: prior run {}",
            fs::read_to_string(receipt).unwrap_or_default()
        )
        .into());
    }
    eprintln!("run: {}", out.display());
    for row in rows {
        let key = &row["id"];
        let tree = Path::new(required(row, "tree")?);
        if let Err(e) = preflight(row) {
            event(
                &mut log,
                json!({"id":key,"status":"skipped","reason":e.to_string()}),
            )?;
            continue;
        }
        let mut members = list(row, "members")?.clone();
        members.push(json!({"path":row["path"],"stamp":row["stamp"]}));
        for entry in members {
            let path = Path::new(required(&entry, "path")?);
            let stage = path.with_file_name(format!(".agent-audit-{}", batch()));
            let mut started = json!({"id":key,"path":path,"status":"started"});
            if cfg!(target_os = "macos") {
                started["recovery_entry"] = json!(stage.join("entry"))
            }
            event(&mut log, started)?;
            let eligible = if row["rule"] == "setup-rotation" {
                scan::backup_eligible(path)
            } else {
                scan::eligible(path, tree)
            };
            let result = eligible.and_then(|_| safety::remove(path, &entry["stamp"], &stage));
            let outcome = match result {
                Ok(()) => {
                    json!({"id":key,"path":path,"status":"deleted","size":if entry["stamp"]["directory"]==true{0}else{entry["stamp"]["size"].as_u64().unwrap_or(0)}})
                }
                Err(e) => json!({"id":key,"path":path,"status":"failed","reason":e.to_string()}),
            };
            event(&mut log, outcome)?
        }
    }
    event(&mut log, json!({"status":"finished"}))?;
    reports::recover(&out)
}
