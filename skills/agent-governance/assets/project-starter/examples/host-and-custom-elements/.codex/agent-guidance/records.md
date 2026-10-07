# Project progress and history

Read only when maintaining project progress, history or related documents. Apply this example after the project confirms its recording policy and destinations.

## Destinations and triggers

Resolve the current progress document, history document and feature guide from the project or task. Progress keeps current conclusions and next work; History keeps bounded dated evidence. Do not invent mandatory filenames or create duplicate handoff/report documents.

| Trigger | Required update |
|---|---|
| Substantive application change or new verification that changes progress | Update affected Progress rows and append one bounded History entry |
| Phase, decision, current blocker or next work changes | Update affected Progress rows; record the previous/new decision and reason in History when traceability requires it |
| Explicit source extraction or index maintenance | Change only authorized source/index targets, preserving provenance and unresolved decisions |
| Governance, tooling, comments, formatting or documentation-only work | Update authorized documents only; do not advance application status or automatically append application History |

Use concise Taiwan Traditional Chinese for adopted user-facing records. Use timestamps in yyyy-mm-dd hh:mm and identify the timezone when the project has not established it. A conversational round ending alone does not require a record.

## Stable IDs and commit evidence

- Keep existing IDs. Strike through resolved IDs, retain the resolution/evidence and do not renumber or reuse vacated IDs. Allocate new IDs from the project's confirmed sequence.
- With a verified source commit, record Git: <repository>@<unique short SHA> and a concrete change summary. The SHA identifies committed content, not later working-tree edits.
- If an entry also covers uncommitted changes, identify the committed base plus uncommitted changes and distinguish each scope. Without a relevant verified commit, record actual changes and checks directly; do not invent a SHA or add unverified SHAs to older entries.
- Keep current status concise and detailed checks in History. Separate passed, failed, blocked, not run, historical and unverified evidence; historical checks do not certify current source.

## Closeout

Read back changed sections, links, encoding and completeness. Main owns final integration; a document worker may own an authorized independent batch. Original sources and progress spreadsheets remain read-only without write authorization. External synchronization requires explicit authorization and readback of exact targets, preserving independent changes.
