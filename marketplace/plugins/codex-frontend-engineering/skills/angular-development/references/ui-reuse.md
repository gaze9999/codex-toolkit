# Select existing UI capabilities

Read for new/replaced generic UI or an explicit reuse review. A small defect in an
unchanged primitive does not require a new catalog audit or migration. Resolve
the actual project, Angular versions and authorized owners first.

## Find the correct source

Resolve the repository root from the active checkout. Resolve reference/document
roots from the task's confirmed sources or project guidance; logical roots need
not be directories inside that checkout. Verify targets and retain a compact
source pointer. Reuse it while project identity and relevant sources remain valid;
recheck affected mappings after a project/checkout/source change. Do not hardcode
a worktree, inherit another project's paths or silently skip required discovery.

Use the project's existing catalog, package aliases and public entrypoints.
Inspect the current exported API, implementation and real consumers. A name,
selector or shared folder alone proves neither compatibility nor actual reuse.
Do not deep import internals, import another application's private component or
modify a read-only library. Read-only ownership still permits consuming public APIs.

## Compare responsibilities and behavior

Separate reusable presentation/container behavior from business content. A small
text confirmation, editable note form and full business dialog need different
decisions. Rendering HTML is not a substitute for Angular forms or compiled bindings.
A transaction bridge wrapper is not automatically a general-purpose dialog shell.

Keep data, requests, persistence and permissions with their confirmed consumer
owner; a presentation component need not own them to be reusable. Check inputs,
outputs, validation timing, disabled/readonly, cancellation, teardown, provider
scope, styles and required interactions. Distinguish configurable defaults from
actual missing capabilities. For example, a configurable size limit differs from
a picker that clears the previous file after a rejected selection.

Compare source/visual requirements with observed behavior. A preferred local
structure or existing overlay does not establish a specification requirement.
Do not force reuse when required behavior cannot be preserved, invent a platform
dependency or widen ownership merely to avoid local code. Preserve business
components when needed and assess their container separately.

## Record and verify the selection

Use the existing reuse assessment or delivery table. Record only relevant fields:

| Capability | Public source and real consumer | Decision | Concrete requirement/gap | Verification |
| --- | --- | --- | --- | --- |
| Selected UI behavior | Existing export and observed use | Reuse, adapt or retain local | Input/event/state/style behavior with specification evidence | Actual imports/templates and affected checks, or pending adoption |

These are fields for an existing record, not a new tracker or mandatory form for
every change. Reuse/adapt/local describes a capability decision, not implementation
or acceptance. Revisit only affected decisions when APIs, requirements or sources
change. Keep project-specific fields/paths and customer data in their private owner.

For an authorized implementation, inspect final imports/templates and run the
smallest relevant type, interaction and lifecycle checks. Preserve loading and
error paths, raw values, pending files and request ownership. Source comparison,
compiled integration, rendered behavior and persistence remain separate evidence.
For an audit, report decisions and evidence without changing code or installation.
