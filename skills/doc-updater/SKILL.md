---
name: doc-updater
description: Update, align or synchronize identified existing documentation when explicitly requested and supported by verifiable implementation-change evidence. Use for maintaining current docs, not source extraction, new reports or substantial README redesign.
metadata:
  short-description: Minimize documentation updates from implementation evidence
  version: "0.4.16"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Doc Updater

Minimally align identified existing README/Markdown, API references, changelogs, memos or context briefs with implementation evidence. Use another workflow for new documents, formal artifacts, source extraction or substantial README redesign.

## Activation and scope

Require an explicit documentation update/alignment/synchronization request, a usable diff/commit/PR/release/changed-file list or implementation summary, and a concrete target. Resolve available targets/evidence first; ask only for missing information affecting correctness or authorization.

Update behavior, public APIs, installation/configuration, deployment, compatibility or established architecture affected by the change. An internal refactor alone normally needs no update. A diff establishes changed source, not runtime success; label claims based only on a supplied summary `summary-based`.

Governing specifications and confirmed decisions retain authority. Preserve unresolved conflicts instead of rewriting requirements to match code. For conflicting versions or paired current/history records, read [source authority and history](references/source-and-history.md).

## Apply the supported change

- Read relevant implementation evidence and target sections, then make the smallest supported update. Recheck the destination when concurrent edits are possible, preserve unrelated changes, authoritative wording, legal notices and material limits, and keep secrets/private implementation details out of public guarantees.
- If impact or target selection is unclear, read [documentation impact rules](references/doc-update-rules.md). The optional `scripts/scan_changed_files.py --repo <repo-root>` aids discovery with a compatible Python runtime; equivalent repository inspection needs no new tool installation.
- For Markdown replacement, use available inspection/dry-run/SHA-256 helpers or an equivalent optimistic-concurrency guard. A preview does not authorize additional writes.
- Local documentation is the default. Notion discovery, access, comparison, validation, writes and remote status reporting require the current request to explicitly name Notion or a Notion target. Links, IDs, snapshots, prior arrangements and sync metadata do not grant that access. For an authorized Notion target, read the [reader/writer contract](references/notion-sync-reader-writer-contract.md); explicit named dual-target synchronization needs no duplicate confirmation.
- Complete independently authorized local changes. Preserve in-scope metadata without inferring remote state or advancing unverified sync timestamps.
- For teaching order, examples/images or presentation changes, read [document presentation](references/presentation.md). Preserve an effective structure during ordinary maintenance; broader restructuring or moves need their own scope.

Check changed prose with available textlint/equivalent and manually review meaning and Taiwan terminology. Preserve code, identifiers, quotes and legal/source language. Sensitive content may stay out of tool processing/temp files with manual review; report that scope and any unavailable/failed check.

Report changed targets, supported behavior, no-update decisions, actual checks and remaining acceptance. Distinguish checked source state, historical evidence, human/agent reports and summary-based claims, including relevant earlier uncommitted work. Diff/prose checks do not establish runtime, deployment or model behavior.
