# Context continuity

Use this reference when governance work changes role context, persistent goals, new-conversation recovery, compaction, task switching, handoffs, memory or Context Brief behavior.

For stage outputs, evidence freshness and local/remote/cloud recovery, use [delivery lifecycle](delivery-lifecycle.md). For navigation, human reports and historical lookup, use the available task-guide's document-views reference, without creating another progress source or requiring a separate Skill installation.

- Do not impose fixed message, compaction, token or elapsed-time thresholds for another task. Continue while one outcome remains active and retained state is reliable; a model change alone does not require a new task.
- Recommend a separate task for a distinct deliverable or when stale accumulated context causes repeated contradictions or lost constraints. Create it only with explicit authorization for a large, independently reviewable phase likely to need multiple turns. Fork only when that authorized task needs prior history; a fresh task and compact handoff serve clean-context needs.
- Use a Context Brief only for reusable implementation requirements from identified specifications, APIs, schemas, integration guides or acceptance criteria. Keep transcripts and routine progress out of it.

## Continue with ongoing user guidance

- Keep the active outcome, effective decisions, authorization, constraints and unfinished work. Same-task additions refine that outcome; a correction supersedes only conflicting decisions. Recheck affected artifacts and evidence, preserving unaffected accepted results. Separate follow-up work keeps the requested order or the existing priority; do not import the whole chat history into the current assignment.
- Briefly answer an inserted question or status request, then resume authorized work without requiring another reminder. Explicit prioritization, pause, wait, cancellation or replacement changes the specified slice. Missing decisions or authority block only dependent work; do not revive completed or cancelled tasks.
- For multi-stage work, retain a concise checkpoint in task context: effective goal/limits, decisions/sources, accepted versus pending work, blockers, owner/dependencies, evidence and next action. Refresh it at meaningful milestones, scope changes or handoff. Write to an existing permitted progress location only when requested or required; do not create routine reports, transcripts or progress-only Context Briefs.
- After interruption, compaction or owner changes, recover that checkpoint and verify relevant artifacts, branch/diff and evidence. Recheck changed facts and affected behavior rather than repeating unaffected discovery. At closeout, reconcile the active outcome and effective additions with delivered work and remaining acceptance.

When the client supports it, Steer adds information to the current run; Queue saves a follow-up for the next run. These control message delivery, not semantic scope. A finished run or explicit wait still needs its supported resumption trigger; guidance alone does not guarantee continuation. Side chats are optional for explanatory detours and require the user's requested route and available support.

