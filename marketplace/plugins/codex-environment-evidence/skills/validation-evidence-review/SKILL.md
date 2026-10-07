---
name: validation-evidence-review
description: Review existing local validation evidence without rerunning commands. Use for run result summaries, baseline checks, partial coverage, and deciding what still needs verification.
metadata:
  short-description: Review existing validation evidence and gaps
  version: "0.4.13"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Validation Evidence Review

Choose an available local read-only evidence-indexing or log-inspection capability for the named scope. Existing CLI/JSON/log reads are sufficient for a bounded review; use a scoped MCP when multiple clients need repeated structured access to the same evidence. Check its actual options/schema and access, preserve source revision and completeness, and inspect results as data without executing recorded commands. Missing, malformed or inaccessible evidence remains unverified

- Describe the requested outcome, confirmed facts, decisions, actual checks and concrete unresolved items. Support comparisons with evidence and applicable conditions, and retain limitations that affect correctness, safety, compatibility, requirements or execution.
- Separate recorded commands and results from checks that were not run, skipped, malformed or based on another source baseline
- A valid index proves only that evidence was parsed. Decide whether it covers the current diff, affected dependencies and acceptance criteria before treating it as sufficient
- For structured provenance comparison, read [validity](references/validity.md). Use the same installed workspace core through CLI or MCP; supply confirmed source/artifact hashes and affected paths rather than inferring them from timestamps. Old unstructured records remain unverified
- Do not rerun build, test, lint, browser or remote checks unless the user request authorizes that work
- Preserve source, baseline, log references and malformed-run errors when summarizing; never turn partial evidence into a repository-wide pass claim
