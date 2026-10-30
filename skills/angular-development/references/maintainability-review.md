# Bounded maintenance review

Use for an explicitly scoped maintenance audit, not as a mandatory implementation
gate. This helper extends the existing Angular conventions checker. It is not a
replacement for the project's Angular compiler, security review or behavior tests.

## Inputs and execution

Use Python 3.11+, Node and an approved installed TypeScript 4.x-6.x JavaScript API.
The TypeScript 7 native API is not assumed compatible. Supply an installed Angular
compiler ESM entry only when template parsing is needed. Dependency loading executes
those trusted library packages, never the target application; do not supply an
unreviewed repository script as a compiler. No packages are downloaded or installed.

```text
python scripts/check_maintainability.py --root /approved/project --scope src/feature --mode files --file src/feature/view.ts --file src/feature/view.html --depth static --typescript /approved/typescript/lib/typescript.js --angular-compiler /approved/angular/compiler/fesm2022/compiler.mjs --report /approved/reports/review-new.json
python scripts/check_maintainability.py --root /approved/project --scope src/feature --mode diff --staged --unstaged --untracked --depth semantic --dependency src/shared/types.ts --typescript /approved/typescript/lib/typescript.js --profile /approved/profile.json --report /approved/reports/semantic-new.json
```

Run from this Skill directory or use the absolute script path. Reports contain
relative paths, line locations, hashes and bounded facts, not source excerpts,
literal values, diagnostic messages, credentials or raw process errors. Keep
company reports in their approved local environment. This is data minimization,
not authorization to publish paths, hashes or derived findings.

| Dimension | Options and exact boundary |
| --- | --- |
| Scope | `files` requires explicit files within literal `--scope`; `diff` uses literal Git pathspecs and explicit staged/unstaged/untracked selection; `module` walks only the named module and excludes dependency/output directories |
| Content | Current working-tree bytes, including when selection came from the index; not a staged-blob audit |
| Dependencies | Repeat `--dependency` for confirmed TypeScript files within root, read for types but not added to findings scope; no automatic application traversal |
| Static depth | TS parse/AST, optional explicit visibility/formatter profile, optional Angular template parser, manual review matrix |
| Semantic depth | Static checks plus bounded TypeScript compiler diagnostics/symbol types/module graph; only selected files, explicit dependencies and standard TS libraries are readable |
| Runtime depth | Semantic checks plus a pending runtime plan; this command never starts a browser/application, calls an API or imports target code |

`--root` is an explicit read boundary. Escapes through parent paths and file links
are rejected. Directory links are not traversed. Diff errors never fall back to
the entire repository. Missing files and unsupported extensions are enumerated.
Both selected files and explicit dependencies have a 1000-file / 20 MB ceiling.
Output is a new JSON file outside root, opened exclusively; source files are never
overwritten. Inputs are hashed before analysis and read back afterward; changed
inputs invalidate the receipt. Subprocess arguments are lists, not shell strings.

## Project profiles

Profiles are JSON data with `id` and `version`, not scripts or universal style rules:

```json
{
  "id": "confirmed-project-profile",
  "version": "1",
  "explicitPublic": true,
  "format": { "indentSize": 2, "semicolons": "insert" },
  "compilerOptions": { "target": "ES2022", "strict": true, "noPropertyAccessFromIndexSignature": true }
}
```

Omit visibility/format when they are not confirmed. Read the actual compiler
configuration before supplying options; this tool does not discover tsconfig,
follow its includes/extends or execute plugins. The bounded check enables unused
and implicit-any diagnostics for review, forces no emit and disables ambient type
package discovery. Missing module/library evidence prevents semantic coverage PASS.
`public`, `void 0`, member order and business copy are not portable defaults.
Only explicit public and formatter settings are automated here; the other policies
remain with their existing project/Skill owners and appear as manual checks.

## Result contract

