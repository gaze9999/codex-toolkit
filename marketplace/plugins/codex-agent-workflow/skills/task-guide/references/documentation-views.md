# Requirement files and document views

Read when organizing reusable requirements, AI navigation, human reports or history retrieval. Select the smallest useful set within authorized documentation scope. Existing filenames, stable IDs, destinations and source authority take precedence over these illustrative labels.

## One authority, several reading views

| View | Retain | Avoid |
|---|---|---|
| Original sources and traceable extracts | Source identity, revision/hash, page/sheet/section, extraction coverage and unresolved differences | Replacing the original specification with a summary |
| AI index / task guide | Task-to-source routes, source authority, applicable constraints, maintained current-state and evidence links | Copied field catalogs, per-run logs, duplicated progress or independent completion claims |
| Requirement/decision reference | Exact behavior, copy, fields, formats, invariants, failure paths and source pointers | Treating an execution plan or existing implementation as a confirmed requirement |
| Current-state record | Durable goal, effective decisions, stable IDs, difference from target, owner, dependencies, acceptance and next action | Repeated historical delivery narratives or replacing the goal with recent activity |
| Human report | Result, impact, meaningful evidence, limitations and required next decision | Tool transcripts, machine inventories and every intermediate action |
| History/evidence | Material change, decision replacement, tested artifact, environment/input, actual outcome and immutable evidence link | Overwriting an old failed run with a later PASS or adding an entry for every message |

A small task can use sections in one maintained document. Split files when audience, source authority, update cadence, ownership, independent reuse or reading cost differ. Do not require one file per page, field, agent or conversation. If a split is authorized, preserve inbound links and historical IDs and update the existing index. Human reports are delivered only when requested or required; routine closeout can remain in chat.

## Turn identified requirements into reusable files

1. Inventory only relevant existing sources and outputs; reuse source-matched extracts. Record missing sections and conflicts before compression.
2. Group by coherent behavior or interface owner, such as a form, approval flow or public API. Keep shared invariants and wording in one maintained source, linking from feature-specific sections.
3. Map each acceptance-relevant requirement to its source location, effective decision, implementation owner/location and expected check. Use the existing ID scheme; do not fabricate a completed implementation mapping before inspection.
4. Preserve exact UI labels, warnings, state/role rules, field types, requiredness, units, precision, null/omitted/empty distinctions and error behavior. Layout/interaction references need the relevant original image or rendered source when textual extraction is insufficient.
5. Verify links, source boundaries and representative source-to-requirement-to-check traces. Conflicting requirements remain unresolved until the governing source or authorized decision resolves them.

Implementation acceptance for UI distinguishes layout, exact copy, field validation, enabled/disabled/read-only/visible states and interaction. These are separate observations, not a universal scoring formula. Add state transitions, loading/empty/error/cancel paths, stale responses, request/response mapping and persistence/permission checks when applicable. Synthetic fixtures cover only their exercised behavior; retain formal API/Host/environment gates.

## Decide what stays detailed

Write direct explanations of purpose, behavior, steps, results and necessary conditions. Remove boilerplate disclaimers, defensive wording, self-justification and unnecessary contrasts. State material constraints through their concrete impact and handling. Apply this style when creating, revising, organizing or translating documents.

