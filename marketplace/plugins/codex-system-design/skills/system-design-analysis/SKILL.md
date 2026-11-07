---
name: system-design-analysis
description: Turn a product or system question into an evidence-based design analysis of domain boundaries, data ownership, interfaces, quality requirements and architectural trade-offs. Use for system design, system analysis or an architecture decision, not ordinary implementation with a settled design.
metadata:
  version: "0.4.12"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# System Design and Analysis

Separate the observed system from a proposed design. Start with the requested outcome, actors, existing workflow and authoritative requirements; inspect only the relevant implementation and deployment evidence. Do not infer scale, SLA, consistency, budget or business rules from a product category.

## Find decisions that affect behavior

- Express the important scenarios and invariants, including failure, retry, cancellation and concurrent operations. Mark missing requirements as assumptions or open questions; only block decisions that depend on them.
- Identify owners of authoritative data, derived views and external side effects. Trace reads and writes across module, process and organizational boundaries; frontend state is not proof of durable persistence or authorization.
- For asynchronous workflows, examine idempotency, ordering, retries, duplicates, partial success and recovery. Do not introduce a queue, distributed transaction or event-driven architecture without a concrete need.
- For orders, payments, stock or other irreversible actions, keep business state transitions and reconciliation explicit; never infer a successful transaction from an HTTP acceptance or UI message alone.
- Resolve material quality requirements such as availability, latency, security, privacy, operability and deployment constraints from evidence or explicit assumptions. Distinguish measured demand from estimates.

## Compare options proportionally

Use the current architecture as one candidate. Compare only viable alternatives on the requirements that change the decision, including failure recovery, implementation/migration cost, dependencies and ownership. Prefer a reversible small step when evidence is incomplete; do not default to microservices, a particular cloud or a new framework.

Use a context/data-flow diagram when it clarifies trust or ownership boundaries and a compact table for trade-offs. Keep private endpoints, identities and real customer data out of shareable examples. Existing project decisions retain their authority until explicitly revised.

Choose available diagram, editable-whiteboard or quantitative-analysis capabilities by the required output, editability and data boundary. Use simple text or a local diagram when sufficient, inspect the rendered result when rendering is material, and retain editable source or assumptions for follow-up. Tool choice and successful rendering do not validate architecture or authorize publishing a board.

## Deliver a decision that can be checked

Describe the requested outcome, confirmed facts, decisions, actual checks and concrete unresolved items. Support comparisons with evidence and applicable conditions, and retain limitations that affect correctness, safety, compatibility, requirements or execution.

State the problem and scope, observed facts, assumptions, chosen or proposed option, rejected alternatives with reasons, remaining questions and the smallest useful validation. Use the existing authorized decision record if one exists; do not create another backlog or automatically write to Notion.

Analysis does not authorize implementation, infrastructure changes or purchases. If implementation is authorized, keep the accepted decision and public interfaces explicit and verify the affected failure and recovery paths rather than declaring the design correct from a diagram.
