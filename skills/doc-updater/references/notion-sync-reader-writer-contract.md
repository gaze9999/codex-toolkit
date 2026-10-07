# Notion Sync Reader and Writer Contract

Load and use this contract when the current request explicitly mentions Notion or names a Notion target for an implementation-backed documentation update.

## Scope and access

- Use an explicit uploaded Notion JSON snapshot for offline reading, or the available Notion connector / first-party tool for live reading and writing. Do not add a personal access token, secret, or connector credential to this repository, a script argument, a document, or a log.
- Read or write only a page, database item, or memo explicitly named by the user or already confirmed as a target in the current Notion request.
- Links, page IDs, and `sync_mode: bidirectional` identify targets but do not authorize access. Resume paused synchronization only on explicit user request, comparing current content before any write.
- Do not search, crawl, enumerate, or classify a broad Notion workspace to discover a sync target.

## Reader procedure

1. Read the exact target before planning an update. For an uploaded snapshot, use the Skill-relative `scripts/inspect_notion_sync_target.py` when a compatible Python runtime is available, or an equivalent local JSON inspection, with that one file and, when known, its page ID.
   For local Markdown metadata, `scripts/inspect_markdown_sync_target.py --include-notion-metadata <file>` is available only inside this explicitly authorized Notion workflow.
2. Record page ID or URL, title, relevant content blocks, child-page or database-item boundary, and any source / last-synced metadata.
3. Compare only the implementation-relevant sections with the canonical Markdown target. Treat Notion formatting as presentation; compare meaning, links, identifiers, tables, and constraints.
4. If the uploaded snapshot is incomplete, a connector truncates content, returns unknown blocks, or cannot read the exact target, stop and report that the Notion side is unverified.
5. If the Markdown and Notion sides have independent changes, report a conflict and do not overwrite either side.

## Writer procedure

1. Resolve the specific target and dual-update authorization from the current request. An explicit request naming both targets is sufficient; ask only when the scope remains ambiguous.
2. Fetch the exact target immediately before the write with the available first-party connector or Notion tool, and use that snapshot as the concurrency baseline.
3. Apply the smallest exact replacement that aligns the implementation-backed change. Preserve page IDs, unrelated sections, page hierarchy, source links, and intentional Notion-only formatting.
4. Create, delete, move, or reorganize pages or database items only when the user explicitly asks.
5. Re-fetch the same target after writing. Verify the expected markers, content coverage, and no truncation or unexpected block conversion.
6. Report the target, changed section, canonical source, post-write verification, and any unverified layout or connector limitation.

## Failure handling

- Authentication failure, timeouts, rate limits, and ambiguous write results do not prove that no change occurred. Re-read the exact target before any retry.
- Never retry a broad workspace read or overwrite a target to resolve ambiguity.
- If a write cannot be verified, label it unverified and stop rather than claiming synchronization completed.
