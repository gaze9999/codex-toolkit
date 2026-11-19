//! Self-contained HTML reports from neutral report data (`report-html/v1`).
//! Markup follows the Workbench UI static class names, so the built-in styles and an appearance
//! package (a folder with `manifest.json` and a style file) are interchangeable.
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};

pub const SCHEMA: &str = "report-html/v1";
pub mod code;
pub mod output;
mod package;

pub use package::REQUIRED_CLASSES;

/// The built-in styles chosen at build time (src/default.css or REPORT_HTML_STYLE_DIR) and their label.
const BUILTIN: &str = include_str!(concat!(env!("OUT_DIR"), "/style.css"));
const BUILTIN_LABEL: &str = include_str!(concat!(env!("OUT_DIR"), "/style-label.txt"));
const TONES: [&str; 5] = ["neutral", "category", "success", "warning", "error"];
/// Report layout on top of either style source.
const PAGE: &str = "body{margin:0}.wb-card-head>h2{font-size:1.1rem}.rh-meta{color:var(--wb-muted);font-size:.85rem;margin:0 0 .6em;word-break:break-word}.rh-tags{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 .8em}.rh-stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}.rh-stat{display:flex;flex-direction:column;gap:6px;margin:0;padding:14px 16px;background:var(--wb-bg)}.rh-stat b{font-size:1.6rem;line-height:1;font-variant-numeric:tabular-nums;white-space:nowrap}.rh-stat b[data-tone=warning]{color:var(--wb-warning)}.rh-stat b[data-tone=success]{color:var(--wb-success)}.rh-stat b[data-tone=error]{color:var(--wb-error)}.rh-stat b[data-tone=category]{color:var(--wb-accent)}.rh-stat .wb-tag{align-self:flex-start}.rh-bar{margin-top:16px}.rh-tabs{display:flex;flex-wrap:wrap;gap:4px;margin:0 0 12px;border-bottom:1px solid var(--wb-border)}.rh-tabs [role=tab]{border:0;border-bottom:2px solid transparent;background:none;padding:6px 10px;font:inherit;color:inherit;cursor:pointer}.rh-tabs [role=tab][aria-selected=true]{border-bottom-color:var(--wb-accent);font-weight:600}.rh-count{margin-inline-start:6px;color:var(--wb-muted);font-size:.85em}.rh-num{text-align:end;font-variant-numeric:tabular-nums;white-space:nowrap}.rh-text{white-space:pre-line;overflow-wrap:break-word}.rh-nowrap{white-space:nowrap}.wb-table thead th{white-space:nowrap}.wb-filter{margin:0 0 8px}.wb-filter label{display:inline-flex;align-items:center;gap:6px}code{font-size:.85em;overflow-wrap:anywhere}.rh-code{margin:0;padding:6px 8px;border-radius:6px;background:var(--wb-code-bg,var(--wb-bg));white-space:pre-wrap;overflow-wrap:anywhere;tab-size:4;font-size:.85rem}.rh-code code{display:block;padding:0;background:none;font-size:inherit}.wb-table-striped tbody tr:nth-child(even) .rh-code{background:var(--wb-surface)}.rh-stat small{color:var(--wb-muted);font-size:.8rem}.rh-list{margin:0;padding-left:1.1em}.rh-list li{overflow-wrap:anywhere}.rh-tip{position:fixed;z-index:1000;max-width:min(480px,calc(100vw - 16px));padding:8px 10px;border:1px solid var(--wb-border);border-radius:6px;background:var(--wb-surface);color:var(--wb-text);box-shadow:0 4px 14px rgb(0 0 0 / .18);white-space:pre-line;overflow-wrap:anywhere;font-size:.85rem;line-height:1.5;pointer-events:none}.rh-tip[hidden]{display:none}.wb-detail{white-space:pre-line}.wb-table tbody tr[hidden]{display:none}.wb-table-striped td{vertical-align:top}.wb-table td>code{font-size:1em}.rh-id{white-space:nowrap}.wb-table td>code:not(.rh-id){display:inline-block;min-inline-size:min(18ch,100vw);max-inline-size:36ch;overflow-wrap:anywhere}.rh-long{width:clamp(13rem,23vw,23rem);max-width:100%;white-space:pre-line;overflow-wrap:anywhere}.rh-long summary{cursor:pointer;white-space:normal}.rh-info{width:auto}.rh-long[open] summary{margin-bottom:.35em}.wb-table-wrap .rh-text{overflow-wrap:anywhere}.wb-filter{display:flex;flex-wrap:wrap;gap:.5em 1em}";
const SCRIPT: &str = "const panels={};document.querySelectorAll('.rh-tabs').forEach(nav=>{const tabs=[...nav.querySelectorAll('[role=tab]')];const select=i=>tabs.forEach((t,j)=>{t.setAttribute('aria-selected',String(i===j));t.tabIndex=i===j?0:-1;document.getElementById(t.getAttribute('aria-controls')).hidden=i!==j;});tabs.forEach((t,i)=>{panels[t.getAttribute('aria-controls')]=()=>select(i);t.addEventListener('click',()=>select(i));t.addEventListener('keydown',e=>{const d={ArrowRight:1,ArrowLeft:-1}[e.key];if(d){const n=(i+d+tabs.length)%tabs.length;select(n);tabs[n].focus();}});});});const open=()=>{const f=panels[decodeURIComponent(location.hash.slice(1))];if(f)f();};document.querySelectorAll('a.wb-tag-link').forEach(a=>a.addEventListener('click',()=>{const f=panels[a.getAttribute('href').slice(1)];if(f)f();}));addEventListener('hashchange',open);open();document.querySelectorAll('.wb-filter[data-for]').forEach(box=>{const table=document.getElementById(box.dataset.for),input=box.querySelector('input'),selects=[...box.querySelectorAll('select')];const apply=()=>{const t=input.value.trim().toLowerCase();table.querySelectorAll('tbody tr').forEach(r=>{r.hidden=(!!t&&!r.textContent.toLowerCase().includes(t))||selects.some(s=>s.value&&r.dataset['f'+s.dataset.filter]!==s.value);});};input.addEventListener('input',apply);selects.forEach(s=>s.addEventListener('input',apply));});document.querySelectorAll('.wb-count-matrix .wb-count').forEach(b=>b.addEventListener('click',()=>{const box=b.closest('.rh-matrix').querySelector('.wb-detail');box.textContent=b.dataset.detail;}));const tip=document.createElement('div');tip.className='rh-tip';tip.setAttribute('role','tooltip');tip.hidden=true;document.querySelector('.wb-workbench').append(tip);const hide=()=>{tip.hidden=true;};const show=n=>{tip.textContent=n.dataset.detail;tip.hidden=false;const r=n.getBoundingClientRect(),t=tip.getBoundingClientRect(),gap=8;let top=r.bottom+gap;if(top+t.height>innerHeight)top=Math.max(gap,r.top-t.height-gap);tip.style.top=top+'px';tip.style.left=Math.max(gap,Math.min(r.left,innerWidth-t.width-gap))+'px';};document.querySelectorAll('.wb-flow-node[data-detail]').forEach(n=>{n.addEventListener('mouseenter',()=>show(n));n.addEventListener('focus',()=>show(n));n.addEventListener('mouseleave',hide);n.addEventListener('blur',hide);});document.addEventListener('keydown',e=>{if(e.key==='Escape')hide();});addEventListener('scroll',hide,{passive:true});";

