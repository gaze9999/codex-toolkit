# Suite API

Read when writing or reviewing a suite for `scripts/run.mjs`. The harness source is [scripts/harness/index.ts](../scripts/harness/index.ts).

## Imports

| Specifier | Resolves to |
| --- | --- |
| `@component-test/harness` | Test helpers below |
| `@project/<path>` | `<--project>/<path>`, for example `@project/src/app/orders/order-form.component` |
| Project aliases from `--tsconfig` | Unchanged, for example a workspace library alias |

Every TypeScript import is AOT-compiled by the project's `ngc`; the runner rejects a bundle that still contains TypeScript source. A JavaScript alias target is bundled as is.

## Expected values

Derive each expected value from the code's intended contract: the name, JSDoc or comments of the code under test and the developer's stated decisions. Do not read or cite specifications here; specification conformance belongs to a specification verification tool. Never run the code under test first and copy its output into an expectation. When the contract is unclear, ask the developer or record the value with `observe` instead of judging it.

## Cases

| API | Use |
| --- | --- |
| `group(name)` | Group name for the following cases, such as one form or component |
| `test(id, name, fn)` | Judged case; `fn(check)` may be async and needs at least one judgment, otherwise it is an error |
| `observe(id, name, fn)` | Records values without a verdict; never counts as passed |
| `check.equal(actual, expected, label)` | Deep equality on plain values |
| `check.ok(condition, label, actual?)` | Boolean judgment, optionally recording the actual value |
| `check.observe(value)` | Records an observed value on the case |

Cases run one at a time in definition order. A thrown error or a case timeout (`--case-timeout`) marks that case as error and the next case still runs. Values cross the DevTools boundary as JSON: functions, `undefined` and cycles become text.

## Mounting and DOM helpers

| API | Use |
| --- | --- |
| `mount(Component, providers?)` | Bootstraps a standalone host component with an element selector in its own application; returns `ref`, `host`, `element`, `settle()`, `destroy()` |
| `settle()` | Runs change detection, waits one timer turn and runs it again |
| `typeBlur(selector, text)` | Sets the input value and dispatches `input` and `blur`; a wrapper selector uses its first `input` |
| `click(selector)` | Clicks the element and waits one timer turn |
| `query(selector)`, `input(selector)` | Find an element or input, throwing when missing |
| `wait(ms)` | Timer delay |

- Without zone.js in the project, `mount` adds the zoneless change-detection provider that the Angular version exports. Call `settle()` after state changes that the test drives directly.
- Synchronous change detection: suite code runs outside Angular's zone, so a value assigned on `host` renders only after `mounted.ref.tick()`.
- Deferred change detection: `await mounted.settle()` renders a `setTimeout(0)` or promise update scheduled before the call. For longer delays, `await wait(ms)` first.
- Scope DOM reads to `mounted.element` when one case mounts several times; when a later case mounts the same selector, call `destroy()` and remove `mounted.element`.

## Result shape

Each case in `report.json` `results[]` is `{ id, group, name, status, assertions: [{ label, pass, actual, expected? }], observed?, message?, elapsedMs }`.

| `status` | When |
| --- | --- |
| `passed` | A `test` with at least one judgment, all passing |
| `failed` | Any judgment did not pass |
| `error` | Thrown error, case timeout or a `test` with no judgment; `message` holds the stack and earlier judgments are kept |
| `info` | An `observe` case; never judged |

`check.observe(value)` works in both `test` and `observe` cases; the last call is kept in `observed`. The report also holds `summary { total, passed, failed, error, info }`, `exitCode`, `statusText`, `runtime`, `sources`, `consoleErrors` and `limits`; `report.md` and `report.html` render the same model.
- Destroy each mounted application at the end of its case so later cases start from a clean document.
- Gate a form behind `@if (show)` in the host when service state must be prepared before the form is created; toggle `show` and `settle()` to simulate reopening.

## Stand-in services

Replace network and host-bridge services with providers so no case reaches a real API:

```ts
const api = new Proxy({}, { get: (_target, key) => (key === 'then' ? undefined : () => EMPTY) });
await mount(OrderHost, [{ provide: OrderApiService, useValue: api }]);
```

Record outgoing requests in the stand-in when a case judges them. Real services may log errors for empty responses; read the report's browser errors before judging.

## Evidence limits

- `typeBlur` and `click` are script-dispatched events, not native keyboard, paste or IME evidence. Disabled inputs still receive dispatched events, which is how disabled guards are exercised.
- Partially compiled libraries are JIT-compiled in the page by `@angular/compiler`; project components are AOT.
- Component stylesheets are not compiled, so layout is not evidence.
- Results cover the mounted components and stand-ins only.