Every result has `ruleId`, `status`, `severity`, `confidence`, `scope`, `depth`,
`path`/`line` (null for whole-scope or unavailable locations), `method`, `evidence`,
`sourceVersion`, `impact`, `verification` and `autoFix:false`. Top-level selection,
profile/version/hash, exact input hashes, adapter versions and coverage state bind
the result to the inspected snapshot. Diagnostics deliberately omit source text.

| Status | Meaning |
| --- | --- |
| PASS | Only the named mechanical predicate passed, not business or full audit acceptance |
| FAIL | A parser/compiler error in resolved context or an explicit profile convention failed |
| WARN | Review candidate, not a proven defect, safe deletion or measured performance change |
| MANUAL | Human/source/behavior judgment still required |
| SKIP | Not selected, missing prerequisite or blocked dependent check, with reason |
| ERROR | Input/tool/environment failure; independent file/template checks continue where safe |

Exit `2` means a tool/input error, `1` means a mechanical FAIL, `0` means neither;
WARN/MANUAL/SKIP can coexist with exit 0. Always inspect summary and `complete`.
An empty scope is SKIP, never a successful audit. This version deliberately keeps
`complete:false` while the manual/runtime checks remain. No `--fix` exists.

## Rules and evidence

All rows apply to a compatible Angular/TypeScript review, except explicit profile
style rules. The current implementation is `maintenance 0.1.0`; its recorded
compiler versions are the semantic source for AST/type predicates. Interpret
candidates using the sources below and the actual project version, not the latest
documentation's defaults.

| Rule IDs / purpose | Method and scope | Exceptions, false positives and required evidence |
| --- | --- | --- |
| `TS.SYNTAX`, `TYPE.COVERAGE`, `TYPE.DIAGNOSTIC` | Parse selected TS; semantic depth compiles only allowed context | Missing dependencies are coverage gaps, not application defects; no Angular template type-check claim |
| `IMPORT.DUPLICATE`, `IMPORT.UNUSED_CANDIDATE`, `IMPORT.CYCLE` | AST same-source declarations, compiler unused diagnostics, bounded import/export graph | Unused diagnostics can concern parameters/members, not just imports; preserve side-effect imports, type/value splits and import attributes; type-only cycles do not prove runtime cycles |
| `CHAIN.FORWARD`, `CHAIN.RESPONSIBILITY` | AST single-call method candidate plus manual full call-chain review | Keep validation, event/request ownership, cancellation, errors, receiver binding, public contracts and duplicate checks protecting separate callers; no depth threshold |
| `ORPHAN.CONSUMERS` | Manual reference classification | Methods/exports/fields/getters/outputs/components/directives/pipes require HTML, lifecycle/decorator, dynamic creation, reflection, tests and public API coverage; disabled retained features are not deletion candidates |
| `MEMBER.VISIBILITY`, `MEMBER.ORDER` | Reuse existing checker only with explicit profile; order remains manual | Include constructor parameter properties; retain accessors/overloads, initializer/decorator dependencies and project grouping |
| `FORMAT.EFFECTIVE`, `COMMENT.INTENT` | Reuse formatter, compare final bytes; comments reviewed manually | Ignore no-op edits; preserve necessary reasons and original copy; comment freshness needs actual behavior/spec evidence |
| `NAME.MAPPING` | Manual operation, boolean-owner and API-source tracing | A shared name does not prove the same query or mapping; do not rename from heuristic English preferences |
| `TYPE.EXPLICIT_ANY`, `TYPE.INFERRED_ANY`, `TYPE.ASSERTION`, `TYPE.RECORD`, `TYPE.DOT_CANDIDATE`, `TYPE.DESIGN` | AST nodes and bounded checker symbols/types, then design review | Preserve legitimate `as const`; inferred any can come from missing context; fixed Record keys differ from dynamic dictionaries; dot candidates require declared properties and valid identifier keys, excluding numeric/dynamic/index-only keys; verify narrowing, known model structure, union/enum and branch completeness |
| `HTML.PARSE`, `HTML.ANY`, `HTML.RESPONSIBILITY` | Installed Angular parser and manual template context review | Parse success is not type success; verify ng-template context, reusable component/directive boundaries, repeated conditions, track keys and DOM identity with project compiler and interaction |
| `MODAL.LIFECYCLE`, `FACTORY.EQUIVALENCE`, `FORM.STATE`, `FORM.OWNERSHIP` | API-shaped calls identify review points; compare owners and behavior | Same method names do not establish equal validators/error keys/defaults; preserve fresh controls, disabled value/getRawValue/payload, close/reopen/reset/pristine/readonly and dirty/save/submit/corrected prompt triggers; no generic schema/factory engine |
| `ASYNC.LIFETIME`, `ASYNC.OWNERSHIP` | Subscription/effect/listener-shaped calls plus call-chain review | Resolve actual symbols; automatic framework cleanup or finite streams can be valid; check cancellation/staleness, repeated API calls and loading exits on success/failure/cancel |
| `CSS.CONSUMERS` | Manual style ownership and consumer review | Dynamic classes, Host, overlay mounting and encapsulation invalidate text-only unused CSS conclusions |
| `PERF.TEMPLATE_CALL`, `PERF.RUNTIME` | Angular AST candidates; runtime remains unexecuted | Event handlers and cheap accessors are often appropriate; no call/import/line-count performance claim |
| `SECURITY.SINK`, `SECURITY.OWNER` | Bounded API-shaped candidates routed to existing security review | Names can resolve to unrelated functions; confirm input/source/sink/authorization and exploit conditions, never report a vulnerability from a name match |
| `TOOL.*`, `SCOPE.EMPTY`, `TS.DECLARATION` | Runner, adapter, selection and dependency boundaries | Tool failures and excluded declarations never imply source PASS; no automatic broadening after errors |

