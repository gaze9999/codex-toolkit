# Delegation and model routing

Use this reference only when governance work changes subagents, roles, worker ownership, or model and reasoning selection. For role context or handoff design, also read [context-continuity.md](context-continuity.md).

## Choose the execution mode

- Delegate only when current user, project, and environment policy allow it. The primary agent retains requirement interpretation, architecture/pattern and cross-module decisions, necessary direct implementation, integration, final review and acceptance unless explicitly reassigned.
- Choose from the work's independence, context-isolation value, coordination cost and acceptance burden. Direct execution and no subagents are normal outcomes; separate model and tool work is not a token-saving claim.
- Preserve direct execution across main-model changes. Prefer batched tools for mechanical work; reuse a suitable owner instead of creating tiny workers, recursive delegation or routine review chains. Separate user-owned tasks need an independent follow-up lifecycle and explicit authorization; a bounded child stays inside the current task. Use an available task-routing Skill for operational routing, without making it a prerequisite for ordinary edits.

| Mode | Use when | Ownership |
|---|---|---|
| Direct execution | The work is small, tightly coupled or already understood | Main completes discovery, edits and checks |
| Exploration then execution | A bounded unfamiliar area requires substantial reading | Explorer returns evidence; Main decides and implements or assigns a worker |
| One complete worker slice | Goal, boundaries and acceptance are clear | One worker completes discovery, edit, checks and in-scope fixes |
| Independent parallel slices | Shared interfaces are settled and mutable resources can be isolated | Each worker owns one slice; Main integrates and accepts the combined result |

- Keep one coupled feature path with one implementation owner, including its state, callers, interfaces and related checks. Splitting by file extension or using different files/worktrees does not establish semantic independence.
- Before parallel writes, confirm disjoint ownership, shared-interface decisions, test data, ports, temporary outputs and browser sessions. Sequence dependent steps and shared mutable resources; choose concurrency that the primary owner can actually review and integrate.

## Worker loop and acceptance

- Give the worker a self-contained goal, confirmed requirements and sources, owned files/modules, must-preserve constraints, exclusions, relevant checkout and concurrent-work state, acceptance criteria and stop condition. Do not require rediscovery of supported conclusions.
- Let the worker choose implementation details within those boundaries and complete discovery, edit, focused checks and necessary repairs. Prefer supported waiting and one final review over repeated partial handoffs or progress polling.
- Return to Main when specifications conflict, a shared interface must change, ownership or authorization must expand, or the approach repeatedly fails. Explain facts, attempts, failure evidence and the decision needed; continue independent authorized work when possible.
- Define acceptance before dispatch; return the source revision or relevant diff state, changed behavior/files, each criterion as met/not met/unverified, actual checks and next action. Main retains pending work until accepted, confirms adoption of user/source changes, and does not infer completion from silence or interruption. Verification applies only to the checked code state; later relevant edits require affected checks again.
- Add independent review only for concrete coverage or risk. Give the reviewer original requirements, acceptance criteria, applicable rules and the actual diff/revision with relevant code; avoid leading it with the implementer's conclusions.
- Findings identify file/symbol, trigger, expected versus actual behavior, impact and evidence. Separate defects from questions, allow no findings, and avoid style-only or out-of-scope blockers. Main evaluates findings before assigning in-scope repairs to the implementation owner and accepting the integrated result.

## Models, context and permissions

- Keep portable Skills and templates model-agnostic. Personal fallbacks belong in maintained configuration; brief selection preferences belong in global instructions. Main selection remains in chat/session settings. Judge a child independently of Main effort; do not copy a high-effort setting to every child or downgrade uncertain work solely for a cheaper label. Inspect effective defaults/pins before dispatch and preserve explicit user choices.
- Decide whether a slice executes a known approach or must determine it. Select supported model and effort from uncertainty, risk, public-interface impact, tools and verification burden rather than trying every effort level. Higher effort cannot resolve missing authority or broken tooling. Maximum effort may fit a difficult bounded task when its latency is acceptable; compare total work per accepted result, including retries, review and repairs, before claiming savings or speed.
- Resolve current configuration precedence before changing pins. In Codex, explicit spawn values override corresponding `[agents]` defaults. If either selects a model and neither supplies effort, the child uses that model's default effort; when no model/effort is configured, it inherits the parent settings.
- Custom role model/effort pins override the previously resolved settings. A model-only pin retains previously resolved effort, so check compatibility. Keep variable-workload roles unpinned with a suitable fallback; use an unpinned role with equivalent ownership and permissions when a pinned role's model does not fit.
- Explorer and Reviewer remain read-only. Match role instructions with sandbox and tool permissions, then verify the effective spawned configuration: live parent runtime overrides may supersede role sandbox defaults. A parsed file, model self-identification or updated mirror does not prove runtime reload.
- Stop and reroute repeated failures, lost context or expanded ownership. Pass confirmed facts, attempts and evidence to the next owner; a model recommendation does not switch a session or authorize delegation.
