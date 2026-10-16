"""Create an offline, byte-accurate colored token view."""
from __future__ import annotations

from html import escape
import json


PALETTE = ("#dbeafe", "#fce7f3", "#dcfce7", "#fef3c7", "#ede9fe", "#cffafe", "#ffedd5")


def token_spans(text: str, encoding_name: str) -> list[dict]:
    import tiktoken

    encoder = tiktoken.get_encoding(encoding_name)
    offset, spans = 0, []
    for index, token_id in enumerate(encoder.encode_ordinary(text)):
        raw = encoder.decode_single_token_bytes(token_id)
        spans.append({"index": index, "id": token_id, "start": offset, "end": offset + len(raw),
                      "hex": raw.hex(" "), "text": raw.decode("utf-8", errors="backslashreplace")})
        offset += len(raw)
    if offset != len(text.encode("utf-8")):
        raise ValueError("Token 位元組與來源文字長度不符")
    return spans


def colored_text(text: str, spans: list[dict], limit: int) -> str:
    import regex

    pieces, offset, cursor = [], 0, 0
    for char in regex.findall(r"\X", text):
        end = offset + len(char.encode("utf-8"))
        while cursor < len(spans) and spans[cursor]["end"] <= offset:
            cursor += 1
        indexes, colors, scan = [], [], cursor
        while scan < len(spans) and spans[scan]["start"] < end:
            span = spans[scan]
            if span["index"] >= limit:
                return "".join(pieces)
            left = max(offset, span["start"]) - offset
            right = min(end, span["end"]) - offset
            indexes.append(span["index"])
            color = PALETTE[span["index"] % len(PALETTE)]
            colors.append(f"{color} {left / (end - offset) * 100:.2f}% {right / (end - offset) * 100:.2f}%")
            scan += 1
        if not indexes:
            break
        background = f"linear-gradient(90deg,{','.join(colors)})" if len(colors) > 1 else PALETTE[indexes[0] % len(PALETTE)]
        ids = ",".join(str(index) for index in indexes)
        pieces.append(f'<span data-tokens="{ids}" style="background:{background}">{escape(char)}</span>')
        offset = end
    return "".join(pieces)


def render_html(documents: list[tuple[str, str]], encoding_name: str, limit: int = 2000) -> str:
    if limit < 1:
        raise ValueError("顯示 Token 數需大於 0")
    sections = []
    total = 0
    for number, (source, text) in enumerate(documents):
        spans = token_spans(text, encoding_name)
        total += len(spans)
        shown = spans[:limit]
        token_buttons = "".join(
            f'<button class="token" data-index="{row["index"]}" style="background:{PALETTE[row["index"] % len(PALETTE)]}" '
            f'aria-label="Token {row["index"] + 1}, ID {row["id"]}" '
            f'data-detail="{escape(json.dumps(row, ensure_ascii=False), quote=True)}">'
            f'<small>#{row["index"] + 1} · {row["id"]}</small><code>{escape(row["text"]) or "∅"}</code></button>'
            for row in shown)
        sections.append(f'''<section data-document="{number}">
<h2>{escape(source)}</h2><p class="meta">{len(spans):,} Token · {len(text):,} 字元 · {len(text.encode('utf-8')):,} UTF-8 bytes · 顯示 {len(shown):,} Token</p>
<pre class="colored" aria-label="彩色 Token 文字">{colored_text(text, spans, limit)}</pre>
<p class="detail" aria-live="polite">點選 Token 或使用 Tab 與 Enter 查看 ID 及位元組</p>
<div class="tokens">{token_buttons or '<p>空文字 · 0 Token</p>'}</div></section>''')
    return '''<!doctype html>
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
<p>''' + escape(encoding_name) + f''' · {total:,} Token</p></header>''' + "".join(sections) + '''</main><script>
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
</script></body></html>'''
