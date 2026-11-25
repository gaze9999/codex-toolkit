//! Offline, byte-accurate colored token view.

use crate::{encoding, grouped};
use unicode_segmentation::UnicodeSegmentation;

const PALETTE: [&str; 7] = [
    "#dbeafe", "#fce7f3", "#dcfce7", "#fef3c7", "#ede9fe", "#cffafe", "#ffedd5",
];

#[derive(Debug, Clone, PartialEq)]
pub struct Span {
    pub index: usize,
    pub id: u32,
    pub start: usize,
    pub end: usize,
    pub hex: String,
    pub text: String,
}

/// HTML escaping equal to Python `html.escape(text, quote=True)`.
pub fn escape(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for ch in text.chars() {
        match ch {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&#x27;"),
            _ => out.push(ch),
        }
    }
    out
}

/// UTF-8 decode where each invalid byte becomes `\xNN` (Python `backslashreplace`).
fn decode_backslash(mut bytes: &[u8]) -> String {
    let mut out = String::new();
    loop {
        match std::str::from_utf8(bytes) {
            Ok(text) => {
                out.push_str(text);
                return out;
            }
            Err(error) => {
                let valid = error.valid_up_to();
                out.push_str(std::str::from_utf8(&bytes[..valid]).unwrap_or_default());
                let bad = error.error_len().unwrap_or(bytes.len() - valid);
                for byte in &bytes[valid..valid + bad] {
                    out.push_str(&format!("\\x{byte:02x}"));
                }
                bytes = &bytes[valid + bad..];
            }
        }
    }
}

pub fn token_spans(text: &str, encoding_name: &str) -> Result<Vec<Span>, String> {
    let encoder = encoding(encoding_name)?;
    let mut offset = 0;
    let mut spans = Vec::new();
    for (index, id) in encoder.encode_ordinary(text).into_iter().enumerate() {
        let raw = encoder
            .decode_bytes(&[id])
            .map_err(|error| format!("無法解碼 Token {id}: {error:?}"))?;
        let hex = raw
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<Vec<_>>()
            .join(" ");
        spans.push(Span {
            index,
            id,
            start: offset,
            end: offset + raw.len(),
            hex,
            text: decode_backslash(&raw),
        });
        offset += raw.len();
    }
    if offset != text.len() {
        return Err("Token 位元組與來源文字長度不符".into());
    }
    Ok(spans)
}

/// Grapheme-level spans; a grapheme crossing tokens gets a gradient of their colors.
pub fn colored_text(text: &str, spans: &[Span], limit: usize) -> String {
    let mut pieces = String::new();
    let (mut offset, mut cursor) = (0usize, 0usize);
    for grapheme in text.graphemes(true) {
        let end = offset + grapheme.len();
        while cursor < spans.len() && spans[cursor].end <= offset {
            cursor += 1;
        }
        let (mut indexes, mut colors) = (Vec::new(), Vec::new());
        let mut scan = cursor;
        while scan < spans.len() && spans[scan].start < end {
            let span = &spans[scan];
            if span.index >= limit {
                return pieces;
            }
            let width = (end - offset) as f64;
            let left = (offset.max(span.start) - offset) as f64;
            let right = (end.min(span.end) - offset) as f64;
            indexes.push(span.index);
            colors.push(format!(
                "{} {:.2}% {:.2}%",
                PALETTE[span.index % PALETTE.len()],
                left / width * 100.0,
                right / width * 100.0
            ));
            scan += 1;
        }
        if indexes.is_empty() {
            break;
        }
        let background = if colors.len() > 1 {
            format!("linear-gradient(90deg,{})", colors.join(","))
        } else {
            PALETTE[indexes[0] % PALETTE.len()].to_string()
        };
        let ids = indexes
            .iter()
            .map(usize::to_string)
            .collect::<Vec<_>>()
            .join(",");
        pieces.push_str(&format!(
            "<span data-tokens=\"{ids}\" style=\"background:{background}\">{}</span>",
            escape(grapheme)
        ));
        offset = end;
    }
    pieces
}

/// Compact JSON with Python's default `", "` and `": "` separators.
fn detail_json(span: &Span) -> String {
    let quote = |text: &str| serde_json::to_string(text).unwrap_or_default();
    format!(
        "{{\"index\": {}, \"id\": {}, \"start\": {}, \"end\": {}, \"hex\": {}, \"text\": {}}}",
        span.index,
        span.id,
        span.start,
        span.end,
        quote(&span.hex),
        quote(&span.text)
    )
}

