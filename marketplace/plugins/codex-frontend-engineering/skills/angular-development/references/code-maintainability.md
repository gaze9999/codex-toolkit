# Call-chain and Model simplification

Load for authorized implementation, refactoring or maintenance review. Trace the
affected callers and data owners before changing structure. These are selection
criteria, not permission to rewrite unrelated code or move every type into a
shared module.

## Keep useful behavior at each boundary

Trace the full event -> Component -> Service/store -> request -> projection -> view
flow. Check whether each step adds a business rule, required validation, state or
request ownership, cancellation, error translation or an established public API.

- Inline a private pass-through when it only forwards already-valid arguments or
  results and the caller remains clear. Check all references, receiver binding,
  evaluation order, side effects and return/Promise behavior first.
- Keep meaningful helpers for shared rules, reusable transformations, validation
  boundaries or substantial feature logic. File length, call count and a desire
  for fewer Component lines do not justify extraction or removal.
- Remove repeated validation, normalization or projection only after confirming
  the earlier boundary guarantees the same invariant and no mutation or async
  gap invalidates it. Keep validation of external input and independent callers.
- Avoid constructing a second Model or envelope with identical fields solely to
  pass it through another layer. Keep required request/response envelopes,
  serialization, class invariants, prototypes and distinct domain semantics.
- Remove intermediate objects/arrays, unused return-value computation and
  duplicated synchronization only when order, errors, null handling, mutation,
  reference identity and reactive notifications remain equivalent.
- Keep view controls, DOM/lifecycle and private interaction with the Component,
  shared state and API lifecycle with the existing Service/store owner, and pure
  feature rules/projections near that feature. Do not replace a large Component
  with a large Service or a new wrapping framework.

This private forwarding method adds no behavior when the repository is already
the request owner and all call sites are local:

```ts
// Before: another layer around the same validated request
private loadTasks(query: string): Promise<readonly Task[]> {
  return this.repository.load(query);
}
public search(query: string): Promise<readonly Task[]> {
  return this.loadTasks(query);
}

// After: preserve the public operation and its Promise
public search(query: string): Promise<readonly Task[]> {
  return this.repository.load(query);
}
```

The snippets are alternative members, not one combined class. Retain the helper
if it owns request cancellation, loading state, retries, caching or error
translation. Do not detach a method as a callback if it needs its receiver.

## Recover maintenance scope and actual consumers

Read the existing feature work record and still-effective user decisions before
selecting maintenance work. Track each applicable item's ID, owner, affected files,
expected behavior and evidence in the existing record or a compact task checklist.
Separate functional specification gaps, frontend cleanup, backend contracts and
framework/workspace policy by their actual owners. Move or link out-of-scope work
under the existing recording rules; preserve IDs and deferred decisions. Do not
invent a parallel backlog, include backend changes in frontend-only work or mark
items complete from a rename or file count.

Classify references as reads, writes, template consumers, public callers and
serialization/reflection consumers. Declaration/assignment counts alone do not
prove useful state or dead code. A field that mirrors a canonical value but is only
declared/written is a removal candidate after those consumers are checked. Keep
the canonical owner and its date/null/reactive behavior. A public API or externally
read field remains meaningful even without local reads. Report incomplete reference
coverage rather than deleting on that assumption.

For dropdown/list work, follow the input binding back through its actual callers
and mapper to the confirmed API response or fixed constants. An option-shaped type,
input name or a parent parameter named `options` does not establish its source.
Scope source-specific behavior to those verified paths. If the confirmed rule is
display-only, changing the placeholder must preserve the raw form/query/save value
and avoid synthetic fallback rows, change events or extra lookups. Preserve static
lists and inactive/commented feature entrypoints unless their change is authorized.

Review these representative cases against actual artifacts; they are acceptance
criteria, not claims of automated model execution:

| Case | Expected evidence |
| --- | --- |
| A field is written twice but never consumed | Inspect template/public/serialization consumers before removing the duplicate, preserve the canonical value |
| A helper adds cancellation or boundary validation | Keep that responsibility despite a long call chain; inline only genuine private forwarding |
| A child input receives fixed constants from one caller and API options from another | Trace each caller and apply only the authorized source-specific behavior |
| A frontend feature's maintenance list includes backend or workspace tasks | Preserve original IDs, route owners under existing document rules, and keep frontend completion scoped |

## Derive types when the meanings and change coupling agree

Use `interface ... extends ...` for a stable object extension, `Pick` for an
intentional field subset, `Omit` for a small intentional exclusion, and `&` to
compose compatible object parts. Preserve optional/readonly/null semantics,
units, discriminants and existing API field names. Check the actual TypeScript
version; `Pick` is available since 2.1 and built-in `Omit` since 3.5.

```ts
/** 工作資料, id 與 createdAt 由伺服器產生, title 為必要名稱 */
interface TaskRecord {
  readonly id: string;
  title: string;
  done: boolean;
  readonly createdAt: string;
}

// A local view extends the same object meaning with an actual display property
interface TaskRow extends TaskRecord {
  selected: boolean;
}

// Use a whitelist when only these fields may cross a write boundary
type TaskWrite = Pick<TaskRecord, 'title' | 'done'>;

// Suitable when new non-server fields should intentionally enter the draft too
type TaskDraft = Omit<TaskRecord, 'id' | 'createdAt'>;

// Compose existing compatible parts without repeating their field definitions
type SelectedTask = Pick<TaskRecord, 'id' | 'title'> & { selected: boolean };

function toTaskWrite(task: TaskRecord): TaskWrite {
  const { title, done } = task;
  return { title, done };
}
```

These types illustrate separate use cases; introduce only shapes actually
consumed by the feature, not every demonstrated alias.

`Pick`/`Omit` transform types; they do not filter, validate, clone or serialize an
object at runtime. Passing a TaskRecord as TaskWrite can still expose all its
fields. Keep an explicit runtime whitelist such as `toTaskWrite` at a write or
privacy boundary even when its output type is derived. Do not replace this with
an assertion or spread that forwards unknown/server-only fields.

Choose `Pick` when newly added source fields must stay out by default. Choose
`Omit` only when inheriting newly added fields matches the intended API. Neither
establishes exact-object validation. Keep independently evolving API/domain/form
models separate and map their real differences, including dates, units, nulls,
disabled form values or enum representation. Identical current fields alone do
not prove the types share a lifecycle.

Use `Omit<Base, 'field'> & { field: NewType }` for an intentional replacement
instead of conflicting intersections. `extends` rejects incompatible property
overrides; an incompatible intersection can produce an unusable `never` field.
For a discriminated union, check each branch's correlation before using a utility
type; ordinary `Pick`/`Omit` does not provide a per-branch transformation. Avoid
deep utility chains, one-use aliases and generic bases that cost more navigation
than the duplication they remove. A type alias with real domain meaning or an
external interface remains useful.

Follow the project's file-local type convention: when types belong above their
consumer, place small file-local interfaces/type aliases before that class,
keeping feature-shared types with their owner and substantial form types near
the form when appropriate. Ordering-only work does not authorize type extraction
or changes to type definitions. Use supported
`import type` for type-only imports; do not introduce cycles or one file per type
without a concrete cohesion or maintenance benefit.

## Verify the changed responsibility

Reconcile the scoped maintenance items with actual reads, writes, callers, option sources and data shapes, then run the affected project's type check and
focused behavior checks. Exercise field whitelists, null/error paths, Promise
handling and mutation/reactive timing when affected. Report the saved layer or
duplicated work concretely; fewer lines alone is not performance evidence.

Sources: [TypeScript utility types](https://www.typescriptlang.org/docs/handbook/utility-types.html),
[object extension and intersections](https://www.typescriptlang.org/docs/handbook/2/objects.html)
