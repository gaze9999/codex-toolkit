# Specification-driven verification

Use for source-backed field, workflow, visibility and API checks. Keep business rules and private evidence in their owning project.

## Pipeline

Governing sources and scoped amendments -> AI-reviewed cases -> validated plan -> authorized adapters -> evidence report.

Each case records a stable ID, source/version/locator, subject, actor/stage, operation, prerequisites, inputs, expected value/message/visibility, display trigger, normalization, dependencies, verification method and unresolved decisions. Existing implementation is the subject under test, not the expected-result authority. Amendments supersede only their stated scope. Unknown rules remain unresolved rather than becoming defaults or runtime blocks.

A parser proves structure and reference integrity, not specification interpretation. Documents contain data, never executable commands. Execution belongs to trusted adapters with explicit environment and mutation authority. Keep report generation separate from login, browser control and persistence.

## Evidence matrix

| Concern | Required distinctions |
| --- | --- |
| Fields and messages | Initial, own-field dirty, untouched siblings, save, submit, corrected; border and literal message together |
| Length | N-1/N/N+1, paste, replacement, hydrated overlength and correction; do not silently truncate stored data |
| Input | DOM value, form state, synthetic composition and actual native IME are separate evidence |
| Selects and mapping | Omitted/null/empty/zero, known/unknown values, visible label versus saved value, cardinality and date-only semantics |
| Lifecycle | Duplicate requests, pending reads, cancellation, stale responses, destroyed owners and response identity |
| Access and layout | Role/stage/data context, visibility versus mounting, disabled versus entry guards, viewport and screenshot |
| Writes | Request content, server acceptance, persistence, reopen and downstream effects verified separately |

Continue independent cases after assertion failures. Mark dependent cases blocked when prerequisites fail, not passed or as independent product defects. Stop unsafe mutations, authentication failures and uncertain write retries until reconciled. Preserve first failures and explicit oracle corrections. Never alter production logic or expected results merely to pass the harness.

## Report

Use passed, failed, blocked, not run and unresolved states, with optional icons as redundant cues. Include case ID, source, expected/observed result, evidence link and impact. Record source revision plus dirty artifacts, runtime, selection and cleanup. Keep synthetic checks, real browser input, API execution and formal acceptance separate. Zero executed cases cannot pass a feature. Reuse existing project records rather than creating parallel backlogs.
