---
name: doc-updater
description: Update, align or synchronize identified existing documentation when explicitly requested and supported by verifiable implementation-change evidence. Use for maintaining current docs, not source extraction, new reports or substantial README redesign.
metadata:
  short-description: Minimize documentation updates from implementation evidence
  version: "0.4.14"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Doc Updater

Use completed implementation changes to minimally align README files, Markdown, changelogs, API references, Notion memos, or Codex context briefs with verifiable behavior. This is not a workflow for authoring new documentation from scratch.

## Activation

Use only when all conditions hold:

- The user explicitly requests an update, alignment, or synchronization of existing documentation.
- A diff, commit, PR, release, migration, changed-file list, or usable code-change summary is available.
- At least one concrete documentation target is identified.

When evidence or a target is missing, request only the information needed for correctness or authorization. Use another workflow for ordinary authoring, summaries, translation, Notion organization, coding prompts, pre-implementation briefs, or formal document artifacts.

## Workflow

- Treat diffs and changed files as direct evidence of implementation changes, not proof of runtime success, deployment or acceptance. Tie verification claims to the checked source state and actual results. When only a user summary exists, mark resulting claims `summary-based`.
- Preserve the target document's authority: a governing specification or confirmed decision is not rewritten to match conflicting code. Record that conflict; update independent implementation/status sections within scope without turning observed behavior into an approved requirement.
- Update only documents affected by public APIs, user-visible behavior, installation or configuration, deployment, migrations, compatibility, or established architecture descriptions. Internal refactors without behavior change normally do not require updates.
- Check changed prose with available textlint or an equivalent language checker, then review meaning and Taiwan terminology manually. Preserve source quotes, legal text, code, identifiers and English/Japanese conventions. Report unavailable, failed or unchecked coverage. Sensitive content may skip tool processing and temporary files; review it manually and report the exception. Keep checks within changed sections.
- Read only the necessary diff and target sections, then make the smallest supported change. Recheck the target before replacement when concurrent changes are possible; retain unrelated edits and unresolved items. Do not promote internal details to public guarantees or add secrets or unnecessary personal data.
- When a current-state document has a paired history or archive, keep the current document limited to current behavior, active work, unresolved decisions, and the latest verification boundary. Move superseded status, completed batches, dated execution details, old sync records, and obsolete navigation to history after confirming unique evidence is retained.
- When identifiers are reformatted, apply the requested scheme to current records and record the old-to-new mapping in history. Rewrite historical identifiers and anchors only on explicit user request.
- Keep each new history entry to one or two concise paragraphs whenever that preserves the outcome, material evidence, and remaining verification limits. Use a longer entry only when required to retain unique information or when the user explicitly requests detail; do not turn command sequences or check-by-check narration into history.
- When documentation impact or target selection is unclear, read [Doc Update Rules](references/doc-update-rules.md) for the evidence and impact tables. When a compatible Python runtime is available, `scripts/scan_changed_files.py --repo <repo-root>` supports impact discovery, otherwise use equivalent repository inspection without installing optional tooling.

## Local-first updates

- Update local documentation by default. Notion discovery, access, comparison, validation, writes, and status reporting require the current request to explicitly name Notion or a Notion target; links, page IDs, snapshots, paired targets, prior sync arrangements, and `sync_mode` metadata do not satisfy this gate. Include synchronization or maintenance status only when it affects the requested content or execution.
- When synchronizing to Notion, do not copy local filesystem paths or relative Markdown links into the page. Link or mention only a confirmed Notion target; otherwise keep the label as plain text and omit the local path.
- Complete authorized local updates independently. Preserve existing metadata only when it lies inside an edited local target, but do not use it to infer remote state or advance sync timestamps.
- An explicit request to synchronize identified local and Notion targets is authorization for those targets; do not ask for duplicate confirmation. Resolve the exact targets and compare current content before writing, asking only if ambiguity would change scope or overwrite risk. Follow [Notion Sync Reader and Writer Contract](references/notion-sync-reader-writer-contract.md); do not blindly overwrite changes accumulated while sync was paused.
- For Markdown replacement, use the bundled inspection, dry-run, and SHA-256 helpers when compatible tooling is available, or an equivalent optimistic-concurrency check in the active environment.

For teaching order, purpose-specific outline references, examples/images and explanation-first wording, read [document presentation](references/presentation.md) only when that aspect is in scope. Preserve an effective existing structure during maintenance, patch the affected content/references and avoid broad rewrites or document moves without authorized need. Keep authoritative wording, legal notices, side effects, data boundaries and material verification limits.

## Delivery

Report the documentation result, changed files and no-update decisions. Include actual check results, coverage and unverified scope; distinguish direct checks, historical evidence, agent reports and summary-based claims. Identify relevant earlier uncommitted changes and required next actions. Diff or prose checks do not prove runtime success, deployment or model behavior.