/// Styles embedded in the page and the label that names their source.
pub struct Style {
    css: String,
    label: String,
}

impl Style {
    pub fn builtin() -> Self {
        Self {
            css: BUILTIN.into(),
            label: BUILTIN_LABEL.into(),
        }
    }

    /// Loads an appearance package and checks its class list and style SHA-256 against the manifest.
    pub fn load(dir: &Path) -> Result<Self, String> {
        let package = package::load(dir)?;
        Ok(Self {
            css: package.css,
            label: format!(
                "外觀套件 {} (SHA-256 {})",
                package.version,
                &package.sha256[..12]
            ),
        })
    }

    pub fn label(&self) -> &str {
        &self.label
    }
}

/// Escapes text for HTML content and attribute values.
pub fn escape(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for ch in text.chars() {
        match ch {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&#39;"),
            other => out.push(other),
        }
    }
    out
}

fn plain(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::String(s) => s.clone(),
        other => other.to_string(),
    }
}
fn text(value: &Value) -> String {
    escape(&plain(value))
}
fn items<'a>(value: &'a Value, name: &str) -> Result<&'a [Value], String> {
    match value {
        Value::Null => Ok(&[]),
        Value::Array(list) => Ok(list),
        _ => Err(format!("{name} must be a list")),
    }
}
fn tone(value: &Value) -> Result<String, String> {
    match value.as_str() {
        None if value.is_null() => Ok(String::new()),
        Some(name) if TONES.contains(&name) => Ok(format!(" data-tone=\"{name}\"")),
        _ => Err(format!("tone must be one of {}", TONES.join(", "))),
    }
}
fn heading<'a>(report: &'a Value, key: &str, default: &'a str) -> String {
    escape(report["headings"][key].as_str().unwrap_or(default))
}
fn card(title: &str, body: &str) -> String {
    format!("<section class=\"wb-card\"><div class=\"wb-card-head\"><h2>{title}</h2></div><div class=\"wb-card-body\">{body}</div></section>\n")
}