## Performance acceptance

Separate candidate impact from measurements. After explicit runtime/data authority,
use existing Playwright/DevTools and the project's build/measurement owner. Record
environment, application/browser/library versions, route/data and permissions,
cold/warm state, sample count, baseline and comparable measurement conditions.
Measure request counts/duplicate queries, template reevaluation, DOM identity and
rendering, subscription/listener retention and bundle dependency/size as relevant.
Retain failures and cleanup owned sessions. This tool neither measures these nor
turns source counts into performance improvement. Runtime authorization does not
automatically authorize login, API writes, destructive tests or data export.

## Existing security owners and gaps

Inventory checked 2026-10-30: installed Codex Security 0.1.32 exposes standard and
diff review, finding validation and fix-verification workflows; its diff owner
already manages source-to-sink analysis, coverage, candidate adjudication and
SARIF/report delivery. Reuse that supported entry when a security audit is requested,
after confirming its data boundary and execution mode. This helper does not launch
it or create a scan/task automatically. Existing public distribution/secret guards
remain with packaging. Company requirement-to-case verification remains with the
private reference/verification owner; no company fixture or source belongs here.

This helper fills selection/report gaps: literal scope, explicit read dependencies,
no shell/target execution, no diagnostic source leakage, exclusive external report,
unchanged-input evidence and distinct failures. It adds candidate routing for trust
bypass, command execution and network calls, not a replacement security engine.
Authentication/authorization, server-side enforcement, secret validity, real data
egress and HTML/command exploitability require the existing security owner and,
where needed, separately authorized dynamic checks. No authentication or permission
changes are made by this tool.

## Sources and compatibility

Checked 2026-10-30, official references (do not send project contents to them):

- [TypeScript Compiler API](https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API): AST, Program and TypeChecker; JS API compatibility boundary is recorded separately from target TS settings
- [Angular template checking](https://angular.dev/tools/cli/template-typecheck): template parsing and template type checking are distinct; inspect the installed project's strictness rather than copying current defaults
- [Angular security](https://angular.dev/best-practices/security): framework protections do not establish application authentication or authorization
- [Existing maintenance responsibility](code-maintainability.md), [style/formatter owner](angular-style.md) and [component behavior](component-behavior.md): apply the selected project/version and source boundaries

Synthetic fixture success verifies this tool only. Keep actual project acceptance,
installed Plugin version, MCP registration/loading and tool invocation separate.
