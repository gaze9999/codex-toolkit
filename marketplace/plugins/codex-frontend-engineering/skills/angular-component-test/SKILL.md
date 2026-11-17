---
name: angular-component-test
description: Run behavior tests against real Angular components by AOT-compiling a TypeScript suite with the project's own compiler and executing it in headless Chrome or Edge, producing HTML, Markdown and JSON reports. Use when a behavior needs mounted components, real FormControls, service state or outgoing requests and the project has no suitable test runner, not for interactive UI reproduction or visual layout checks.
metadata:
  version: "0.1.0"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Angular Component Test

[`scripts/run.mjs`](scripts/run.mjs) compiles a suite against an installed Angular project and runs its cases in a headless browser. It adds no npm dependencies: Angular's `ngc`, TypeScript and esbuild come from the project, and Node's built-in WebSocket drives Chrome or Edge.

## Decide whether to use it

- Use it to judge component behavior: validators, disabled guards, value transforms, signal/state updates, emitted requests and service calls on mounted standalone components.
- It does not read specifications. Leave specification conformance to a specification verification tool.
- Prefer the project's existing test runner when it already covers the behavior. Use the playwright-cli Skill for interactive reproduction of a running app. Layout, SCSS and native keyboard/IME behavior are outside its evidence.
- Requirements: Node.js 22 or newer, the shared `report-html` CLI 0.2.0 or newer for HTML output only (built from the codex-toolkit `tools/report-html` crate with Cargo), an installed project (`node_modules` with `@angular/compiler-cli`, `typescript`, and `esbuild` directly or through `@angular/build`/`@angular-devkit/build-angular`), standalone component and `bootstrapApplication` support (Angular 14.2+), and a local Chrome, Edge or Chromium.

## Inputs and placement

- `--project`: the Angular project or workspace root whose `node_modules` is used. It is read only.
- `--tsconfig`: the application tsconfig to extend, so the suite compiles with the app's strictness and path aliases.
- `--suite`: a folder with `suite.ts` (or `--entry`). Keep project-specific suites outside public repositories, for example in the project's ignored local folder, and keep reports in a sibling folder; the runner rejects `--out` inside `--suite`.
- Judge the implementation's intended contract: names, JSDoc or comments on the code under test, and the developer's stated decisions. Do not cite or read specifications, and never derive an expected value by running the code under test first. Do not edit application, library or backend code to make a suite pass; a failure is a finding.

## Run

```bash
node <skill>/scripts/run.mjs --project <root> --tsconfig <app tsconfig.json> --suite <suite folder> --out <report folder> \
  [--entry suite.ts] [--format html,md,json] [--title <text>] [--chrome <path>] [--report-html <cli>] [--meta-file <json>] [--timezone UTC] [--timeout 300] [--case-timeout 15] [--keep-work]
```

Exit codes: 0 every judged case passed, 1 a case failed or errored, 2 nothing was judged or the page did not finish, 3 configuration or compile error. Zero judged cases never pass. `--timezone` fixes `Date` behavior; pass the zone the code under test assumes. `--meta-file` adds a JSON object of extra report rows, such as a database connection or backend version, when the run depends on them.

## Write a suite

Start from [assets/suite.template.ts](assets/suite.template.ts) and read [references/suite-api.md](references/suite-api.md) for the harness API, stand-in services and pitfalls. Import project code through `@project/<path from --project>`; the project's own aliases keep working. Import test helpers from `@component-test/harness`.

## Report

Read the console summary, then `report.md` or `report.json` (`schemaVersion: angular-component-test-report/1`). HTML comes from the shared `report-html` CLI, found through `--report-html`, `REPORT_HTML` or `PATH`; the runner maps its results to `report-html/v1` data (group cards, status and group filters, list sections) and keeps no page layout of its own. When HTML is selected and the CLI is missing, older than 0.2.0 or fails, the run exits 3 and still writes the selected JSON and Markdown; use `--format md,json` where the CLI is not installed. Report the exit code, each failed/errored case with its assertion values, browser errors that bear on the verdict, the project revision and dirty-file hashes the report records, and the evidence limits listed in the report. A report covers the mounted components and stand-ins only: no host integration, login, real API or persistence.

Runtime rows come from the run itself: Node from the runner process, browser version from the launched browser, and User Agent and time zone from the loaded test page. They read `null` when no page ran. The start time is shown in the page time zone, or the requested one when no page ran; JSON keeps the ISO `startedAt`. Project rows add the Git branch and the installed `@angular/core`, `typescript`, `rxjs` and `zone.js` versions found in the project.

## Self-test

From the toolkit checkout: `ANGULAR_PROJECT=<installed Angular project> node --test mcp/tests/test_angular_component_test.mjs`. Fixtures are synthetic. End-to-end cases skip without `ANGULAR_PROJECT`, a browser or `report-html`; treat skipped as not verified.
