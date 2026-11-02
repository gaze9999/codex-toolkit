---
name: decisions-evaluation
description: Evaluate authorized text, JSON or image evidence with OpenAI Decisions for a bounded predicate, finite choice or ordered rubric during development. Use when uncertainty can change the next action, not for routine coding or exact checks.
metadata:
  short-description: Bounded development evaluation with Decisions
  version: "0.1.2"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Decisions Evaluation

Retrieve sufficient evidence and resolve exact facts locally first. Select a provider by supported modality, validated task quality, latency, cost and authorized data. Existing Jev remains suitable for its bounded text-ranking/evaluation workflow; no provider is mandatory and failures never silently transfer data elsewhere.

Use the installed `decisions` CLI or `decisions_*` MCP tools. Read [usage](references/usage.md) for request fields, authentication and limits. During ordinary use, missing installation or credentials returns to Main; do not install tools or access Codex login credentials to recover.

Prepare only authorized evidence and a literal atomic question. Include an unknown choice when information may be missing. Exact counts, versions, invariants and permission checks use deterministic checks. Run local validation before a new request shape. Paid calls require the current task's approved transfer scope; `approved` reports that authority rather than creating it. When external evaluation is useful and the transfer is authorized, first construct a minimal generic or synthetic representation that preserves the decision-relevant conditions, relationships and unknowns. Review the complete outgoing question, rubric, candidates and metadata for sensitive or proprietary information and semantic drift; keep source mappings local. Name replacement alone is insufficient. If a safe representation loses decisive meaning, decide locally or request the missing scoped authority. Results about an abstraction do not verify the original implementation.

Preserve raw provider results, refusals, unknowns and failures. Calibrate thresholds on the actual model, language and task. Scores do not decide source authority, correctness, legal/safety/permission/release approval or acceptance. Report purpose, provider, status and effect on Main's next step without repeating evidence or credentials.

For delegation or model/reasoning ambiguity, first establish permission, independent ownership, dependencies, actual model/tool availability, supported effort and Main's ceiling. Compare eligible role/model/reasoning tuples by opaque candidate ID using approved summaries; include Main and unknown when appropriate. Revalidate the chosen ID against current defaults, role overrides and history-mode constraints before dispatch. Main dispatches and accepts; this tool cannot spawn, change Main's settings, exceed model/reasoning limits, expand permissions or authorize recursive delegation.

Offline validation, synthetic transport tests, live API scoring and MCP invocation are separate evidence. No persistent evaluation-content collection is enabled.
