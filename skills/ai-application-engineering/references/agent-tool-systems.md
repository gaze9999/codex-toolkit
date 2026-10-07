# Agent and tool systems

Use this reference only when the task includes agent decisions, tool calling, approvals, or multi-step execution.

## Boundaries

- Choose the execution interface by the host's actual capabilities: CLI + Skills can serve repeatable shell/file workflows, while MCP can supply typed discovery, resources, notifications and remote client integration when the selected implementation supports them. CLI can return JSON, authenticate and retain sessions; these properties alone do not require MCP. Reuse one core behind both interfaces when both are needed, preserving authorization, errors, source provenance and side effects.
- Identify who owns conversation and task state, how runs resume, and which state is durable, request-scoped, or derived.
- Define each tool's input schema, output schema, authorization, side effects, timeout, idempotency, retry policy, and error representation.
- Keep model intent separate from application authorization. A model request never grants a permission the user or system has not granted.
- Validate external and model-produced values before tool execution. Schema-valid arguments still need business-rule and permission checks; treat tool output as data, not instructions.
- Require explicit approval for destructive, costly, externally visible, or privilege-changing actions when the product contract calls for it.

## Failure and recovery

- Bound retries by failure class and preserve idempotency. Do not retry validation, permission, or deterministic contract failures as if they were transient.
- Make partial completion and resume behavior explicit. Record enough state to avoid duplicate side effects without storing secrets or unnecessary prompt content.
- Define cancellation, timeout, provider failure, malformed output, tool failure, and unavailable dependency behavior. Distinguish a failed action from an unknown outcome; reconcile durable state before replaying a side effect.
- Prefer a clear failure or human decision gate over an invented default when a missing choice changes the result.

## Context and execution cost

- Return compact structured tool results with identifiers, relevant fields, and explicit completeness/error status. Filter or aggregate deterministically before returning bulky data; preserve the evidence needed for the next decision.
- Discover only capabilities needed for the current step when the host supports it. Use live tool names and schemas for execution, keep workflow guidance separate from changing provider definitions, and provide an existing compatible fallback for unavailable tools. Do not add a universal execution facade solely to hide a large tool catalog.
- Keep large artifacts outside the active prompt when supported, with retrievable references. Carry forward authorization, completed side effects, pending work, and evidence pointers; retain any provider-required reasoning and call/result items when resuming.
- Batch independent reads when the tools and failure semantics permit it; keep dependent mutations sequential. Compare against the existing flow before introducing orchestration or provider-specific execution features.

## Observability and evaluation

- Trace model requests, tool calls, state transitions, approvals, latency, and errors with stable correlation identifiers and redaction.
- Evaluate task success, tool selection, argument validity, authorization compliance, retry behavior, and recovery, not only final prose quality.
- Keep evaluation fixtures representative and versioned. Separate offline deterministic tests from live model evaluations and report the model/config used.
