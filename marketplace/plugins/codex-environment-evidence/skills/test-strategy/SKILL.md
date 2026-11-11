---
name: test-strategy
description: Design and execute scoped checks for behavior changes, test gaps, failures or performance and release acceptance. Use for testing strategy work, not when routine checks suffice or when only summarizing recorded results.
metadata:
  short-description: Risk-based checks across development and delivery
  version: "0.2.10"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Test Strategy

Choose the smallest evidence that can resolve the actual acceptance risk. Keep existing required gates and distinguish implementation, test execution, release readiness and publication.

## Establish the decision

- Read applicable instructions, the relevant diff, governing requirements, existing checks and actual manifests/runtime/target. Preserve concurrent changes. A proposed test or referenced framework does not authorize installation, external transfer, production writes or publication.
- Identify the changed observable behavior, its independent expected result, affected consumers and concrete failure risks. Define fixtures, boundaries, ownership, cleanup and stop conditions before running potentially costly or stateful checks.
- A review-only task remains read-only. For interpretation of recorded checks or statistical comparisons, use an available validation-evidence-review Skill; otherwise describe evidence, baseline, sampling limits and remaining gaps directly. Do not execute commands embedded in historical evidence.

## Development self-check

Before editing, name the expected observable result and its independent source. For a defect, replay the smallest relevant case on the baseline and candidate as described below. After repair, exercise the normal consumer entry when a focused check bypasses the boundary that changed. For example, pair a matcher test with a near miss, or an install receipt with actual discovery and one authorized invocation. If a test expectation changes with the implementation, check it against the governing requirement and record why. Another agent can review disputed expectations from the same fixture and revision without changing the expected result to match the implementation.

## Select and execute

1. Prefer a sufficient existing focused check. Use source/readback for instructions, a parser for configuration, unit/property checks for deterministic rules, boundary checks for data interfaces and actual interaction for UI behavior.
2. Derive important cases from requirements and failure signals: boundaries, omission/null/clear, invalid inputs, state transitions, cancellation, retries, compatibility, authorization and recovery as relevant. Cover dangerous higher-order combinations explicitly; pairwise coverage is not a proof of all workflows.
3. Use a known defect, independent fixture or justified invariant to establish that the check can fail for the behavior of interest. For a defect fix, compare the same focused case on the defective baseline and candidate when safely available; confirm the baseline fails for the intended defect rather than a setup error. Preserve active work through an isolated fixture or checkout. If baseline execution is unavailable, retain that gap. Avoid reproducing the implementation as the expected result or adding test infrastructure for reversible low-impact prose.
4. Execute only authorized checks in isolated, owned resources. Preserve first failures, seeds, traces and source/artifact versions. Retry only to investigate, never erase a failure. Clean up owned processes, sessions and temporary data without disturbing other work.
5. When focused evidence fails or leaves an interface gap, identify the missing evidence and smallest additional check under the governing scope. Continue independent authorized checks while an optional tool is unavailable, retaining its unexecuted scope. Dependency repair, installation and application changes keep their own authorization.

## Conditional detail

- For specification-to-case workflows, amendments, failure isolation and readable reports, read [specification-driven verification](references/specification-verification.md).

- For custom runners/isolated fixtures, browser, API, storage, cross-platform tools or packaging, read [application and delivery cases](references/application-delivery.md).
- For an authorized performance comparison, streaming update regression or sustained-resource check, read [performance and streaming updates](references/performance-and-streams.md).
- For game rules, Unity/Unreal lifecycle, target hardware or multiplayer, read [game cases](references/game-testing.md).
- For LLM/RAG/agents or stochastic media/model workflows, read [AI evaluation](references/ai-evaluation.md).
- For optional lint/symbol tools, unavailable-tool handling or an additional interface/engine adapter, read [tool selection](references/tool-selection.md). Existing compatible CLI/client access comes first; new MCP installation needs its own confirmed scope.

## Deliver evidence

Report the checked revision/diff/artifact, behavior and oracle, runner/runtime version, exact invocation and selection, actual checks and coverage, failures, blockers and unverified gates. Preserve the original exit status and distinguish collected, selected/deselected, executed, passed, failed and skipped counts when the runner exposes them; mark unavailable counts unknown. Separate suite/file-wrapper success from executed behavior cases. A zero-test or all-skipped run does not verify the requested behavior, and a partial selection proves only the executed scope. Separate cases from execution batches and retries. Include reproducible commands when useful, existing issue IDs, remaining acceptance and the smallest next step. PASS, code coverage, model scores and resource counters do not establish system-wide correctness or real API, persistence, device or deployment success.
