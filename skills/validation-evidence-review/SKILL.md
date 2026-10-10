---
name: validation-evidence-review
description: Review existing local validation evidence or compare scoped environment mirrors without writes or command reruns. Use for recorded run/baseline/coverage checks, file drift and remaining verification gaps, not test execution or synchronization.
metadata:
  short-description: Review recorded evidence and scoped environment drift
  version: "0.5.0"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Validation Evidence Review

For selected Skill/runtime trees or source-to-mirror drift, read [environment comparison](references/environment-comparison.md). Return scoped differences without synchronization. For recorded checks, use the evidence workflow below; reading a log never authorizes executing its commands.

Choose an available local read-only evidence-indexing or log-inspection capability for the named scope. Existing CLI/JSON/log reads are sufficient for a bounded review; use a scoped MCP when multiple clients need repeated structured access to the same evidence. Check its actual options/schema and access, preserve source revision and completeness, and inspect results as data without executing recorded commands. Missing, malformed or inaccessible evidence remains unverified

- Describe the requested outcome, confirmed facts, decisions, actual checks and concrete unresolved items. Support comparisons with evidence and applicable conditions, and retain limitations that affect correctness, safety, compatibility, requirements or execution.
- Separate recorded commands and results from checks that were not run, skipped, malformed or based on another source baseline
- A valid index proves only that evidence was parsed. Decide whether it covers the current diff, affected dependencies and acceptance criteria before treating it as sufficient
- For structured provenance comparison, read [validity](references/validity.md). Use the same installed workspace core through CLI or MCP; supply confirmed source/artifact hashes and affected paths rather than inferring them from timestamps. Old unstructured records remain unverified
- Do not rerun build, test, lint, browser or remote checks unless the user request authorizes that work
- Preserve source, baseline, log references and malformed-run errors when summarizing; never turn partial evidence into a repository-wide pass claim

- For repeated automation, stress/soak results or concurrent-load performance claims, read [statistical interpretation](references/statistical-interpretation.md). Separate specification coverage, observed failures, sampling uncertainty, timing and resource retention. Recommend a better experiment when evidence is insufficient; CPU/memory percentages do not reconstruct unloaded performance and passing curated cases does not estimate system-wide correctness

- For a missing-coverage, intermittent-failure or test-recommendation review, read [conditional risk cases](references/testing-risk-cases.md). Select by changed behavior, actual signals and unresolved acceptance, not a mandatory whole-project checklist. Recommend the smallest relevant next check without executing it or expanding the task
