# Conditional testing risk cases

Read when reviewing test gaps, intermittent failures or next-check recommendations. Select only relevant rows from the actual diff, requirements, failure signals and evidence. These are scenarios to assess, not confirmed defects or an automatic full-suite plan. Existing required CI/release gates still apply. Keep execution authorization separate from a review recommendation.

## Choose the next evidence

| Signal or affected behavior | Smallest useful check or evidence | Do not infer |
|---|---|---|
| Many passing assertions but unclear expected behavior | Trace critical assertions to governing rules; distinguish independent oracle, fixture assumptions and implementation-derived expected values | A test mirroring the implementation establishes correctness |
| Roles, stages or action conditions interact | Decision table for valid combinations, mandatory negatives and critical higher-order interactions; see statistical interpretation for covering arrays | Pairwise cases cover every workflow or server permission |
| Sorting, grouping, parsing or aggregates change | Boundary/generated inputs and justified invariants, stable IDs/order, zero/null/missing distinctions, totals and round-trip semantics | A plausible chart or self-consistent output is numerically correct |
| Async refresh, navigation, close/reopen or rapid typing | Replay out-of-order completions, cancellation, stale callbacks and overlapping requests with deterministic scheduling when supported | One successful click excludes races |
| Double-click, network retry or timeout during a write | Inspect actual idempotency rules, request identity and authoritative persistence; distinguish rejected, pending, committed and unknown outcomes | Retrying a timed-out operation is safe or cannot duplicate it |
| Empty, loading, stale, error and partial results | Observe transitions with both no prior data and retained data, bounded retries and actionable recovery | Rendering an empty placeholder proves successful data loading |
| Flaky result or failure only in parallel/CI | Preserve first failure, trace/seed, order, fixture ownership and shared resources; compare one isolated replay with the original conditions | A retry PASS erases failure or proves environment-only cause |
| Selector or timing-related browser failure | User-facing stable locator, explicit readiness/state and bounded web-first assertions; inspect console/network/trace as needed | Longer arbitrary sleep repairs the behavior |
| Unexpected old behavior after code change | Match served artifact/bundle, build inputs, source hash, service-worker/cache state and actual entrypoint | Current HEAD is the code running in the browser |
| Mocks or isolated harness pass | State exactly which services, identity and persistence were replaced; identify the remaining integration/Host/API gate | Mock PASS establishes real API, authorization or saved state |
| Request/response or serialized data changes | Verify actual schema/version, omission/null/clear behavior, response errors and compatibility with affected consumers | Type-check PASS proves transport or runtime compatibility |
| Persistence, migrations or partial failures | Readback/reopen and allowed rollback/atomicity checks in an isolated approved store | A successful response or local state update proves durable storage |
| UI looks right at one size | Font/zoom, long text, empty/large data, narrow layout, keyboard focus, reduced motion and loading-state bounds by affected behavior | A screenshot proves interaction, accessibility or every device |
| Visual snapshot changes | Hold browser/OS/fonts/render readiness stable; inspect semantic and geometry differences before accepting a new baseline | Automatically updating a snapshot resolves a regression |
| Mobile or cross-browser support claim | Separate emulation from actual engine/device evidence, touch/focus/viewport behavior and supported runtime APIs | Desktop emulation proves physical Safari/iPad compatibility |
| Numeric, temporal or localized inputs | Thresholds, rounding/unit rules, overflow/NaN where applicable, timezone/DST boundaries, locale formatting and Unicode/IME | Display formatting preserves stored values or every locale |
| Attachments, downloads or large payloads | Allowed types/sizes, malformed input, cancellation, partial reads, content integrity and owned-temp cleanup | A filename extension proves content validity or successful persistence |
| Cleanup or long-session stability | Post-cleanup owned DOM/listener/controller/timer counts and comparable heap snapshots/traces across cycles | Stable RSS proves no leaks, or rising RSS alone proves one |
| Performance degrades during another test | Comparable workload blocks and attributable measurements; consult statistical interpretation | CPU/memory percentages reveal unloaded latency |
| Broad green coverage but suspicious weak assertions | Inspect critical assertion sensitivity; consider a targeted mutation check only when its cost/risk is justified and authorized | Coverage percentage or mutation score is system correctness |
| Runner, fixture, auth, certificate or endpoint fails | Separate harness/environment/application outcomes and retain independent valid evidence | A setup error is an application defect, or all blocked tests passed |
| Sensitive traces, test data or shared services | Use approved synthetic fixtures and bounded redacted evidence; namespace owned state/ports; cleanup only owned resources | Testing authorizes production writes, external uploads or stopping another task |

Use properties/state machines for meaningful sequences only when the specified rules justify them. Keep reproducible seeds and minimized failing sequences, plus errors and cleanup outcomes. A new test framework, mutation suite, dependency upgrade or full E2E run needs a concrete acceptance gap and applicable authorization; ordinary instruction/documentation updates do not justify them.

## Review and recommendation output

For each material gap, retain its existing ID if any, source/artifact identity, expected versus observed behavior, evidence pointer, affected acceptance and the smallest proposed next check. Distinguish a reproduced defect from a hypothesis, flaky result, external blocker or unrun scenario. Keep mandatory work separate from optional improvement; do not invent IDs or append every row to the report.

If a failure is caused by the test harness, preserve the original result and its cause rather than silently rewriting the expectation. Confirm specification-defined UI text, existing snapshots and implementation intent before proposing a baseline update. Never delete assertions or disable tests merely to obtain green results. Quarantine is an explicit temporary project decision with owner, reason and follow-up, not completed acceptance.

When reviewing an ongoing task, account for the tested code state and later changes. Reuse unaffected evidence; invalidate only the results whose inputs/dependencies changed. Separate functional assertions from statistical workload estimates and performance trends. Detailed statistical assumptions belong in [statistical interpretation](statistical-interpretation.md).

## Primary references

Checked 2026-10-07. Framework-specific API details must match the project's installed version; these links do not require installing the frameworks.

- [Playwright best practices](https://playwright.dev/docs/best-practices): isolation, user-visible behavior, locators, waiting and debugging evidence
- [pytest flaky tests](https://docs.pytest.org/en/stable/explanation/flaky.html): uncontrolled state, order/parallel dependence and flaky-result handling
- [Hypothesis stateful tests](https://hypothesis.readthedocs.io/en/latest/stateful.html): rule-driven operation sequences and invariants
- [Chrome memory diagnosis](https://developer.chrome.com/docs/devtools/memory-problems): distinguish leaks, bloat and repeated garbage collection using process/heap evidence