fn table(id: &str, section: &Value, search: &str, placeholder: &str) -> Result<String, String> {
    let columns = items(&section["columns"], "section columns")?;
    if columns.is_empty() {
        return Err("A section needs at least one column".into());
    }
    let rows = items(&section["rows"], "section rows")?;
    if rows.is_empty() {
        return Ok(format!(
            "<p class=\"wb-muted\">{}</p>",
            escape(section["empty"].as_str().unwrap_or("沒有資料"))
        ));
    }
    let mut kinds = Vec::new();
    let mut head = String::new();
    for column in columns {
        let key = column["key"]
            .as_str()
            .filter(|key| !key.is_empty())
            .ok_or("A column needs a key")?;
        let kind = column["kind"].as_str().unwrap_or("text");
        if !["text", "number", "code", "source"].contains(&kind) {
            return Err(format!(
                "Unknown column kind {kind:?}; use text, number, code or source"
            ));
        }
        let lang = match column["lang"].as_str() {
            Some(name) => Some(code::find(name)?),
            None if column["lang"].is_null() => None,
            None => return Err("Column lang must be text".into()),
        };
        head.push_str(&format!(
            "<th scope=\"col\"{}>{}</th>",
            if kind == "number" {
                " class=\"rh-num\""
            } else {
                ""
            },
            escape(column["label"].as_str().unwrap_or(key))
        ));
        kinds.push((key, kind, lang));
    }
    // Each filter is a select over the distinct values of one column, combined with the keyword search
    let mut filters = Vec::new();
    for filter in items(&section["filters"], "section filters")? {
        let key = filter["key"]
            .as_str()
            .filter(|key| !key.is_empty())
            .ok_or("A filter needs a key")?;
        let mut values: Vec<String> = Vec::new();
        for row in rows {
            let value = plain(&row[key]);
            if !value.is_empty() && !values.contains(&value) {
                values.push(value);
            }
        }
        filters.push((key, escape(filter["label"].as_str().unwrap_or(key)), values));
    }
    let body: String = rows
        .iter()
        .map(|row| {
            let cells: String = kinds
                .iter()
                .map(|(key, kind, lang)| {
                    if *kind == "source" {
                        let source = plain(&row[*key]);
                        if source.is_empty() {
                            return "<td></td>".to_owned();
                        }
                        let lang = lang.unwrap_or(&code::LANGS[0]);
                        return format!(
                            "<td><pre class=\"rh-code\"><code data-lang=\"{}\">{}</code></pre></td>",
                            lang.name,
                            code::highlight(&source, lang)
                        );
                    }
                    let raw = plain(&row[*key]);
                    let value = escape(&raw);
                    match *kind {
                        "number" => format!("<td class=\"rh-num\">{value}</td>"),
                        "code" if raw.len() <= 40 && raw.bytes().all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_')) => {
                            format!("<td><code class=\"rh-id\">{value}</code></td>")
                        }
                        "code" if !value.is_empty() => format!("<td><code>{value}</code></td>"),
                        "text" if raw.chars().count() > 100 => {
                            let preview: String = raw.chars().take(52).collect();
                            format!("<td><details class=\"rh-long\"><summary>{}…</summary>{value}</details></td>", escape(&preview))
                        }
                        // Short single-line values such as status labels stay on one line
                        _ if value.chars().count() <= 12 && !value.contains('\n') => {
                            format!("<td><span class=\"rh-text rh-nowrap\">{value}</span></td>")
                        }
                        _ => format!("<td><span class=\"rh-text\">{value}</span></td>"),
                    }
                })
                .collect();
            let marks: String = filters
                .iter()
                .enumerate()
                .map(|(i, (key, _, _))| format!(" data-f{i}=\"{}\"", text(&row[*key])))
                .collect();
            format!("<tr{marks}>{cells}</tr>")
        })
        .collect();
    let selects: String = filters
        .iter()
        .enumerate()
        .map(|(i, (_, label, values))| {
            let options: String = values
                .iter()
                .map(|value| format!("<option>{}</option>", escape(value)))
                .collect();
            format!("<label>{label} <select data-filter=\"{i}\"><option value=\"\">{}</option>{options}</select></label>", escape("全部"))
        })
        .collect();
    Ok(format!("<div class=\"wb-filter\" data-for=\"{id}\">{selects}<label>{search} <input type=\"search\" placeholder=\"{placeholder}\"></label></div><div class=\"wb-table-wrap\"><table class=\"wb-table wb-table-striped\" id=\"{id}\"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"))
}

/// Stat-like cards: a value, a label, an optional note, tone and hover text per item.
fn cards(section: &Value) -> Result<(String, usize), String> {
    let list = items(&section["items"], "cards items")?;
    if list.is_empty() {
        return Ok((empty(section), 0));
    }
    let mut out = String::new();
    for item in list {
        let tone = tone(&item["tone"])?;
        let title = match plain(&item["title"]) {
            hint if hint.is_empty() => String::new(),
            hint => format!(" title=\"{}\"", escape(&hint)),
        };
        let note = match plain(&item["note"]) {
            note if note.is_empty() => String::new(),
            note => format!("<small>{}</small>", escape(&note)),
        };
        out.push_str(&format!(
            "<div class=\"wb-card rh-stat\"{tone}{title}><b{tone}>{}</b><span>{}</span>{note}</div>",
            text(&item["value"]),
            text(&item["label"])
        ));
    }
    Ok((format!("<div class=\"rh-stats\">{out}</div>"), list.len()))
}

