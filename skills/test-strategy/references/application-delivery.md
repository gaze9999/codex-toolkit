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

For retention or performance, capture a comparable baseline and workload, warm/cold states, wall time and attributable resources. Multiple tools or services running concurrently are nuisance factors, not a formula for removing load. Match chart units, sorting, sampling and aggregation to raw fixtures. An aggregate metric cannot prove every underlying record.

For collection/streaming changes, burst handling or long-running resource checks, use [performance and streaming updates](performance-and-streams.md) to select layer-specific measurements, bounded diagnostics and recovery cases.

For recorded intermittent failures and broader coverage gaps, an available validation-evidence-review Skill supplies conditional risk cases and statistical interpretation. Without it, keep claims descriptive unless the sampling unit, independence, estimator and uncertainty are established. Do not turn isolated fixtures into production reliability percentages.

Sources: [Playwright practices](https://playwright.dev/docs/best-practices), [pytest flaky tests](https://docs.pytest.org/en/stable/explanation/flaky.html), [Chrome memory problems](https://developer.chrome.com/docs/devtools/memory-problems). Recheck exact installed versions when using their commands or APIs.
