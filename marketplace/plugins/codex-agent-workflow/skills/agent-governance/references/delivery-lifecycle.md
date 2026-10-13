# Durable development lifecycle

Read when designing or revising a development workflow from requirements to acceptance across projects, conversations or computers. Apply only the relevant stages; this is neither a mandatory agent roster nor a new tracker. Reuse existing project records and enforcement tools.

## Establish the work identity

Resolve the project/repository identity, stable work ID, intended outcome, effective decisions, authorization, acceptance, current owner and approved record. A chat, branch, host or directory locates execution; none replaces the work identity. Keep desired behavior separate from observed implementation and completion claims.

Select evidence by the current gap: current record and original requirement first, relevant artifacts second, history or archived conversation only for unresolved provenance. Preserve source locations and scope when converting material. Missing specifications block dependent behavior, not independent authorized work.

## Connect stages by observable results

| Stage | Required input and action | Output and exit condition |
|---|---|---|
| Recover | Current request, record, effective decisions, actual checkout/diff and owner | Same goal/ID recovered; conflicts, dirty work and missing authority identified |
| Interpret | Original/extracted requirements, UI references, interface specifications, confirmed changes | Requirements mapped to source locations and acceptance; unknowns remain explicit |
| Organize | Existing document layout and actual reuse/ownership needs | Small navigation entry and only needed requirement sections/files; no duplicate status owner |
| Design | Scenarios, shared interfaces, state/data owners, failure paths | Bounded implementation units and dependencies; preserve public contracts or obtain the required decision |
| Implement | Confirmed unit, owned files, real stack, accepted UI/copy and tests | Complete behavior and local checks, including in-scope fixes; source revision/dirty bytes identifiable |
| Verify | Original acceptance, actual diff/artifact, relevant runtime and representative inputs | Per-requirement evidence, failures and unverified boundaries; passing counts alone do not close work |
| Accept | Integrated artifact and independent required gates | Main reconciles every effective requirement; returned work becomes accepted only within proven scope |
| Deliver | Authorized destinations and repository-specific policy | Report and selected source/record updates; Git, installation, loading and deployment states separate |
| Iterate | User correction, observed failure or applicable new research | Supersede affected decisions, identify dependent work/checks and repeat only the affected stages |

Use available context-brief, task-guide, implementation and verification capabilities when their actual triggers match. Do not activate every Skill or install an absent capability to satisfy this table. For document organization and detail limits, use the available task-guide's documentation-views reference. If unavailable, retain a navigation-only index, one current-state owner, a result-first human report when requested and source-linked history in existing destinations.

Requirements, implementation and evidence share stable references: requirement/source -> confirmed decision -> owned implementation -> check -> current acceptance. One check may cover several requirements only when the observed behavior supports each claim. A generated check must be reviewed against the requirement, including a representative failure, rather than simply repeating the implementation.

Make work observable through a compact stage record in the existing destination: current stage, selected inputs/source revision, owned output, decision and brief rationale, check/result, unresolved dependency and next action. Update at a material transition, not every tool call. A human must be able to trace an accepted result back to its source and tested artifact. Transparency means observable inputs, decisions, actions and evidence; do not promise access to hidden reasoning or preserve raw conversations by default.

## Place rules and capabilities at their owner

Global carries durable cross-project preferences and boundaries. Root/nested AGENTS.md carries project architecture, accepted exceptions and record entrypoints. Role files describe only ownership/permission differences; Skills describe reusable triggered work; references hold conditional detail. Plugins package related capabilities for distribution, while MCP supplies needed structured access around maintained tools. A configured role, installed Plugin or listed MCP is not an active worker, loaded workflow, authenticated connection or successful call.

Before splitting or merging Skills/Plugins, compare triggers, consumers, permissions, dependencies and acceptance. Keep distinct audiences/data boundaries separate, consolidate duplicated rules at their owner, and keep existing identifiers/callers unless a migration is authorized. Do not create a new orchestrator service when Main plus existing records and supported task mechanisms meets the need.

## Adapt UI and research to the project

