---
name: token-count
description: Count and color exact text tokens, compare encodings or estimate Codex context from Global/Project Agent instructions, Skills, tools and dated community profiles. Use for token budgets and reports, not API credentials, account usage or pricing.
metadata:
  version: "0.2.0"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Token Count

Use the bundled [counting helper](scripts/count_tokens.py) and the maintained Python Tools core, with `o200k_base` by default. Select exact text counting, colored tokens or environment estimation when the request needs a token budget or report.

## Context estimates and colored tokens

- For Global/Project Agent, Skills, tool or environment budgets, read [context budget](references/context-budget.md). Run `python <skill-directory>/scripts/count_tokens.py context --project <directory>` with the selected sources. Count startup metadata and activated bodies separately, and apply the dated community profile to system/tool overhead.
- For a colored view, add `--html <new-file.html>` to exact text counting. The offline HTML shows token colors, IDs and UTF-8 byte boundaries; the full count is retained and display defaults to the first 2000 tokens per source. Increase `--max-display-tokens` when needed.
- Reports contain requested category counts, totals, output links and sources. Use concise results and source dates; omit generic warnings, defensive prefaces and disclaimers. Keep measured file BPE, rendered metadata counts and community estimates identified by their row labels.

## Inputs and execution

- Identify the exact supplied text or authorized local files and honor an explicit encoding. If the request names only a model, establish its actual supported tokenizer mapping before claiming model-specific accuracy; a named encoding measures that encoding only.
- Use an existing Python 3.10+ runtime with `tiktoken` and `regex` for colored output; context discovery requires Python 3.11+. The Plugin bundles the core and its focused requirements, not a Python runtime or installed dependencies. Missing prerequisites require a setup step within the user's authorization; do not silently install them or replace exact counts with estimates.
- Resolve this Skill's actual directory and run `python <skill-directory>/scripts/count_tokens.py --input <file> [<file> ...] --json`. For short supplied text use `--text`; omitted input reads UTF-8 stdin. Preserve the original text and whitespace; shell pipes/here-documents may add a trailing newline or change encoding.
- Files must be UTF-8 text with optional BOM. UTF-8 BOM is excluded; CRLF, spaces and trailing newlines are preserved. Special-token-looking strings are counted literally. For PDF/Office, count an identified text extraction and label that scope; do not treat binary bytes as document text or silently alter the source.
- To compare encodings, run the same input once per selected `--encoding` and report each encoding separately. Multiple files are counted independently; `total_tokens` sums those counts and is not the token count of concatenated text.
- Add `--output <new-file>` when an export is requested. `.json` selects JSON; other extensions default to plain text unless `--json` is supplied. Existing files are preserved and the output parent must exist.

## Runtime and results

The helper resolves its Plugin-relative runtime first, or the canonical runtime in the same Toolkit checkout. It does not search neighboring repositories or installed client caches. A copied Skill without its Plugin runtime must report that missing resource. Requirements are at `resources/token-count/requirements.txt` under the Plugin root; canonical source owns them in Python Tools.

Counting uses no OpenAI API or API key and sends no source text over the network. First use of an encoding may download its public dictionary; cached dictionaries permit offline counting. The helper respects `TIKTOKEN_CACHE_DIR`/`DATA_GYM_CACHE_DIR` and otherwise uses the system temporary cache, keeping runtime writes outside the Plugin payload.

Report the input scope, encoding, exact Token count and requested comparison/export. Include character and UTF-8 byte counts or characters/Token when useful. `chars` counts Unicode code points; empty text has zero tokens and a null ratio. An error exits with code 2 and must not be presented as a completed count.

Exact mode reports the supplied text. Context mode reports selected source components plus the community profile. Use the selected mode's result labels and sources.