For backend, data-processing or algorithm design affected by input growth or repeated calls, retain a compact complexity view of the significant call path: input variables, node/path boundary, time and auxiliary-space bounds, assumptions, source revision, evidence status and next analysis. Keep API/database call counts and measured latency separate from Big O, and structural maintainability separate from algorithmic complexity. Follow the [delivery lifecycle guidance](../../agent-governance/references/delivery-lifecycle.md#adapt-ui-and-research-to-the-project). Frontend documents exclude Big O analysis and annotations; describe interaction performance, rendering/request behavior and maintainability.

Keep decision-changing detail: exact public contracts and specification wording, source conflicts, authorization, irreversible effects, known failure evidence, acceptance gaps and migration constraints. Keep detailed data tables and raw runner output at their maintained source/evidence destination, with narrow references from the index and report.

Summarize repeated rationale, settled background, routine discovery and unchanged successful checks. Use a result-first human report with an evidence link; let the reader open the detail. Do not use a fixed line/token cap to remove a condition needed for correctness. A compact index is useful only if its links resolve and a fresh reader can find the necessary detail.

Optimize for the reader's task and surface: semantic headings, meaningful links, a small complete example, nearby limitations and readable tables. Use the available document-presentation reference for a requested teaching/layout redesign; otherwise retain the effective structure. Do not hide required actions in collapsed or image-only content. Source checks and actual narrow-screen or paginated rendering prove different things.

## Retrieve history by question

Start with the current work ID and the question to resolve. Follow its active source/decision/evidence pointer, then inspect only the relevant historical entry or code diff. Search archived chats by known project/task identity when the source of a decision is still missing; read the relevant user decision and result, not just the title/summary. A matching title is not identity, and an archived chat is not deletion, completion or current authority.

Compare historical evidence against current requirement revision, relevant dirty files, built artifact and runtime. Mark superseded results historical and recheck the affected scope. An inaccessible history item leaves a provenance gap; do not infer what it contained, revive a cancelled item or restart accepted work simply to fill the gap.

Preserve original timestamps/precision and distinguish source revision, decision, observation and verification times. Keep an old issue ID when corrected; link replacement decisions or split/merged work without recycling IDs. A generated current summary may be consolidated in place; append-only history stays append-only with an explicit correction reference. Deletion or relocation of evidence requires checking ownership, references and retention needs first.

## Review the views together

When a diagram, chart or interactive explanation helps answer the current question, use the available `data-visualization` Skill for visual selection, data mapping and rendered-output checks. Keep the document's narrative and authoritative sources with its owner and reference the maintained figure source. Resolve this optional capability from the current environment when needed.

For document planning, resolve purpose/audience, authority, detail level, owner/update trigger, authorized destination and acceptance. Reuse current filenames and directories; separate editable sources, generated outputs, evidence and temporary material only when their lifecycle differs. Check inbound references, scripts, local-only files and ownership before moving, renaming or removing anything. Portable sources use repository identity and relative paths; rendered handoffs must give recipients reachable links.

Classify AI artifacts by purpose and adoption separately: proposal/draft, accepted maintained source, generated deliverable, validation evidence or temporary analysis. Preserve owner, source/artifact revision, accepted/superseded status and approved destination where continuation or review needs them. Record model/tool settings only when relevant to reproducibility. Generation or a filename never establishes acceptance; retain required history and check references before cleanup.

Cross-format work preserves meaning before appearance. Identify the editable authority and target renderer. Retain exact copy, numbers/units, table relationships, formulas, source pointers and necessary annotations. Convert unsupported blocks or diagrams into supported headings/lists/tables/images plus explanations, explicitly recording lost interaction or properties. Keep diagram/data sources where needed; do not emit platform-specific directives into an incompatible target or assume a reverse conversion may overwrite the original.

Inspect representative headings, lists, tables, formulas, links and images after conversion. Render or open layout-sensitive outputs such as PDF, DOCX or slides, and recalculate spreadsheet formulas with a suitable tool when results matter. Separate content checks, visual checks and destination readback. A file that exists or a successful export does not establish semantic equivalence, full format support or correct rendering.

Personal, collaborator and acceptance views derive from one maintained state. Expose current differences/next action to the implementer, ownership/dependencies to collaborators, and source-to-evidence acceptance to reviewers. Keep implemented, pending acceptance, accepted, blocked, deferred and cancelled states distinct using the project's terminology. Preserve waiting/restart conditions; counts or activity do not replace accepted outcomes. Notifications and external writes need the applicable authorization.

Project conventions and exceptions stay at their narrow owner. Record exception scope, governing source, reason, owner and recheck trigger. Code-style guidance remains conditional on the requested change and actual runtime; document maintenance does not authorize renaming symbols, formatting unrelated code, lifecycle/state refactoring or framework migrations.

- From the index, locate one requirement, one current unresolved item and its detailed evidence without scanning all documents.
- From the human report, determine what changed, the tested artifact, actual acceptance and next action.
- From history, identify which prior decision/result was superseded and which current item owns follow-up.
- Check that status, goals and requirements each have one maintained owner; links and summaries do not silently become competing specifications.
- Classify these as source/readback or manual retrieval checks. A new-conversation, cross-device or model-behavior claim requires an actual run on that surface.