For backend, data-processing or algorithm paths with material search, iteration, sorting, aggregation, batch or recursion, document complexity beside the maintained design/call-chain evidence. Define input sizes, operation boundaries and source revision; distinguish time, auxiliary space and output size. Mark bounds as worst-case, expected or amortized only when justified, with assumptions and derived/measured/unknown evidence. Sequential work adds; nested repetitions require their actual bounds; concurrent execution changes critical-path latency without removing total work. Recursion and cycles need explicit termination and recurrence reasoning. Unknown library or database costs remain unknown.

Separate CPU work from database/API call counts, payload size, concurrency and measured latency. Record each significant node and the end-to-end path without double-counting inclusive costs. For example, scanning m candidates for each of n rows is worst-case O(nm); building a hash index may yield expected O(n+m) time with O(m) auxiliary space under expected constant-time lookup. Validate equivalent duplicate/order/null semantics and measure the actual runtime. Batching n calls into ceil(n/b) calls can matter even though both are O(n) for fixed batch size b. Record the next representative measurement or analysis question.

Maintainability is a separate design dimension: ownership, coupling, call depth/fan-out, shared mutable state, cycles, error/retry/cancellation and side effects. Use complexity annotations to prioritize investigation. Frontend design, implementation and call-chain documentation exclude Big O analysis and annotations; document interaction performance, rendering/request behavior and maintainability instead. Keep public interfaces, transaction semantics and memory tradeoffs visible when considering alternatives.

UI decisions follow the governing product specification, adopted design system, relevant platform semantics and confirmed exceptions. General UX principles guide unresolved choices; preserve exact specified copy and existing public component APIs. Record a project exception with its scope, reason, controlling source and recheck trigger, instead of copying it into Global. Visual acceptance uses the served artifact, representative data and affected layout/copy/validation/state/interaction evidence. A diagram or prototype does not prove browser behavior or persistence.

For data/backend/frontend design, identify data lineage/types/units/lifecycle, authoritative state, producer/consumer contracts and failure/recovery ownership before implementation. Map each changed boundary to its own checks and integrated acceptance, including storage migration, authorization or idempotency only when affected. Game UI follows the actual core rules and representative play, with clear choices, resource/time feedback and supported controls. A frontend-only assignment does not authorize backend work; complete independent UI/fixture work while retaining unresolved formal integration.

For new knowledge, start from the decision/evidence gap, read compatible collected evidence, then trace necessary official sources, original papers or dated practitioner/community reports. Distinguish product guarantees, experiment results, personal practice and inference; preserve contrary findings and source access limits. Adopt only a change whose application and acceptance are explicit. Research feeds a candidate decision, not automatic installation, scheduling or code publication. Retain the original source/version and question scope so later projects can judge reuse.

## Split work by ownership, not stage names

Main retains requirement interpretation, architecture, cross-owner decisions, integration and final acceptance. One implementation owner normally completes discovery, edit, focused verification and in-scope corrections for a coupled unit. Do not automatically create a reader, planner, coder, tester and reporter for every feature.

Delegate only when the current instructions/user authorize it and the unit has bounded inputs, owned outputs, dependencies, acceptance and a stop condition. Independent source questions can use a read-only explorer; a specific integration/security risk can justify independent review. Shared configuration, installation, mutable fixtures and coupled interfaces have one writer or sequential ownership. Documentation can be independent once facts and evidence are settled; its writer cannot accept unverified program behavior.

Merge overlapping work into the established owner/record while retaining old IDs and relationships. Separate work when source/data permissions, runtime ownership, independent maintenance or actual acceptance differ. A workspace manager coordinates independent repositories; it does not merge their Git histories, acquire publication authority or run persistently merely because a role file exists.

Distinguish instruction scope (Global/project/nested guidance) from execution hierarchy (Main/local coordinator/workers). A deeper directory does not require another agent. Start with Main and only authorized independent workers. Add a local coordinator only for a bounded independently deliverable unit with real integration decisions that reduce overall coordination cost; keep requirements, architecture and cross-owner decisions with Main. Every parent-child assignment carries the work ID, effective decision revision, read/write scope, artifact, acceptance, dependencies, stop condition and available resource bounds. Do not infer recursive-delegation permission or a fixed depth/agent count from this design.

