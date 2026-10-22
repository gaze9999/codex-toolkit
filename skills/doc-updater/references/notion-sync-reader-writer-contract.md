# Notion Sync Reader and Writer Contract

Load and use this contract when the current request explicitly mentions Notion or names a Notion target for an implementation-backed documentation update.

## Scope and access

- Use an explicit uploaded Notion JSON snapshot for offline reading, or the available Notion connector / first-party tool for live reading and writing. Do not add a personal access token, secret, or connector credential to this repository, a script argument, a document, or a log.
- Read or write only a page, database item, or memo explicitly named by the user or already confirmed as a target in the current Notion request.
- Links, page IDs, and `sync_mode: bidirectional` identify targets but do not authorize access. Resume paused synchronization only on explicit user request, comparing current content before any write.
- Do not search, crawl, enumerate, or classify a broad Notion workspace to discover a sync target.
- The current request must explicitly name Notion or a Notion target for discovery, access, comparison, validation, writes or remote status reporting. Snapshots, paired targets, prior arrangements and metadata alone do not satisfy this gate. Complete independently authorized local updates without inferring remote state or advancing unverified sync timestamps.
- Never copy local filesystem paths or relative Markdown links into Notion. Link only confirmed remote targets; otherwise keep the label as plain text.

## Reader procedure

1. Read the exact target before planning an update. For an uploaded snapshot, use the Skill-relative `scripts/inspect_notion_sync_target.py` when a compatible Python runtime is available, or an equivalent local JSON inspection, with that one file and, when known, its page ID.
   For local Markdown metadata, `scripts/inspect_markdown_sync_target.py --include-notion-metadata <file>` is available only inside this explicitly authorized Notion workflow.
2. Record page ID or URL, title, relevant content blocks, child-page or database-item boundary, and any source / last-synced metadata.
3. Compare implementation-relevant content with the canonical Markdown: text and identifiers, each table cell and its row/column association, link labels and destinations, inline code/fences and literal operators/escapes, plus child-page/database identities and hierarchy. Formatting equivalence must preserve these semantics; plain text equality is insufficient. Do not strip all HTML/tags or punctuation to make comparisons pass.
4. If the uploaded snapshot is incomplete, a connector truncates content, returns unknown blocks, or cannot read the exact target, stop and report that the Notion side is unverified.
5. If the Markdown and Notion sides have independent changes, report a conflict and do not overwrite either side.

## Writer procedure

1. Resolve the specific target and dual-update authorization from the current request. An explicit request naming both targets is sufficient; ask only when the scope remains ambiguous.
2. Fetch the exact target immediately before the write with the available first-party connector or Notion tool, and use that snapshot as the concurrency baseline.
3. Serialize technical identifiers such as `api.data.value` and `DB_TABLE.FIELD` as inline code when they are literals rather than URLs. Preserve code/fence content, comparison operators, braces, backslashes and table pipes through the selected Markdown/JSON transport. Check the current tool schema and use structured arguments rather than shell-built payloads. Apply the smallest exact replacement; preserve page IDs, unrelated sections, hierarchy, source links and intentional Notion-only formatting.
4. Create, delete, move, or reorganize pages or database items only when the user explicitly asks.
5. For an asynchronous write, retain the operation/task ID and await its successful terminal result before fetching. A timeout, local process exit or stopped wait does not establish cancellation or completion. For an unknown outcome, inspect the original receipt/status and destination before retrying; never replay confirmed writes.
6. Re-fetch the same target and compare the reader dimensions above. Inspect actual link destinations, table values, code and child identities as well as text coverage; dotted identifiers must not acquire HTTP links. Repair only the affected spans against a fresh baseline, then read back again.
7. Report the target, changed section, canonical source, actual post-write checks and remaining layout/connector acceptance. Source guidance or an offline parser check does not establish live round-trip success.

## Neutral acceptance case

Use a user-authorized test target or the next authorized document update. Preserve a baseline with a text identifier, a table, a code fence, one explicit link and an existing child page. Include these literals:

```text
api.data.value
DB_TABLE.FIELD
value < limit && count >= 1
left | right
{"key": "{value}", "path": "example\folder"}
```

Encode dotted literals as inline code, retain the code fence contents and escape a table pipe only for its transport context. After the write succeeds, read back and check exact literal values, cell positions, explicit link destination and unchanged child identity. No additional HTTP target may appear. Record actual results per dimension; incomplete reads leave the affected dimension unverified.

## Failure handling

- Authentication failure, timeouts, rate limits, and ambiguous write results do not prove that no change occurred. Re-read the exact target before any retry.
- Never retry a broad workspace read or overwrite a target to resolve ambiguity.
- If a write cannot be verified, label it unverified and stop rather than claiming synchronization completed.
