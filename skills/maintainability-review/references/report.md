# Review report

State the scan root, entry points, selected checks and thresholds, and any partial or unresolved coverage. Separate tool candidates from findings verified against source and consumers.

| Status | Location | Evidence and impact | Proposed change or decision |
| --- | --- | --- | --- |
| Finding | File, line, symbol and caller | Verified condition, affected behavior and scope | Smallest reviewable diff and required check |
| Keep | Covered file or declaration | Applicable retention or meaningful behavior | Preserve the scope and keep private reasons in their registry |
| Needs decision | File, line and missing evidence | Dynamic reference, external caller, distinct responsibility, or unresolved specification | State the source or decision needed |

A high score with clear branching, stable behavior and appropriate verification can stay in Keep. Show why the branches belong together. A low score can still conceal a brittle boundary or unknown consumer.

For independently reviewable candidates, show the affected hunks, patch paths, overlap or application order, and the observed verification results. Keep functional acceptance and patch applicability separate.