Before redesigning an existing hierarchy, inspect relevant coordinator/work conversations, role settings and actual invocation/return evidence. Preserve useful established ownership. Cross-conversation responsibility is distinct from native parent-child identity: a long-lived coordinator may route authorized independent conversations, whose owners may use permitted subagents. Titles/configuration alone prove neither invocation nor current liveness; recent runs without delegation do not prove it was never used. Do not flatten an established structure or propose it as wholly new without this evidence.

Propagate relevant corrections before conflicting child work continues, retain unaffected results, and require artifact/diff plus evidence references on return. Classify blockers and escalate them to the decision owner rather than multiplying retries through layers. Cancellation and owned-resource cleanup follow the same ownership boundaries. Main can inspect source evidence when summaries are insufficient; a child's completion claim is not integrated acceptance. Merge a layer that only relays summaries or duplicates responsibility, judging actual handoff loss, rework and accepted outcomes rather than role names.

## Persistence and freshness are different

| Information | Retention and reuse | Recheck trigger |
|---|---|---|
| Goal, accepted requirement, decision, ownership and deferral | Durable approved record, until explicitly superseded or accepted | New request, source contradiction or changed scope |
| Source specification, derived extract, public interface | Source identity/location, revision/hash and coverage | Governing revision, changed contract, missing visual evidence or extraction mismatch |
| Test/browser/API evidence | Exact source/diff or artifact bytes, inputs, relevant environment, result and evidence reference | Changed relevant inputs/consumer/runtime or unresolved risk; unchanged HEAD is insufficient for dirty work |
| Research conclusion | Topic/question/project/version coverage and original sources | Decision-relevant change, gap, contradiction or explicit recheck; a revisit date is advisory |
| Host/session, tools, credentials availability, selected computer, running owner | Current execution context; secrets stay in approved storage | Reconnection, new client/device or before dependent use |
| Git refs, build/deployment or installed Plugin state | Observed state tied to repository and target | Before claims or actions that depend on present delivery/loading |

Reading a record does not refresh its check time. A new Page timestamp, completed run, accessible screenshot, role configuration or saved memory does not prove the goal, runtime or installation passed. Separate source revision, extraction, observation and verification times; preserve unknown precision.

Keep decision-relevant lineage at the existing owner: source identity/revision -> scoped claim and limitations -> adoption decision -> affected guidance/implementation -> acceptance evidence. Distinguish original publication, revision and successful inspection. Deduplicate reposts and versions under the original source identity. A hash identifies bytes, not semantic significance. A revision weakening a claim triggers review of dependent decisions; a newer method starts as a candidate, not an automatic replacement. Preserve prior evidence and unaffected accepted work, and mark missing coverage without refreshing its successful-check date.

When recurring collection is authorized, inspect existing schedules and preserve their IDs, owners, pause/supersession decisions and notification intent. Bound each run by topic, approved sources/data, execution host, prior verified coverage and current evidence gaps. Compare revisions and necessary related research, identify affected adoptions, and update the same record only for material changes. Collection, interpretation, authorized implementation and acceptance are responsibilities, not a mandatory agent chain. Use one writer or guarded sequential edits; inspect uncertain side effects before retrying. Catch up selectively after interruption, retain access failures without claiming freshness, and notify only actionable changes unless periodic reporting was requested. Research collection does not grant installation, publication or additional data-transfer authority.

## Recover on another execution surface

First distinguish orchestration location, execution host, source/record storage and delivery destination. The selected surface must have the permitted data, tools and repository, not just a familiar model name.

| Surface | Recovery requirement | Evidence boundary |
|---|---|---|
| Same checkout, new conversation | Approved record plus actual current files and applicable instructions | Earlier chat completion is historical evidence, not new authorization |
| Another computer or remote host | Repository identity and relative root, source revision, dirty/ignored artifact inventory, destination settings/permissions | Source transfer, dependency availability, client loading and a representative operation are separate |
| Git worktree | Verified starting revision and required local-only material; independent mutable resources | Worktrees do not isolate shared services, accounts or databases |
| Cloud task | Existing configured environment, approved sources/data and persisted output destination | Local files, sessions and installed tools are not assumed present |
| Dot or scheduled work | Existing responsibility/schedule, original host/task identity, destination and notification/stop conditions | Saved notes and execution completion do not replace requirement acceptance |

