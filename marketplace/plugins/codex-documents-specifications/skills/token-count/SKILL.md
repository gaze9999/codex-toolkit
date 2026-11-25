---
name: token-count
description: Count and color exact text tokens, compare encodings or estimate Codex context from Global/Project Agent instructions, Skills, tools and dated community profiles. Use for token budgets and reports, not API credentials, account usage or pricing.
metadata:
  version: "0.4.0"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Token Count

Use the native `token-count` CLI from the Toolkit `tools/token-count`, with `o200k_base` by default. Select exact text counting, colored tokens or environment estimation when the request needs a token budget or report.

## Context estimates and colored tokens

- For Global/Project Agent, Skills, tool or environment budgets, read [context budget](references/context-budget.md). Run `token-count context --project <directory>` with the selected sources. Count startup metadata and activated bodies separately, and apply the dated community profile to system/tool overhead.
- For a colored view, add `--html <new-file.html>` to exact text counting. The offline HTML shows token colors, IDs and UTF-8 byte boundaries; the full count is retained and display defaults to the first 2000 tokens per source. Increase `--max-display-tokens` when needed.
- Reports contain requested category counts, totals, output links and sources. Use concise results and source dates; omit generic warnings, defensive prefaces and disclaimers. Keep measured file BPE, rendered metadata counts and community estimates identified by their row labels.

## Inputs and execution

- Identify the exact supplied text or authorized local files and honor an explicit encoding. If the request names only a model, establish its actual supported tokenizer mapping before claiming model-specific accuracy; a named encoding measures that encoding only.
- Run `token-count --input <file> [<file> ...] --json`. For short supplied text use `--text`; omitted input reads UTF-8 stdin. Preserve the original text and whitespace; shell pipes/here-documents may add a trailing newline or change encoding.
- Files must be UTF-8 text with optional BOM. UTF-8 BOM is excluded; CRLF, spaces and trailing newlines are preserved. Special-token-looking strings are counted literally. For PDF/Office, count an identified text extraction and label that scope; count document text only, never binary bytes, and keep the source unchanged.
- To compare encodings, run the same input once per selected `--encoding` and report each encoding separately. Available encodings: `o200k_base`, `o200k_harmony`, `cl100k_base`, `p50k_base`, `p50k_edit`, `r50k_base`, `gpt2`. Multiple files are counted independently; `total_tokens` sums those counts and is not the token count of concatenated text.
- Add `--output <new-file>` when an export is requested. `.json` selects JSON; other extensions default to plain text unless `--json` is supplied. Existing files are preserved and the output parent must exist.

## Runtime and results

Check `token-count --version` first. When the command is missing, report that and install it within the user's authorization with `cargo install --locked --path <Toolkit>/tools/token-count` (Rust 1.89+) or the user's Setup installer; keep exact counts pending until it runs, never substituting estimates.

The CLI embeds the encoding dictionaries. Counting uses no API, API key, download or network, and source text stays local.

Report the input scope, encoding, exact Token count and requested comparison/export. Include character and UTF-8 byte counts or characters/Token when useful. `chars` counts Unicode code points; empty text has zero tokens and a null ratio. An error exits with code 2 and must not be presented as a completed count.

Exact mode reports the supplied text. Context mode reports selected source components plus the community profile. Use the selected mode's result labels and sources.
