# Task routing and handoff

Read only when deciding task creation/forking, subagent delegation or an ownership handoff.

- Keep small, dependent or unresolved work in the current task and reuse a suitable owner. Conversation length or Main model changes do not require a new task.
- Consider a user-owned task for a large, independently reviewable phase expected to need several turns. Creation requires explicit user authorization; satisfy conditional authorization first.
- Fork an authorized task only when its history is needed. Create a fresh task when a concise handoff suffices; worktree handoff moves the same task.
- Delegate only when allowed. Require an independent slice, clear ownership and acceptance. Keep coupled behavior/checks with one owner; parallel writes require confirmed shared interfaces and isolated mutable resources. Select the minimum sufficient owners by quality, time and context needs.
- Handoff purpose, confirmed decisions/sources, change/prohibited scope, checkout/worktree and relevant uncommitted/ignored files, acceptance, unresolved items and stop conditions. Adjust context to the role; retain failed attempts only when they affect decisions. Identify independent tasks by `threadId`.
- Communicate changed specifications/decisions to affected owners only under existing coordination authorization. Identify work requiring recheck; a fork does not receive later decisions automatically.
- Keep the original request and every effective steering item for this execution, authorization/limits, completed/pending acceptance, unfinished work, owner/ID, dependencies, evidence and next actions primarily in conversation/task context. Use files only when requested or required by applicable guidance. Check state at decisions/milestones and restore relevant evidence after interruption/compaction. Returned work awaits acceptance; silence/interruption is not completion.
- End while work is pending only when the user permits background execution/handoff, explaining remaining work and tracking. Otherwise complete necessary work. Validate returned results against acceptance and actual code, preserving issue sources/status.
- Messaging an independent user-owned task requires explicit user authorization for that target. Agent messages, known IDs, task-creation permission or tool availability do not authorize messaging. Otherwise retain decisions in current context/authorized records and reconcile when results return; parent/subagent coordination follows applicable rules.