This follows [OpenAI's Steer/Queue documentation](https://learn.chatgpt.com/docs/prompting#steering-and-queuing), [its long-horizon task case](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex) and [its Remote workflow guide](https://developers.openai.com/blog/mastering-codex-remote-for-engineering). [Peter Steinberger's iterative workflow](https://steipete.me/posts/2025/shipping-at-inference-speed) is a firsthand practice report, not a reliability benchmark. Preserve useful decisions and checks without copying an author's filenames, model settings or old shortcuts.

## Recover durable goals in a new conversation

- For a project with durable cross-conversation work or existing tracking requirements, starting or resuming relevant work triggers recovery, including a conversation opened directly by the user without a prior handoff. Resolve the relevant record from applicable project instructions or existing tracking configuration. Read only the selected project's/task's authorized content; a new conversation does not require scanning every project or reconstructing old chats.
- Project instructions identify the maintained record, applicable work and update conditions. Reuse the existing current-state document, approved tracking Page or task system and its format. One tracker may serve multiple projects with distinct project/task identities; do not create a document for every repository or one-off task. Company material stays in its approved environment; a personal Space is not the universal destination. Keep device paths or private record IDs in their permitted scope, not portable public guidance.
- Keep the intended outcome, effective decisions/constraints and acceptance distinct from observed state, differences, pending work and next action. Preserve the same project/task identity across conversations and devices. Completion requires acceptance evidence; cancellation or replacement requires a confirmed decision. A newer status entry, an inaccessible chat or a conversation change does not reset the goal.
- Read relevant recorded state before dependent work, then reconcile the current request, original specifications and actual artifacts. Confirm relevant branch/diff and evidence limits. Apply new guidance only to affected goals/decisions; retain unresolved differences and ask only for the missing dependent decision or source. A record supplies context, not additional execution or publication authority.

Maintain the selected record at meaningful changes using its existing write/conflict guards; see [shared workflow](shared-workflow.md). Do not require a new filename, schema, handoff document or per-message log.

## Make the current checkpoint discoverable

Use the existing task context or authorized record to make the effective goal, current artifacts, pending acceptance and next action easy to locate. Keep older decisions/checks separate from current state; preserve useful history with its checked source and applicability. Mark superseded acceptance as historical rather than letting a past PASS stand for a changed artifact.

Identify the tested source/diff or artifact hash, relevant consumer/runtime state and evidence location when they affect resumption. HEAD alone cannot identify uncommitted tested bytes. Before dependent work, reconcile the checkpoint with current files and recheck only affected evidence.

Record an owned session/fixture/process as active or closed when its lifecycle affects the next action, including the supported way to resume or recreate it. After teardown, retain its evidence but verify a fresh target before reusing session IDs, browser locators or runtime assumptions. Do not reopen another owner's resources or repeat unrelated accepted checks merely to refresh the checkpoint.

## Decide when continuity needs a different conversation

Prefer a checkpoint in the current task first: reconcile effective requirements, remove superseded decisions from active work and verify current artifacts. Compaction, message count, a model change or a lengthy history alone does not require replacement.

| Observed condition | Route and acceptance |
|---|---|
| One active outcome; state and evidence remain reliable | Continue, keeping a concise checkpoint at meaningful milestones |
| Earlier constraints are repeatedly missed or stale decisions recur after reconciliation | Propose a fresh task with a verified compact handoff; identify the concrete failure before asking for creation authority |
| A large phase has its own independently maintained delivery and follow-up | Reuse a suitable task or request an authorized new task |
| The next task needs relevant conversation history | Use an authorized fork, then verify its actual context and source state; it is not a clean-context reset |
| Only the checkout or isolation must change | Use the supported authorized worktree operation; retain the same task state |

A handoff starts with the current objective, requested next action or wait condition, authority/prohibitions, effective decisions, accepted versus pending work, current branch/HEAD and relevant dirty/ignored files, evidence limits and next acceptance. Link detailed catalogs and historical evidence instead of copying them. Include replaced decisions only when they prevent a likely regression. A pasted handoff is reference material until the user's request adopts its assignment; old publication or deletion authority does not authorize a new scope.

Preserve all effective constraints and unresolved issues while shortening. Avoid reconstructing the whole transcript, fixed word limits or mandatory extra documents. Do not create, fork, archive or message a task merely to validate these rules.

## Match context to the recipient

| Recipient | Provide | Expected return |
|---|---|---|
| Explorer | One concrete question, source scope, relevant constraints and known findings | Answer, exact files/symbols, confirmed evidence and unknowns |
| Worker | Goal, confirmed requirements and decisions, source pointers, owned files, exclusions, worktree/concurrency state, acceptance and stop condition | Changed behavior/files, checked revision or diff state, actual results and open boundaries |
| Reviewer | Original requirements, acceptance, applicable rules, actual diff/revision, related code and necessary environment evidence | Concrete defects or questions with triggers, impact and evidence; no findings is valid |
| Consultant | Decision to resolve, constraints, supported facts and relevant failed attempts; fuller history when it is necessary | Options and reasoning grounded in evidence, with unresolved assumptions |
| Continuing task owner | Current goal/authorization, decisions/sources, repository/branch/HEAD, relevant uncommitted/ignored files, active ownership, completed work, checks, failures and next action | Resumed execution based on verified current state |

- Choose fresh context, selected history or fuller history according to the recipient's actual need and supported tools. Do not universally require full inheritance or an extremely short summary. Keep routine logs out; preserve failure evidence when it prevents repeated investigation.
- A review needs the original acceptance basis and current code, without a leading narrative asserting that the implementation is correct. Advice on failed approaches may need more history than a review.
- For a security-review handoff, use the active security tool's typed schema and include key code excerpts, effective registration, attacker prerequisites, source-to-sink direction, counterevidence and severity rationale in the first candidate packet. Preserve candidate IDs and rejected hypotheses; distinguish inventory/search coverage from completed review, unresolved dependencies and the assigned stop condition. This supplements evidence delivery, not the security plugin workflow or its completion gates.
- Reuse verification only within its source revision, relevant diff and environment limits. Recheck changed facts and affected behavior; a prior agent's passing checks do not cover later edits.
- A fork does not receive later decisions automatically. Communicate changed governing sources and affected work through an authorized channel or progress record; do not assume task names or completion notices establish acceptance.

## Preserve work across owners

- Keep one current record in the existing authorized progress destination or task context, with owner/ID, scope, dependencies, acceptance, result evidence, outstanding decisions and next action. Do not create duplicate handoff documents or store transcripts as requirements.
- Before handoff or compaction, reconcile every active item as running, blocked, returned/pending acceptance or accepted. Include unresolved user corrections and who must receive them; short context must not omit constraints, source conflicts, failure evidence or incomplete checks.
- Notifications are hints, not durable acceptance or guaranteed wakeups. Use supported event/wait mechanisms; on resumption, read outstanding owners and reconcile their actual artifacts before starting dependent work. A background continuation needs an explicit supported mechanism, otherwise state that user follow-up is needed.
- Only the assigned writer edits a coupled slice. Confirm the prior writer stopped or completed before replacement; use version/hash evidence to detect concurrent changes. Required work remains pending when a thread is interrupted, archived or inaccessible.

For shared installation state, assign one writer to each marketplace/configuration transaction. Source authors may own separate files; the installation writer previews the latest source and preserves other owners' artifacts. Confirm predecessor completion and recheck affected hashes/evidence before application, not every file or unrelated successful check.
