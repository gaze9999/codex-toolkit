# Context continuity

Use this reference when governance work changes role context, persistent goals, new-conversation recovery, compaction, task switching, handoffs, memory or Context Brief behavior.

- Do not impose fixed message, compaction, token or elapsed-time thresholds for another task. Continue while one outcome remains active and retained state is reliable; a model change alone does not require a new task.
- Recommend a separate task for a distinct deliverable or when stale accumulated context causes repeated contradictions or lost constraints. Create it only with explicit authorization for a large, independently reviewable phase likely to need multiple turns. Fork only when that authorized task needs prior history; a fresh task and compact handoff serve clean-context needs.
- Use a Context Brief only for reusable implementation requirements from identified specifications, APIs, schemas, integration guides or acceptance criteria. Keep transcripts and routine progress out of it.

## Continue with ongoing user guidance

- Track each execution from its initiating request and still-effective prior decisions. Incorporate every steering message received before that execution finishes, including questions, corrections, constraints and acceptance changes. Preserve effective items regardless of duration, message count or compaction; do not treat the entire chat history as the current execution's scope.
- Interpret a new message against the active outcome and effective decisions. It may add requirements, correct a decision, ask a question or change scope; retain valid goals, authority, constraints and unfinished work unless the user cancels or replaces them. Resolve an ambiguity from available evidence first; block only dependent work when a decision is missing.
- Map changed guidance to prior decisions, delivered artifacts and pending work. Identify superseded decisions explicitly. When completed work is affected, mark only the necessary slice pending recheck, inspect its changes and relevant evidence, and preserve unaffected accepted results.
- For a multi-stage or repeatedly steered execution, keep current execution state in conversation/task context: initiating requirements and later steering, effective goal/authority/constraints, decisions/sources, completed versus pending acceptance, unfinished work, blockers, owner/dependencies, evidence and next action. Persist durable state in an existing permitted project record when requested or required by applicable guidance. Do not create a separate report, duplicate the record, copy transcripts or put routine progress in a Context Brief.
- Update that state after a milestone, consequential decision/scope change, blocker or before handoff. Follow an existing history convention when present. Do not create a summary for every message or rely on predicting compaction; maintain recoverable state during meaningful work.
- After interruption, compaction or a change of owner, recover the current state and verify the relevant sources/artifacts and evidence. In a Git workspace, confirm the relevant branch and diff; recheck only changed facts and affected behavior. Missing context does not establish completion and does not require repeating unaffected investigation.
- Answer an inserted question or status request, then resume the active outcome unless the user replaced it or the next step lacks necessary information/authority. Before ending, reconcile the initiating request and every effective steering item against delivered/accepted work and evidence. State progress, deviations and remaining work in the conversation, not only the outcome of the latest message.

The milestone, decision-note and validation approach is informed by [OpenAI's long-horizon task case](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex). Adapt the case to existing project records; its filenames and model are not requirements for this workflow.

## Recover durable goals in a new conversation

- For a project with durable cross-conversation work or existing tracking requirements, starting or resuming relevant work triggers recovery, including a conversation opened directly by the user without a prior handoff. Resolve the relevant record from applicable project instructions or existing tracking configuration. Read only the selected project's/task's authorized content; a new conversation does not require scanning every project or reconstructing old chats.
- Project instructions identify the maintained record, applicable work and update conditions. Reuse the existing current-state document, approved tracking Page or task system and its format. One tracker may serve multiple projects with distinct project/task identities; do not create a document for every repository or one-off task. Company material stays in its approved environment; a personal Space is not the universal destination. Keep device paths or private record IDs in their permitted scope, not portable public guidance.
- Keep the intended outcome, effective decisions/constraints and acceptance distinct from observed state, differences, pending work and next action. Preserve the same project/task identity across conversations and devices. Completion requires acceptance evidence; cancellation or replacement requires a confirmed decision. A newer status entry, an inaccessible chat or a conversation change does not reset the goal.
- Read relevant recorded state before dependent work, then reconcile the current request, original specifications and actual artifacts. Confirm relevant branch/diff and evidence limits. Apply new guidance only to affected goals/decisions; retain unresolved differences and ask only for the missing dependent decision or source. A record supplies context, not additional execution or publication authority.

Maintain the selected record at meaningful changes using its existing write/conflict guards; see [shared workflow](shared-workflow.md). Do not require a new filename, schema, handoff document or per-message log.

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