pub fn render_html(
    documents: &[(String, String)],
    encoding_name: &str,
    limit: usize,
) -> Result<String, String> {
    if limit < 1 {
        return Err("顯示 Token 數需大於 0".into());
    }
    let mut sections = String::new();
    let mut total = 0u64;
    for (number, (source, text)) in documents.iter().enumerate() {
        let spans = token_spans(text, encoding_name)?;
        total += spans.len() as u64;
        let shown = &spans[..spans.len().min(limit)];
        let buttons: String =
            shown
                .iter()
                .map(|row| {
                    let label = escape(&row.text);
                    format!(
                    "<button class=\"token\" data-index=\"{index}\" style=\"background:{color}\" \
                     aria-label=\"Token {number}, ID {id}\" data-detail=\"{detail}\">\
                     <small>#{number} · {id}</small><code>{code}</code></button>",
                    index = row.index,
                    color = PALETTE[row.index % PALETTE.len()],
                    number = row.index + 1,
                    id = row.id,
                    detail = escape(&detail_json(row)),
                    code = if label.is_empty() { "∅".into() } else { label },
                )
                })
                .collect();
        let buttons = if buttons.is_empty() {
            "<p>空文字 · 0 Token</p>".to_string()
        } else {
            buttons
        };
        sections.push_str(&format!(
            "<section data-document=\"{number}\">\n<h2>{source}</h2><p class=\"meta\">{tokens} Token · {chars} 字元 · {bytes} UTF-8 bytes · 顯示 {shown} Token</p>\n<pre class=\"colored\" aria-label=\"彩色 Token 文字\">{colored}</pre>\n<p class=\"detail\" aria-live=\"polite\">點選 Token 或使用 Tab 與 Enter 查看 ID 及位元組</p>\n<div class=\"tokens\">{buttons}</div></section>",
            source = escape(source),
            tokens = grouped(spans.len() as u64),
            chars = grouped(text.chars().count() as u64),
            bytes = grouped(text.len() as u64),
            shown = grouped(shown.len() as u64),
            colored = colored_text(text, &spans, limit),
        ));
    }
    Ok(format!(
        "{HEAD}{encoding} · {total} Token</p></header>{sections}{TAIL}",
        encoding = escape(encoding_name),
        total = grouped(total),
    ))
}

const HEAD: &str = r#"<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Token 彩色檢視</title><link rel="icon" href="data:,"><style>
:root{font-family:system-ui,"Microsoft JhengHei",sans-serif;color:#17243b;background:#f4f7fb;line-height:1.55}
*{box-sizing:border-box}body{margin:0}main{max-width:1120px;margin:32px auto;padding:0 24px 40px}
h1{font-size:30px;margin:0 0 8px}h2{font-size:19px;overflow-wrap:anywhere;margin:0}header{margin-bottom:24px}
.eyebrow{color:#3c5985;font-size:13px;letter-spacing:.1em}header p{margin:6px 0}.meta{color:#506078;font-size:14px}
section{background:white;border:1px solid #dbe3ef;border-radius:16px;padding:24px;margin:20px 0;box-shadow:0 6px 22px #17243b06}
.colored{white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;font:16px/2.1 ui-monospace,monospace;min-height:80px;padding:16px;background:#f9fbff;border:1px solid #e2e8f0;border-radius:10px}
.colored span{padding:3px 0}.colored span.selected{outline:2px solid #204e88;outline-offset:1px}
.tokens{display:flex;flex-wrap:wrap;gap:8px}.token{border:1px solid #ffffff;border-radius:8px;padding:9px 11px;min-height:48px;max-width:100%;color:#17243b;cursor:pointer;text-align:left}
.token small{display:block;font:11px system-ui;color:#38465c}.token code{white-space:pre-wrap;overflow-wrap:anywhere;font:14px ui-monospace,monospace}
.token:hover,.token[aria-pressed=true]{border-color:#204e88}.token:focus-visible{outline:3px solid #204e88;outline-offset:2px}
.detail{font:13px/1.7 ui-monospace,monospace;background:#edf2f8;padding:12px;border-radius:8px;overflow-wrap:anywhere;min-height:46px}
@media(max-width:600px){main{margin:20px auto;padding:0 12px 24px}section{padding:16px}h1{font-size:25px}.colored{padding:10px}}
</style></head><body><main><header><p class="eyebrow">TOKEN EXPLORER</p><h1>Token 彩色檢視</h1>
<p>"#;

const TAIL: &str = r#"</main><script>
for(const section of document.querySelectorAll('section')){
 function select(index){
  const buttons=section.querySelectorAll('.token');
  const button=[...buttons].find(item=>item.dataset.index===String(index));if(!button)return;
  const data=JSON.parse(button.dataset.detail);
  for(const item of buttons)item.setAttribute('aria-pressed',String(item===button));
  section.querySelector('.detail').textContent=`Token #${data.index+1} · ID ${data.id} · UTF-8 bytes ${data.start}–${data.end} · ${data.hex}`;
  for(const span of section.querySelectorAll('.colored span'))span.classList.toggle('selected',span.dataset.tokens.split(',').includes(String(index)));
 }
 for(const button of section.querySelectorAll('.token')){button.setAttribute('aria-pressed','false');button.addEventListener('click',()=>select(button.dataset.index));}
 section.querySelector('.colored').addEventListener('click',event=>{if(event.target.dataset.tokens)select(event.target.dataset.tokens.split(',')[0]);});
}
</script></body></html>"#;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn spans_cover_utf8_bytes() {
        let text = "繁體 emoji 👩‍💻";
        let spans = token_spans(text, "o200k_base").unwrap();
        assert_eq!(spans.last().unwrap().end, text.len());
        assert!(colored_text(text, &spans, 1).len() < colored_text(text, &spans, 2000).len());
    }

    #[test]
    fn escapes_like_python() {
        assert_eq!(
            escape("<a href='x'>&\""),
            "&lt;a href=&#x27;x&#x27;&gt;&amp;&quot;"
        );
        assert_eq!(decode_backslash(b"a\xe4\xb8"), "a\\xe4\\xb8");
    }
}
