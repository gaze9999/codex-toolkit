# Decisions operation

Read for a real invocation or authorized setup. Runtime package: `codex-decisions`, source `python-tools/packages/decisions`, or Plugin `resources/decisions`. Install the selected package with the `mcp` extra only when needed and authorized. The packaged README owns complete CLI/setup details.

`decisions status` is local credential-presence inspection. `decisions validate --input request.json` returns hash/size without network. `decisions evaluate --input request.json --approved` makes at most one POST to `https://api.openai.com/v1/decisions`. `decisions-mcp --config settings.json` exposes status, validate and evaluate with the same core. No retries, provider fallback or endpoint override.

The optional JSON config accepts only `credential_env`, `model`, `timeout_seconds`. Default credential source is `OPENAI_API_KEY`; never put its value in config. A deliberately selected `OPENAI_ACCESS_TOKEN` may carry an externally managed Platform workload-identity token; this package neither provisions nor refreshes it. No documented personal ChatGPT account-binding flow is used. Missing credentials remain a setup action for the user when they choose manual setup.

```json
{
  "input": "Two modules have separate owners and independent acceptance checks.",
  "questions": [{
    "type": "choice",
    "name": "execution_route",
    "instructions": "Compare only these already-authorized execution routes for coordination and verification burden. Choose unknown if evidence is insufficient.",
    "choices": [
      {"value": "main", "description": "Main completes the coupled work"},
      {"value": "bounded_worker", "description": "A worker completes one independent module and returns evidence"},
      {"value": "unknown"}
    ]
  }]
}
```

Each question needs a unique nonempty name. Types: predicate, choice (2–255 typed string/boolean options), score (2–10 labeled levels). Score is the probability-weighted level index, not a correctness percentage. Model support is currently explicitly `gpt-6-luna`.

For model/reasoning selection, prepare eligible tuples from the actual host catalog before evaluation. Keep exact dispatch parameters locally by candidate ID; attach only approved descriptions of capability, supported effort, task uncertainty, acceptance cost and constraints. Choices can represent complete tuples rather than selecting role, model and effort independently, which could produce an invalid combination. Include an unknown option and Main when appropriate. The returned ID selects a recommendation, not an executable tool call; Main checks the mapping is still current and dispatches only within existing authority. Do not use the evaluator's own model as a worker default or reuse scores across providers without calibration.

Input accepts nonempty text or up to 64 user/developer/system messages. User content and question instructions support input_text, input_json and input_image. Developer/system messages support text only. Images use HTTPS or PNG/JPEG/WebP base64 data URLs; local paths and file IDs are rejected. No tool history or explicit cache options in this adapter version. Requests are bounded to 2 MiB, response to 2 MiB, text segment to 65536 characters. JSON evidence follows 256 KiB / 32 levels / 10000 values limits. Timeout is 1–60 seconds, default 20.

MCP `decisions_evaluate(request, approved=false)` requires an actual boolean. Never set true merely because a tool asks for it. CLI exit 0 includes refusals as a completed API operation, so always inspect status; refusal is never successful acceptance. `needs_credentials`, `approval_required`, `invalid_input`, `invalid_response`, `http_error` and `transport_error` retain distinct meanings.

Sources checked 2026-11-01: [Decisions](https://developers.openai.com/api/docs/guides/decisions), [API schema](https://developers.openai.com/api/reference/resources/decisions/methods/create), [authentication](https://developers.openai.com/api/reference/overview#authentication), [workload identity](https://developers.openai.com/api/docs/guides/workload-identity-federation). Recheck price/model/access before live adoption; Codex subscription is not proof of API credit.
