# Requirement files and document views

Read when organizing reusable requirements, AI navigation, human reports or history retrieval. Select the smallest useful set within authorized documentation scope. Existing filenames, stable IDs, destinations and source authority take precedence over these illustrative labels.

## One authority, several reading views

Write AI-facing guides, briefs, indexes and handoffs in concise English. Human-facing authored Chinese uses concise Taiwan Traditional Chinese and Taiwan wording, never Simplified characters. Use halfwidth punctuation, one space after commas/colons/question/exclamation marks when text follows, allow 、 for enumeration, and omit Chinese sentence periods and semicolons. Preserve requested languages, source quotations, contractual copy, code, URLs and versions. These defaults apply even when Global is unavailable.

Read relevant sections/symbols first and retain checked source/version pointers. Expand only when confidence is insufficient or the specification is unclear/conflicting; do not require whole-file/document reads by default.

| View | Retain | Avoid |
|---|---|---|
| Original sources and traceable extracts | Source identity, revision/hash, page/sheet/section, extraction coverage and unresolved differences | Replacing the original specification with a summary |
| AI index / task guide | Task-to-source routes, source authority, applicable constraints, maintained current-state and evidence links | Copied field catalogs, per-run logs, duplicated progress or independent completion claims |
| Requirement/decision/reference | Exact behavior, copy, API/fields/integration mappings, stable reference IDs and governing source pointers | Appending acceptance logs instead of maintaining reference content |
| Current-state record | Active feature progress with IDs and unresolved issue/maintenance work, owner, dependencies, gaps and next action | Keeping resolved issue rows/completion narratives or growing catalogs in current state |
| Method guidance | Procedures, calculations, persistent issued-ID high-water source/usage, shared platform checks and version criteria | Duplicate completion state or copying common platform work into feature backlogs |
| Human report | Result, impact, meaningful evidence, limitations and required next decision | Tool transcripts, machine inventories and every intermediate action |
| History/evidence | Resolved issue ID, original problem, concrete solution/replacement, relevant version/source, actual results and necessary gaps | Completion logs, overwriting an old failure with PASS or an entry for every message |

A small task may use distinct sections in an existing document; growing references, methods and history use their existing destinations rather than a fixed three-part current-state file. Split by record type, audience, authority, update cadence, ownership or reading cost when needed, without another parallel tracker or one file per field/agent/conversation. Preserve inbound links and stable IDs and update the existing index. Human reports are delivered only when requested or required; routine closeout can remain in chat.

Choose existing destinations by record type. Current state keeps active feature progress and unresolved issue/maintenance work; references keep API/fields/integration mappings, methods keep calculations and persistent issued-ID source/usage, and concise history keeps resolved problems and actual checks. Update only for material decisions, scope, stage, blockers, acceptance or handoffs. For cleanup or an explicitly requested new starting round, follow [current/history maintenance](https://github.com/gaze9999/codex-toolkit/blob/main/skills/doc-updater/references/source-and-history.md), including complete ZIP preservation and extracted byte comparison before replacement. Use ordinary Markdown headings and reconnect existing navigation.

## Turn identified requirements into reusable files

For field validation, retain field/type, governing jurisdiction, required/empty/null rules, normalization, bounds/pattern/checksum, cross-field conditions, validation timing, exact message/key, named helper/algorithm and usage, accepted/rejected examples, source/version and unresolved decisions. Never infer an unspecified rule from an option name or current UI.

For each shared capability, record every supported feature with selector/export, import/provider requirements, typed inputs/outputs/methods, minimum usage, validation/error behavior, ownership and source baseline. A service has no selector; provide its callable API. A complete checked entry is the consumption baseline, not an instruction to rediscover source each round. Functional-test failures justify affected-source investigation; maintainers repair missing/stale entries rather than consumers guessing.

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

Preserve original timestamps/precision and distinguish source revision, decision, observation and verification times. Choose current-row retention/removal from explicit task/project decisions, with the user's current decision first. This decision removes entire resolved issue/maintenance rows after concise history retains their ID, problem, solution, version/source and checks/gaps; progress records and API/endpoint reference indexes retain IDs. Keep unfinished work and verification gaps in their appropriate views. Use the persistent issuance source in [the ID method](task-guide.md#issued-id-high-water-source), never the remaining current maximum, and preserve split/replacement relationships. Append-only history uses correction references until an archive-verified restart is requested. Check ownership, references and retention needs before relocating evidence.

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
