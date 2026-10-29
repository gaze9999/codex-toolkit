# Application and delivery cases

Read for affected browser, API, storage, CLI or packaging behavior. Select by requirements and diff, not every row. Use the project's actual commands and supported tool versions.

| Boundary or signal | Useful evidence | Remaining acceptance |
|---|---|---|
| Deterministic rules or parsing | Independent expected fixture, boundaries, generated inputs, round trips and justified invariants | Real consumers and runtime inputs |
| Browser/UI changes | State transitions, keyboard/focus, accessible names, responsive/zoom conditions, stale responses, console/network and served bundle | Other browser engines, touch devices, actual backend |
| Shared UI or library | Public interface checks against affected consumers, mount/update/destroy lifecycle, listener cancellation and supported fallback | Consumer integration and native WebView/platform |
| Extension | Manifest permissions, message boundaries, service-worker suspension/restart, content-script match rules and an isolated browser profile | Extension packaging, real target-site changes and policy review |
| API write | Actual payload schema, auth boundary, response identity, timeout/unknown outcome and idempotency rules | Authoritative persisted state, role/session and integration |
| Storage or migration | Versioned golden fixtures, corrupted/unknown input, backup preservation, quota/write failure, recovery and multi-owner conflict | Actual store/process crash behavior under authorized isolation |
| CLI/setup | Help/exit codes, configuration precedence, dry-run, path/Unicode/permission failures, bounded child-process cleanup | Native OS/architecture and signed/packaged artifacts |
| Release package | Version/license/notices, reproducible inputs, expected files/entrypoints, hashes and clean-environment smoke | Actual target OS, signing, download/readback and deployment |

Development: turn a concrete defect or changed requirement into a useful failing check when justified, then verify its repair. Testing: preserve scope, fixtures and source state; investigate flaky failures without hiding them. Release: apply the actual project gate, route artifact acceptance to an available packaging-acceptance Skill, and separate preparation from authorized publication.

## Custom runners and isolated fixtures

Read when creating or repairing a custom runner; existing test frameworks may already enforce these conditions.

- Declare required scripts, fixture HTML/bundles and other inputs. Check their existence, readability and required nonempty content before opening a browser/server or starting a costly process. Missing required input fails nonzero; optional inputs are named and reported separately, never silently substituted for required checks.
- Preserve earlier evidence before reuse, or select a fresh result location. Record a run identity/time, started state, terminal status, required selection and actually executed scripts/checks. An interrupted run or a stale success file is not a successful current run. Report errors and the original exit code even when cleanup or result writing fails.
- Exercise a missing-input case in a temporary copy, without deleting or renaming the real input. Confirm nonzero failure, no dependent resource startup and no stale success claim. Verify the normal selected fixture too; identify the bundle/revision actually loaded rather than treating it as the current checkout.
- Resolve compiler, bundler and framework dependencies from the selected project's existing manifest/module resolution. A helper runner's own folder or client runtime does not establish the project's package versions. Do not install or change dependencies to repair a lookup path without authorization.
- Retain the first setup failure and diagnose compiler/resource resolution, browser errors and readiness separately. Wait for the relevant observable render/state/CSS condition with a bounded timeout; do not add product timers to satisfy the fixture.
- Clean up owned browser, server and subprocess resources independently so one cleanup failure does not skip the rest. Retain cleanup failures and distinguish resources never started from resources closed after execution.

For a scoped syntax/refactor comparison, parse with the project's compatible parser. State the reviewed normalizations and excluded imports/comments/regions; retain literal values and distinguish structural equality from full semantic equivalence. Pair this evidence with the affected type/interface and runtime checks. Fixture data, intercepted requests and a simulated host establish only those exercised boundaries, not formal API, persistence or host acceptance.

## Loaded behavior and consumer boundaries

Read for changed settings, service/API behavior or shared-component integration. Select the affected links in the chain rather than treating one successful check as evidence for all of them.

- For configuration changes, distinguish saved configuration, emitted request, returned response and the service's loaded state. A validated file or successful response does not show that an existing process loaded the new setting; inspect the relevant runtime through its established entry point.
- For a shared API, compare the callable runtime entry, published declarations when present, supported capability detection and affected consumer usage. Keep proposed interfaces separate from implemented callable APIs, and verify the consumer's actual bundle/pin independently of the source checkout.
- For close/reset/destroy changes, exercise the documented preserve/dispose policy: static form state, dynamically owned content, requests/subscriptions and later reopen behavior as applicable. Check bounded history/pending data and listener cleanup where those resources exist; do not infer retention from an empty panel.
- For an affected native capability or fallback, verify the selected branch in supported environments or an explicitly isolated fixture. Record how the fallback was selected and its evidence limits. For floating-widget semantics, focus and layering, use the applicable UI acceptance reference or primary pattern rather than treating all overlays as the same widget.

For retention or performance, capture a comparable baseline and workload, warm/cold states, wall time and attributable resources. Multiple tools or services running concurrently are nuisance factors, not a formula for removing load. Match chart units, sorting, sampling and aggregation to raw fixtures. An aggregate metric cannot prove every underlying record.

For collection/streaming changes, burst handling or long-running resource checks, use [performance and streaming updates](performance-and-streams.md) to select layer-specific measurements, bounded diagnostics and recovery cases.

For recorded intermittent failures and broader coverage gaps, an available validation-evidence-review Skill supplies conditional risk cases and statistical interpretation. Without it, keep claims descriptive unless the sampling unit, independence, estimator and uncertainty are established. Do not turn isolated fixtures into production reliability percentages.

Sources: [Playwright practices](https://playwright.dev/docs/best-practices), [pytest flaky tests](https://docs.pytest.org/en/stable/explanation/flaky.html), [Chrome memory problems](https://developer.chrome.com/docs/devtools/memory-problems). Recheck exact installed versions when using their commands or APIs.