fn empty(section: &Value) -> String {
    format!(
        "<p class=\"wb-muted\">{}</p>",
        escape(section["empty"].as_str().unwrap_or("沒有資料"))
    )
}

/// A left-to-right flow: nodes stacked in named columns, curved edges, hover or focus shows the node detail.
fn flow(section: &Value) -> Result<(String, usize), String> {
    let nodes = items(&section["nodes"], "flow nodes")?;
    if nodes.is_empty() {
        return Ok((empty(section), 0));
    }
    let columns: Vec<String> = items(&section["columns"], "flow columns")?
        .iter()
        .map(plain)
        .collect();
    let (col_width, row_height, node_width, node_height, pad) =
        (230u64, 64u64, 200u64, 44u64, 24u64);
    let mut counts = vec![0u64; columns.len()];
    let mut places = std::collections::HashMap::new();
    let mut boxes = String::new();
    for node in nodes {
        let id = plain(&node["id"]);
        let column = columns
            .iter()
            .position(|name| *name == plain(&node["column"]))
            .ok_or_else(|| format!("Flow node {id:?} names an unknown column"))?;
        let (x, y) = (
            pad + column as u64 * col_width,
            pad + 28 + counts[column] * row_height,
        );
        counts[column] += 1;
        places.insert(id, (x, y));
        let label = plain(&node["label"]);
        let short = if label.chars().count() > 24 {
            format!("{}…", label.chars().take(23).collect::<String>())
        } else {
            label.clone()
        };
        let detail = match plain(&node["detail"]) {
            detail if detail.is_empty() => label.clone(),
            detail => detail,
        };
        boxes.push_str(&format!(
            "<g class=\"wb-flow-node\"{} tabindex=\"0\" aria-label=\"{detail}\" data-detail=\"{detail}\"><rect x=\"{x}\" y=\"{y}\" width=\"{node_width}\" height=\"{node_height}\" rx=\"6\"/><text x=\"{}\" y=\"{}\">{}</text></g>",
            tone(&node["tone"])?,
            x + 10,
            y + 27,
            escape(&short),
            detail = escape(&detail)
        ));
    }
    let mut edges = String::new();
    for edge in items(&section["edges"], "flow edges")? {
        let (Some(&(ax, ay)), Some(&(bx, by))) = (
            places.get(&plain(&edge["from"])),
            places.get(&plain(&edge["to"])),
        ) else {
            continue;
        };
        let (x1, y1, x2, y2) = (
            ax + node_width,
            ay + node_height / 2,
            bx,
            by + node_height / 2,
        );
        let mid = (x1 + x2) / 2;
        edges.push_str(&format!("<path class=\"wb-flow-edge\" d=\"M{x1},{y1} C{mid},{y1} {mid},{y2} {x2},{y2}\" marker-end=\"url(#rh-arrow)\"/>"));
    }
    let heads: String = columns
        .iter()
        .enumerate()
        .map(|(i, name)| {
            format!(
                "<text class=\"wb-flow-head\" x=\"{}\" y=\"{}\">{}</text>",
                pad + i as u64 * col_width,
                pad + 12,
                escape(name)
            )
        })
        .collect();
    let width = pad * 2 + (columns.len().max(1) as u64) * col_width - (col_width - node_width);
    let height = pad * 2 + 28 + counts.iter().copied().max().unwrap_or(1).max(1) * row_height;
    let label = escape(section["label"].as_str().unwrap_or("flow"));
    Ok((format!("<div class=\"wb-scroll\"><svg class=\"wb-flow\" viewBox=\"0 0 {width} {height}\" width=\"{width}\" height=\"{height}\" role=\"img\" aria-label=\"{label}\"><defs><marker id=\"rh-arrow\" viewBox=\"0 0 10 10\" refX=\"9\" refY=\"5\" markerWidth=\"7\" markerHeight=\"7\" orient=\"auto-start-reverse\"><path d=\"M0,0 L10,5 L0,10 z\" class=\"wb-flow-arrow\"/></marker></defs>{heads}{edges}{boxes}</svg></div>"), nodes.len()))
}

