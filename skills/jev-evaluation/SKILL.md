---
name: jev-evaluation
description: Rank locally retrieved context or compare approved summaries with a finite rubric when semantic ordering remains useful. Use for Jev setup or diagnosis too, not routine coding preflight.
metadata:
  short-description: Optional candidate ranking and typed semantic evaluation
  version: "0.4.13"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Jev Evaluation

Choose the available Jev CLI or MCP route by required capability, shell/client access, repeatability and evidence; neither has a universal priority. Both use the shared Python API client. Python 3.10+ is required; MCP uses the pinned official SDK, while the CLI needs only the standard library.

## Choose useful work

- Retrieve locally first and apply deterministic filters such as source identity/version, tracked status and confirmed dependencies. Consider Jev only when reading order across optional document/code/evidence excerpts still needs semantic comparison, or approved summaries need an atomic finite choice/ordered rubric. Complete small, already-settled or rule-determined work directly; no per-turn preflight or fixed candidate-count threshold.
- For work-item or reusable-tool candidates, compare a stated question against explicit criteria, not the entire planning problem. Main determines readiness, dependencies and final priority. See [usage scenarios](references/usage.md#when-to-use-jev) when the boundary is unclear.
- Main retains requirements, architecture, delegation, implementation and acceptance. Jev signals do not establish API compatibility, permissions, persistence, correctness or test coverage.
- Keep mandatory instructions, governing specifications, acceptance criteria, confirmed decisions and unresolved blockers in Main's context. Ranking changes reading order, not source authority or required verification.
- Supply only approved, necessary excerpts or sanitized summaries. Setup authorization and installing this Skill do not authorize uploading company source, private specifications, logs or customer data. A decision needing unapproved proprietary context stays with Main.

## Run without expanding context

- For first installation, credentials, Mac/Windows commands or API diagnosis, read [usage.md](references/usage.md). Otherwise use the helper without reading its implementation or repeating setup.
- For relevance, use CLI `rank --input <file>` or MCP `jev_rank` with `query` and `candidates` containing opaque `id` and approved `text`; mark mandatory entries `required: true`. Required entries need no text and are never sent to Jev; every candidate ID remains in the result.
- Keep source path/line or document-page pointers locally by candidate ID; queries and rubrics must also be approved for external transfer. Send bounded excerpts, not repository dumps, conversation history or full instructions. Batch independent questions when useful, then read relevant Markdown extractions first; return to necessary originals/screenshots only for missing, unclear, stale or conflicting content, visual evidence or an explicit source check. Do not re-extract documents merely for ranking.
- For a finite choice, boolean probability or ordered rubric, use CLI `evaluate --input <file>` or MCP `jev_evaluate`; read only its schema section in the usage reference when needed. Do not generate code, explanations or history summaries with Jev. Keep each question literal and atomic, with aligned criteria and an explicit unknown option when information may be absent. Use code for counts, arithmetic, date/version comparisons and invariant checks; see [question design](references/usage.md#question-design-and-call-cost) for unfamiliar rubrics.
- Verify the selected route's actual help/schema, credential access and data scope. If unavailable, use an authorized compatible alternative or return to Main. Do not install dependencies, reconfigure the client or repeat credential setup during ordinary coding.
- Consume the compact result: candidate IDs/probabilities or typed answers, resolved model, usage, latency and status. After actual use, briefly state the purpose, tool, returned status and how Main used the signal or fell back; include the resolved model only when returned. Do not echo inputs, raw HTTP errors or credentials, or create persistent logs unless requested. Installation, local status and offline protocol checks do not prove task ranking/evaluation occurred; explain non-use only when asked or material to a requested evaluation.
- Noul probability is not confidence. Choice/Score include provider confidence; calibrate any action threshold against representative domain and language examples. Sorting is advisory and never automatically discards low-ranked or uncertain sources.
- `status: fallback`, malformed results, missing credentials or uncertain judgments return to the existing Main workflow. Keep unknowns explicit; do not interpret failed evaluation as low risk or automatically create tasks, reviewers or retries with another model.

## Maintain one source

Edit the version-controlled Skill, validate changed behavior, then synchronize only its managed installed copy. The wheel uses the same scripts under `codex_jev_mcp`; see [usage](references/usage.md#opt-in-local-monitoring) for requested metadata monitoring. Recording is opt-in and never changes ordinary Jev use decisions. Keep credentials outside repositories and Skill archives. Installation readback does not prove an already-open client refreshed its Skill list; no performance or context savings are established without measurement.
