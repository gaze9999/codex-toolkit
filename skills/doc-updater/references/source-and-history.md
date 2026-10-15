# Source authority and current/history records

Read when documentation conflicts with implementation or when maintaining paired current-state/history files.

## Resolve conflicting evidence

Compare relevant Git history/diffs, document revisions and extract source hashes. Record version, branch/commit, dirty state and verified revision/change time, separating unknown dates. Keep source, modification, download, extraction and verification times distinct. Preserve timezone and source precision; use `yyyy-mm-dd hh:mm` only when supported, retaining date-only evidence as dates.

Governing specifications and confirmed decisions retain authority. Newer timestamps and observed code behavior do not approve a requirement change. Preserve unresolved conflicts and update independent implementation/status sections within scope.

## Maintain existing history

Plan storage by record type in existing locations. Current state keeps active feature progress and unresolved issue/maintenance work. Maintain API/field/integration mappings in existing references, procedures/calculations/issued-ID high-water marks in method guidance, and resolved problems with actual checks in concise history. Growing records do not belong in a fixed three-part current-state document. Shared platform checks and version assessments stay in AGENTS/methods. Preserve unique evidence without another tracker or routine report.

Choose current-row retention/removal from explicit task/project decisions; the user's current decision takes precedence. This decision removes entire resolved issue/maintenance rows from current state, while progress records and API/endpoint reference indexes retain IDs. Preserve another project's explicit policy rather than imposing one display everywhere. Unfinished work and verification gaps stay in the appropriate current view.

Before removing a resolved row, retain its stable ID, original problem, concrete solution/replacement decision, relevant version/source and necessary check results/gaps in concise history. Select useful fields without a completion log. IDs are never reassigned, renumbered or recycled to fill gaps. New serials use each prefix's persistent highest-issued value or equivalent issued-ID record in existing method guidance/approved storage, with source and usage recorded; deleting a current row never lowers that value. Follow the [issued-ID high-water procedure](https://github.com/gaze9999/codex-toolkit/blob/main/skills/task-guide/references/task-guide.md#issued-id-high-water-source).

Update only for a material decision, scope, stage, blocker, acceptance or handoff change under the established trigger. A history entry retains only this round's useful information. Select timestamp/timezone, Git/version, governing sources, changes, decisions, actual checks and evidence limits as needed; this is an open set, not a mandatory field list. Unrun checks never receive PASS. Preserve existing formats and evidence needed for acceptance without recording every message or the full conversation.

Human history omits hash inventories, archive-verification narration, authorization logs, boilerplate disclaimers, old indexes/anchors/sections and prefaces explaining that an old edition is not continued. Keep technical identity or verification detail in the linked evidence or archive metadata when needed for reproducibility.

## Restart from a requested round

1. Resolve the requested starting round and complete old edition in its existing location. Check owners, references, attachments and retention needs; preserve all material belonging to that edition and concurrent changes.
2. Create a complete ZIP archive before replacing the old edition. Extract it into an isolated location, compare relative entry sets and every extracted file byte-for-byte with the original, then recheck the originals before replacement. A CRC result or hash list alone does not substitute for this comparison. A mismatch leaves the old edition in place until resolved.
3. Keep the archive and verification evidence at the project's existing archive/evidence destination or in archive metadata. Create concise new history starting with the requested round, retaining applicable stable IDs, unfinished work and verification gaps.
4. Use ordinary Markdown headings, without embedding `<a id="...">` in a heading. Update necessary navigation links to the new headings; old indexes, anchors and sections stay in the archive and cannot stand in for new content. Keep archive checks and old-edition prefaces out of the new history body.