/// A count matrix: row labels against column labels, each cell a toned count whose detail shows below on click.
fn matrix(section: &Value) -> Result<(String, usize), String> {
    let rows = items(&section["rows"], "matrix rows")?;
    if rows.is_empty() {
        return Ok((empty(section), 0));
    }
    let columns = items(&section["columns"], "matrix columns")?;
    let head: String = columns
        .iter()
        .map(|column| format!("<th scope=\"col\">{}</th>", text(column)))
        .collect();
    let mut body = String::new();
    for row in rows {
        let cells = items(&row["cells"], "matrix cells")?;
        let mut line = format!("<tr><th scope=\"row\">{}</th>", text(&row["label"]));
        for i in 0..columns.len() {
            match cells.get(i) {
                Some(cell) if !cell.is_null() => line.push_str(&format!(
                    "<td><button type=\"button\" class=\"wb-count\"{} data-detail=\"{}\" aria-label=\"{}\">{}</button></td>",
                    tone(&cell["tone"])?,
                    text(&cell["detail"]),
                    text(&cell["label"]),
                    text(&cell["value"])
                )),
                _ => line.push_str("<td></td>"),
            }
        }
        body.push_str(&line);
        body.push_str("</tr>");
    }
    let corner = text(&section["corner"]);
    let hint = escape(section["hint"].as_str().unwrap_or(""));
    Ok((format!("<div class=\"rh-matrix\"><div class=\"wb-scroll\"><table class=\"wb-table wb-count-matrix\"><thead><tr><th scope=\"col\">{corner}</th>{head}</tr></thead><tbody>{body}</tbody></table></div><div class=\"wb-detail\" aria-live=\"polite\">{hint}</div></div>"), rows.len()))
}

/// One section body by kind (table by default) and the count shown on its tab.
fn block(
    id: &str,
    section: &Value,
    search: &str,
    placeholder: &str,
) -> Result<(String, Option<usize>), String> {
    let (html, count) = match section["kind"].as_str().unwrap_or("table") {
        "table" => (
            table(id, section, search, placeholder)?,
            Some(items(&section["rows"], "section rows")?.len()),
        ),
        "cards" => cards(section).map(|(html, n)| (html, Some(n)))?,
        "flow" => flow(section).map(|(html, n)| (html, Some(n)))?,
        "matrix" => matrix(section).map(|(html, n)| (html, Some(n)))?,
        "list" => {
            let list = items(&section["items"], "list items")?;
            let html = if list.is_empty() {
                empty(section)
            } else {
                format!(
                    "<ul class=\"rh-list\">{}</ul>",
                    list.iter()
                        .map(|item| format!(
                            "<li><span class=\"rh-text\">{}</span></li>",
                            text(item)
                        ))
                        .collect::<String>()
                )
            };
            (html, Some(list.len()))
        }
        "text" => (
            format!("<p class=\"rh-text\">{}</p>", text(&section["text"])),
            None,
        ),
        other => {
            return Err(format!(
                "Unknown section kind {other:?}; use table, cards, flow, matrix, list or text"
            ))
        }
    };
    let count = match &section["count"] {
        Value::Null => count,
        value => Some(
            value
                .as_u64()
                .ok_or("section count must be a whole number")? as usize,
        ),
    };
    let note = match section["note"].as_str() {
        Some(note) if !note.is_empty() => format!("<p class=\"rh-meta\">{}</p>", escape(note)),
        _ => String::new(),
    };
    let mut tags = String::new();
    for tag in items(&section["tags"], "section tags")? {
        tags.push_str(&format!(
            "<span class=\"wb-tag\"{}>{}</span>",
            tone(&tag["tone"])?,
            text(&tag["label"])
        ));
    }
    let tags = if tags.is_empty() {
        tags
    } else {
        format!("<p class=\"rh-tags\">{tags}</p>")
    };
    Ok((format!("{tags}{note}{html}"), count))
}

fn check_schema(report: &Value) -> Result<(), String> {
    if report["schema"] == SCHEMA {
        Ok(())
    } else {
        Err(format!("Report data needs \"schema\": \"{SCHEMA}\""))
    }
}