For remote handoff use the currently supported native operation only when authorized. Verify destination project identity and the same repository-relative subdirectory, then check transferred Git state and required untracked/ignored material. Do not assume selecting another computer moves an existing task or that native remote handoff supports a cloud destination.

For offline or interrupted work, preserve the pending unit, last verified artifact, owner and next action in the established record. Check whether the prior writer is still active before replacement. Reconcile by revision/hash and per-item meaning, not last-write-wins. After an uncertain external side effect, inspect its receipt/state before retrying; never duplicate a commit, upload, schedule or message just because the response was lost.

Make a material handoff observable with a compact recovery receipt: work ID, effective objective/decisions, source/artifact revisions, what was actually read or transferred, missing/stale material, ownership and the next check. It is a projection of existing records, not a second tracker. A sender's prepared packet does not prove recipient access or loading; acknowledge only observed receipt/readback. Do not promise that all context, hidden reasoning, credentials or raw conversation history follows a new chat, model or host.

When recovering from context compaction, distinguish authoritative records, the currently available context, product-managed compacted state and the human-readable recovery receipt. Identify preserved decisions, deliberately omitted detail with retrieval pointers, actually re-read sources and unknown or stale material. Do not claim an exact internal-context inventory or expose hidden reasoning. Update material state at its existing owner, reuse unchanged verified evidence and recheck only affected gaps; do not restart completed work or reread the entire repository solely because compaction occurred.

Treat long objectives, long conversations and large input contexts separately. Durable work uses stable IDs and verifiable units; conversations retain effective corrections and retrieval pointers; large inputs use scoped retrieval while Main retains governing requirements and cross-owner conflicts. Preserve exact constraints/copy or their authoritative source rather than relying solely on a generic summary. Read-time reconstruction can complement write-time summaries but cannot override current authority or justify collecting all private history. At a material checkpoint preserve the last verified artifact, unverified changes, current writer, unfinished operations and next check. Before replaying an interrupted action inspect its actual state/receipt. Stop unchanged-input failure loops, retain evidence and continue independent work. Do not rotate chats at fixed token/time/turn thresholds; evaluate observed context loss, coupling, permissions and acceptance cost, and obtain any required task-creation authorization.

