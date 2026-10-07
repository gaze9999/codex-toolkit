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

Keep small private types near their use, feature-shared types with their owner
and substantial form types near the form when appropriate. Use supported
`import type` for type-only imports; do not introduce cycles or one file per type
without a concrete cohesion or maintenance benefit.

## Verify the changed responsibility

Review callers and data shapes, then run the affected project's type check and
focused behavior checks. Exercise field whitelists, null/error paths, Promise
handling and mutation/reactive timing when affected. Report the saved layer or
duplicated work concretely; fewer lines alone is not performance evidence.

Sources: [TypeScript utility types](https://www.typescriptlang.org/docs/handbook/utility-types.html),
[object extension and intersections](https://www.typescriptlang.org/docs/handbook/2/objects.html)