/// Renders report data as one offline page. Every value from the data is escaped.
pub fn render(report: &Value, style: &Style) -> Result<String, String> {
    check_schema(report)?;
    let title = report["title"]
        .as_str()
        .filter(|title| !title.trim().is_empty())
        .ok_or("Report data needs a title")?;
    let title = escape(title);
    let lang = escape(report["lang"].as_str().unwrap_or("zh-Hant-TW"));
    let mut parts = String::new();

    let mut tags = String::new();
    for tag in items(&report["tags"], "tags")? {
        tags.push_str(&format!(
            "<span class=\"wb-tag\"{}>{}</span>",
            tone(&tag["tone"])?,
            text(&tag["label"])
        ));
    }
    let mut info = String::new();
    for row in items(&report["info"], "info")? {
        let pair = row.as_array().filter(|pair| pair.len() == 2);
        let pair = pair.ok_or("Each info row is a [label, value] pair")?;
        // Long values such as path or pending lists fold like long table cells
        let raw = plain(&pair[1]);
        let value = if raw.chars().count() > 100 {
            let preview: String = raw.chars().take(52).collect();
            format!(
                "<details class=\"rh-long rh-info\"><summary>{}…</summary>{}</details>",
                escape(&preview),
                escape(&raw)
            )
        } else {
            format!("<span class=\"rh-text\">{}</span>", text(&pair[1]))
        };
        info.push_str(&format!(
            "<tr><th scope=\"row\">{}</th><td>{value}</td></tr>",
            text(&pair[0])
        ));
    }
    info.push_str(&format!(
        "<tr><th scope=\"row\">{}</th><td>report-html {} ({SCHEMA})</td></tr>",
        heading(report, "renderer", "報告產生器"),
        env!("CARGO_PKG_VERSION")
    ));
    info.push_str(&format!(
        "<tr><th scope=\"row\">{}</th><td><span class=\"rh-text\">{}</span></td></tr>",
        heading(report, "style", "外觀樣式"),
        escape(&style.label)
    ));
    let tags = if tags.is_empty() {
        tags
    } else {
        format!("<p class=\"rh-tags\">{tags}</p>")
    };
    parts.push_str(&card(
        &heading(report, "info", "基本資訊"),
        &format!("{tags}<div class=\"wb-table-wrap\"><table class=\"wb-table\"><tbody>{info}</tbody></table></div>"),
    ));

    let stats = items(&report["stats"], "stats")?;
    let section_count = items(&report["sections"], "sections")?.len();
    if !stats.is_empty() {
        let mut cards = String::new();
        let (mut segments, mut legend, mut total) = (String::new(), String::new(), 0u64);
        for stat in stats {
            let tone = tone(&stat["tone"])?;
            let label = text(&stat["label"]);
            // "section" names the tab, by position, that holds the rows behind the count
            let caption = match &stat["section"] {
                Value::Null => format!("<span>{label}</span>"),
                index => match index.as_u64().filter(|i| (*i as usize) < section_count) {
                    Some(i) => format!("<a class=\"wb-tag wb-tag-link\"{tone} data-outlined=\"false\" href=\"#panel{i}\">{label}</a>"),
                    None => return Err(format!("stat section must be a section position below {section_count}")),
                },
            };
            cards.push_str(&format!(
                "<div class=\"wb-card rh-stat\"><b{tone}>{}</b>{caption}</div>",
                text(&stat["value"])
            ));
            // Positive whole numbers with "bar": true form the distribution bar
            if let Some(count) = stat["value"]
                .as_u64()
                .filter(|n| *n > 0 && stat["bar"] == true)
            {
                let tone = if tone.is_empty() {
                    " data-tone=\"neutral\"".to_owned()
                } else {
                    tone
                };
                segments.push_str(&format!(
                    "<span{tone} style=\"flex:{count}\" title=\"{label} {count}\"></span>"
                ));
                legend.push_str(&format!(
                    "<li><span class=\"wb-legend-dot\"{tone}></span>{label} {count}</li>"
                ));
                total += count;
            }
        }
        let note = match report["note"].as_str() {
            Some(note) if !note.is_empty() => format!("<p class=\"rh-meta\">{}</p>", escape(note)),
            _ => String::new(),
        };
        let bar = if total == 0 {
            String::new()
        } else {
            format!("<div class=\"rh-bar\"><div class=\"wb-status-bar\" role=\"img\" aria-label=\"{} {total}\">{segments}</div><ul class=\"wb-legend\">{legend}</ul></div>", heading(report, "distribution", "筆數分布, 合計"))
        };
        parts.push_str(&card(
            &heading(report, "stats", "結果筆數"),
            &format!("{note}<div class=\"rh-stats\">{cards}</div>{bar}"),
        ));
    }

    let search = heading(report, "search", "搜尋");
    let placeholder = heading(report, "placeholder", "關鍵字");
    // Panels are standalone cards between the stats and the tabbed sections
    for (i, panel) in items(&report["panels"], "panels")?.iter().enumerate() {
        let (body, _) = block(&format!("p{i}"), panel, &search, &placeholder)?;
        parts.push_str(&card(&text(&panel["label"]), &body));
    }

    let sections = items(&report["sections"], "sections")?;
    if !sections.is_empty() {
        let (mut tabs, mut panels) = (String::new(), String::new());
        for (i, section) in sections.iter().enumerate() {
            let (body, count) = block(&format!("t{i}"), section, &search, &placeholder)?;
            let count = count.map_or(String::new(), |n| {
                format!("<span class=\"rh-count\">{n}</span>")
            });
            tabs.push_str(&format!(
                "<button type=\"button\" role=\"tab\" id=\"tab{i}\" aria-controls=\"panel{i}\" aria-selected=\"{}\" tabindex=\"{}\">{}{count}</button>",
                i == 0,
                if i == 0 { 0 } else { -1 },
                text(&section["label"])
            ));
            panels.push_str(&format!(
                "<div role=\"tabpanel\" id=\"panel{i}\" aria-labelledby=\"tab{i}\"{}>{body}</div>",
                if i == 0 { "" } else { " hidden" },
            ));
        }
        parts.push_str(&card(
            &heading(report, "sections", "明細"),
            &format!("<div class=\"rh-tabs\" role=\"tablist\">{tabs}</div>{panels}"),
        ));
    }
    Ok(format!(
        "<!doctype html>\n<html lang=\"{lang}\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<title>{title}</title>\n<style>{}</style>\n<style>{PAGE}</style></head><body><main class=\"wb-workbench wb-page\" data-wb-mode=\"auto\"><div class=\"wb-page-content\">\n<h1>{title}</h1>\n{parts}</div></main>\n<script>{SCRIPT}</script></body></html>\n",
        style.css
    ))
}