Native product references checked 2026-10-13: [remote handoff](https://learn.chatgpt.com/docs/remote-connections#hand-off-a-chat-between-hosts) requires matching saved projects and does not support Codex cloud handoff; [dots tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory) distinguishes notes, task conversations, recurring schedules and the task's original execution environment. Recheck these boundaries when the target client or workflow changes. These references describe product capability, not verified account/device access.

## Close the improvement loop

### Use product controls without replacing project authority

Use a native plan mode for unresolved design when available and appropriate; a plan is not implementation acceptance. A native Goal can sustain an objective in its own conversation, but does not replace the approved project record or a saved recurring schedule. Keep completion evidence and current authorization explicit. Pausing, budget exhaustion and a finished turn are distinct from acceptance. Check the active client's actual controls and lifecycle before applying commands from another surface.

For another model or AI client, keep the portable work packet small: repository/work identity, effective requirements/decisions, authorized source locations, owned artifacts, acceptance and next action. Resolve instruction discovery, tool schemas, permissions, memory, model configuration and environment separately at the destination. Do not assume AGENTS.md, Plugin, Skill or MCP support is equivalent across clients, or that the recipient may receive the same data.

### Control drift with accepted baselines

Retain versioned requirements, exact copy/public interfaces, adopted design references and representative acceptance cases at their existing owners. A model suggestion, newer summary or changed default is not authority to replace them. When prompts, models, Skills or tools change, compare relevant baseline and candidate outcomes with matched inputs and constraints; record actual client/model/settings and artifact revisions. Keep independent cases outside the tuning set when evaluating output quality.

Use deterministic checks for exact formats/invariants and explicit human criteria for open-ended quality. Model grading is advisory and cannot approve contracts, permissions or publication. Separate intended requirement changes, environment differences and model/output regressions. Preserve the last accepted baseline when a candidate is not accepted, without overwriting concurrent work. Document checks alone do not establish reduced drift or equivalent behavior across models.

For numerical or game work, distinguish exact calculation, approximation error, stochastic uncertainty and actual gameplay acceptance. Preserve units, rounding, initial conditions, time, formal rules and replay information; use the project's maintained simulation/verification capability rather than inventing a second implementation of its rules. UI prototypes, charts and simulations retain their actual evidence scope.

### Adopt only supported improvements

Classify a failure before changing guidance: requirement ambiguity, implementation defect, environment/setup, missing evidence, instruction conflict or obsolete source. Correct the narrow canonical owner, then affected consumers/teaching. Do not add Global rules for a one-off application defect or create a new Skill for a recoverable execution error.

For broad work, retain requirement -> inspected source coverage -> decision/artifact -> actual evidence -> gap in the existing acceptance view. Examples are not exhaustive scope; consider dependencies, failure/recovery, data lifecycle and completion conditions where relevant. When a user identifies an omission, locate its requirement and source, distinguish unread/stale/missed retrieval/lost summary/unsupported inference, inspect the smallest decisive evidence, and correct affected outputs and records. Acknowledgment alone does not resolve the omission. Repeated misses may justify a narrow index entry, check or representative failure case at the existing owner, not a mandatory full scan, reviewer chain or inferred permanent preference.

For a recurring failure, maintain a scoped known-issue entry in the existing project/reference location: symptom, applicable version/environment, evidence, unsuccessful attempts, supported remedy or fallback, owner/status and invalidation trigger. Link from the index when that symptom is relevant. Consult it before repeating the same attempt, but do not skip a required gate or keep a permanent prohibition after the conditions change. A changed context can justify an explicitly recorded recheck; preserve unresolved behavior and negative results.

Suggest recurring improvements with the observed pattern, actual evidence, proposed owner, benefit, maintenance cost, data/permission boundary and smallest acceptance trial. Stable deterministic processing belongs in an existing helper/core with explicit inputs, outputs, errors and side effects; reusable agent judgment belongs in a focused Skill/reference. Reuse maintained CLI/core logic, add an MCP adapter only for a demonstrated client-access gap, and do not schedule an unstable procedure. Frequency alone is not adoption evidence.

Surface current correctness, safety or acceptance impact promptly and complete authorized fixes. Keep optional improvements bounded and separate from required delivery; retain rejection/deferral and its revisit trigger rather than repeatedly recommending the same unchanged idea. An alert should identify the changed evidence, affected work and smallest useful next action, not create urgency from novelty or popularity.

Prefer an existing CLI for reproducible local search, Git and checks; prefer a suitable connector/MCP when approved account access, native structured objects or guarded edits require it. Compare actual capability, session, permissions, output and total cost, not transport labels. A new adapter defines schemas, errors, side effects, version compatibility and relevant retry/cancellation/concurrency safeguards around one maintained core. Configuration, authentication, discovery and successful calls are separate evidence.

Select a representation for the decision: mind maps for exploration, flow/sequence/state diagrams for ownership and behavior, tables for alternatives or traceability, reproducible plots for measured results, and interaction only when manipulating a model adds understanding. A visual is a projection, not a second source of truth. Separate desired values, observations and hypotheses; state disconfirming outcomes and use the smallest representative comparison that could change the decision. Preserve contrary results and uncertainty rather than treating correlation, popularity or model grading as causal proof.

Keep proposed memory or learned preferences human-reviewable at the approved existing destination, separate from effective requirements: source/date, applicable scope, proposed wording/change, acceptance/rejection and supersession. Do not silently promote inferred habits or temporary failures to Global, rewrite product memory stores, or transfer private history across AI products. Use the current product's supported and authorized memory/file workflow, and verify the adopted destination. Drafting a candidate and actual installation/loading are separate outcomes.

For a meaningful workflow change, compare representative matched tasks by accepted outcomes, regressions, rework and total cost/time when measured. Include interruption, a mid-task correction, dirty-source evidence and a negative authorization case when affected. Label manual walkthroughs, deterministic checks and observed model/runtime behavior separately; do not claim quality, speed or cross-device success from document checks.