/// Creates a new report folder: the given path, or `<prefix>-<time>-<pid>-<sequence>` under the system
/// temporary directory. The folder must be new and outside every `scanned` root, so a read-only
/// tool never writes into a tree it inspects. Returns the canonical path.
pub fn new_folder(out: Option<&Path>, scanned: &[&Path], prefix: &str) -> Result<PathBuf, String> {
    if prefix.is_empty() || prefix.contains(['/', '\\']) || matches!(prefix, "." | "..") {
        return Err("Report prefix must be a filename component".into());
    }
    static NEXT_REPORT: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let out = match out {
        Some(path) => std::path::absolute(path).map_err(|e| e.to_string())?,
        None => {
            let stamp = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map_or(0, |d| d.as_nanos());
            let sequence = NEXT_REPORT.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            std::env::temp_dir().join(format!(
                "{prefix}-{stamp}-{}-{sequence}",
                std::process::id()
            ))
        }
    };
    if out.exists() {
        return Err(format!("Output already exists: {}", out.display()));
    }
    let parent = out.parent().ok_or("Output needs a parent folder")?;
    // Resolve the nearest existing ancestor before creating any directories.
    let mut ancestor = parent;
    while !ancestor.exists() {
        ancestor = ancestor
            .parent()
            .ok_or("Output needs an existing ancestor")?;
    }
    let resolved = fs::canonicalize(ancestor).map_err(|e| e.to_string())?;
    let pending = parent.strip_prefix(ancestor).map_err(|e| e.to_string())?;
    if pending
        .components()
        .any(|part| matches!(part, std::path::Component::ParentDir))
    {
        return Err("Output through a missing parent cannot contain ..".into());
    }
    let destination = resolved.join(pending);
    for root in scanned {
        let root = fs::canonicalize(root).map_err(|e| e.to_string())?;
        if destination.starts_with(root) {
            return Err("Keep report output outside the scanned root".into());
        }
    }
    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    fs::create_dir(&out).map_err(|e| e.to_string())?;
    fs::canonicalize(&out).map_err(|e| e.to_string())
}

fn markdown_cell(value: &Value) -> String {
    plain(value)
        .replace('|', "\\|")
        .replace('\r', "")
        .replace('\n', "<br>")
}

/// Renders the same report data as Markdown: title, info, stats and one table per section.
pub fn markdown(report: &Value) -> Result<String, String> {
    check_schema(report)?;
    let title = report["title"]
        .as_str()
        .filter(|title| !title.trim().is_empty())
        .ok_or("Report data needs a title")?;
    let mut out = format!("# {}\n", markdown_cell(&Value::from(title)));
    let tags: Vec<String> = items(&report["tags"], "tags")?
        .iter()
        .map(|tag| markdown_cell(&tag["label"]))
        .collect();
    if !tags.is_empty() {
        out.push_str(&format!("\n{}\n", tags.join(" · ")));
    }
    let info = items(&report["info"], "info")?;
    if !info.is_empty() {
        out.push_str(&format!(
            "\n## {}\n\n| | |\n| --- | --- |\n",
            report["headings"]["info"].as_str().unwrap_or("基本資訊")
        ));
        for row in info {
            let pair = row.as_array().filter(|pair| pair.len() == 2);
            let pair = pair.ok_or("Each info row is a [label, value] pair")?;
            out.push_str(&format!(
                "| {} | {} |\n",
                markdown_cell(&pair[0]),
                markdown_cell(&pair[1])
            ));
        }
    }
    let stats = items(&report["stats"], "stats")?;
    if !stats.is_empty() {
        out.push_str(&format!(
            "\n## {}\n\n",
            report["headings"]["stats"].as_str().unwrap_or("結果筆數")
        ));
        if let Some(note) = report["note"].as_str().filter(|note| !note.is_empty()) {
            out.push_str(&format!("{note}\n\n"));
        }
        out.push_str("| | |\n| --- | --- |\n");
        for stat in stats {
            out.push_str(&format!(
                "| {} | {} |\n",
                markdown_cell(&stat["label"]),
                markdown_cell(&stat["value"])
            ));
        }
    }
    for section in items(&report["panels"], "panels")?
        .iter()
        .chain(items(&report["sections"], "sections")?)
    {
        out.push_str(&format!("\n## {}\n\n", markdown_cell(&section["label"])));
        out.push_str(&markdown_block(section)?);
    }
    Ok(out)
}

/// One section or panel as Markdown, by kind.
fn markdown_block(section: &Value) -> Result<String, String> {
    let mut out = String::new();
    let tags: Vec<String> = items(&section["tags"], "section tags")?
        .iter()
        .map(|tag| markdown_cell(&tag["label"]))
        .collect();
    if !tags.is_empty() {
        out.push_str(&format!("{}\n\n", tags.join(" · ")));
    }
    if let Some(note) = section["note"].as_str().filter(|note| !note.is_empty()) {
        out.push_str(&format!("{note}\n\n"));
    }
    let empty = section["empty"].as_str().unwrap_or("沒有資料");
    let table = |head: Vec<String>, rows: Vec<Vec<String>>| {
        let mut text = format!(
            "| {} |\n| {} |\n",
            head.join(" | "),
            vec!["---"; head.len()].join(" | ")
        );
        for row in rows {
            text.push_str(&format!("| {} |\n", row.join(" | ")));
        }
        text
    };
    match section["kind"].as_str().unwrap_or("table") {
        "table" => {
            let columns = items(&section["columns"], "section columns")?;
            if columns.is_empty() {
                return Err("A section needs at least one column".into());
            }
            let rows = items(&section["rows"], "section rows")?;
            if rows.is_empty() {
                out.push_str(&format!("{empty}\n"));
                return Ok(out);
            }
            let mut keys = Vec::new();
            let mut head = Vec::new();
            for column in columns {
                let key = column["key"]
                    .as_str()
                    .filter(|key| !key.is_empty())
                    .ok_or("A column needs a key")?;
                head.push(markdown_cell(&Value::from(
                    column["label"].as_str().unwrap_or(key),
                )));
                keys.push(key);
            }
            out.push_str(&table(
                head,
                rows.iter()
                    .map(|row| keys.iter().map(|key| markdown_cell(&row[*key])).collect())
                    .collect(),
            ));
        }
        "cards" => {
            let list = items(&section["items"], "cards items")?;
            if list.is_empty() {
                out.push_str(&format!("{empty}\n"));
            } else {
                out.push_str(&table(
                    vec![String::new(), String::new(), String::new()],
                    list.iter()
                        .map(|item| {
                            vec![
                                markdown_cell(&item["label"]),
                                markdown_cell(&item["value"]),
                                markdown_cell(&item["note"]),
                            ]
                        })
                        .collect(),
                ));
            }
        }
        "list" => {
            let list = items(&section["items"], "list items")?;
            if list.is_empty() {
                out.push_str(&format!("{empty}\n"));
            }
            for item in list {
                out.push_str(&format!("- {}\n", markdown_cell(item)));
            }
        }
        "text" => out.push_str(&format!("{}\n", plain(&section["text"]))),
        "flow" => {
            let nodes = items(&section["nodes"], "flow nodes")?;
            if nodes.is_empty() {
                out.push_str(&format!("{empty}\n"));
            }
            let label = |id: &Value| {
                nodes
                    .iter()
                    .find(|node| node["id"] == *id)
                    .map_or_else(|| plain(id), |node| plain(&node["label"]))
            };
            for node in nodes {
                out.push_str(&format!(
                    "- {}: {}\n",
                    markdown_cell(&node["column"]),
                    markdown_cell(&node["label"])
                ));
            }
            for edge in items(&section["edges"], "flow edges")? {
                out.push_str(&format!(
                    "- {} → {}\n",
                    label(&edge["from"]),
                    label(&edge["to"])
                ));
            }
        }
        "matrix" => {
            let rows = items(&section["rows"], "matrix rows")?;
            if rows.is_empty() {
                out.push_str(&format!("{empty}\n"));
                return Ok(out);
            }
            let columns = items(&section["columns"], "matrix columns")?;
            let mut head = vec![markdown_cell(&section["corner"])];
            head.extend(columns.iter().map(markdown_cell));
            let mut lines = Vec::new();
            for row in rows {
                let cells = items(&row["cells"], "matrix cells")?;
                let mut line = vec![markdown_cell(&row["label"])];
                line.extend((0..columns.len()).map(|i| {
                    cells
                        .get(i)
                        .map_or(String::new(), |cell| markdown_cell(&cell["value"]))
                }));
                lines.push(line);
            }
            out.push_str(&table(head, lines));
        }
        other => {
            return Err(format!(
                "Unknown section kind {other:?}; use table, cards, flow, matrix, list or text"
            ))
        }
    }
    Ok(out)
}
