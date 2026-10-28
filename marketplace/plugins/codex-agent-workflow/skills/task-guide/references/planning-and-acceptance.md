# Planning and acceptance

Use for requested reusable planning or acceptance artifacts. Recover the existing work identity, requirements, decisions, authority, source versions and acceptance before choosing a format. Preserve project-owned records; a template does not require a new file or a new tracker. Read only the selected assets and specialist guidance needed for the task.

## Select the artifact

| Artifact | Decision it supports | Maintained content |
| --- | --- | --- |
| [Goal](../assets/goal.md) | What result must be achieved and accepted? | Outcome, scope, authority, sources, required results, optional meaningful stages, completion conditions |
| [Plan](../assets/plan.md) | How will authorized work reach that result? | Ordered actions, dependencies, owners, inputs/outputs, checkpoints and evidence-based recovery |
| [Sketch](../assets/sketch.md) | Which layout, flow or relationship needs clarification? | Purpose, known constraints, visual artifact, assumptions, alternatives and decisions needing confirmation |
| [Review and tests](../assets/review-and-tests.md) | What could fail, what should be tested and what proves the result? | Exact baseline/candidate, requirements, risk, independent expected results, selected checks and findings |

Goal stages may include necessary ordered steps when sequence affects acceptance. Keep detailed commands and changing execution choices in Plan. A completed Plan step is not a passed Goal condition. Reuse established IDs and acceptance references; ordinal step numbers are not newly issued work IDs. Small work may use concise Markdown sections in the existing conversation instead of every template.

Use concise English for AI-facing artifacts unless requested otherwise. Human-facing output follows the user's language. Preserve source literals. Replace placeholders with verified facts, omit irrelevant sections, and leave material unknowns explicit. Never invent commands, source revisions, tool availability or passed checks to fill a table.

## Route existing capabilities

| Need | Existing owner to resolve | Boundary |
| --- | --- | --- |
| A copyable coding/handoff prompt | Available coding-prompt workflow | Prompt creation only; model advice outside the uninterrupted prompt |
| New task, fork or subagent choice | Available task-routing workflow and current host tools | Requires applicable authorization; templates do not activate roles |
| Specification context | Available context-brief workflow | Preserve governing sources and exact required literals |
| UI layout or interaction sketch | Available UI/UX workflow and supported rendering/image tools | Design choices stay distinct from confirmed requirements; inspect actual rendering when required |
| Scoped code review | Project review instructions and an available reviewer/tool | Main retains acceptance; no mandatory independent agent or auto-repair |
| Static/domain/security scan | The verified specialist Plugin, Skill, CLI or MCP selected for that project | Check actual execution capability, version, scope, data destination and authority first |
| Test design or execution | Available test-strategy workflow and existing project runners | Use independent oracles, safe fixtures and owned resources; retain required gates |
| Existing evidence review | Available validation-evidence-review workflow | Read-only interpretation does not rerun checks or synchronize files |

This table selects responsibility, not an install list or fixed tool bundle. A reference-only MCP can supply rules, but cannot be described as a scanner. Do not infer a tool from a Plugin name, invoke all security scans automatically, send private code to external tools, or claim a specialist ran because its instructions were read. If a specialist is absent, use an authorized compatible method or retain the specific gap; do not install implicitly.

For each selected specialist record the objective, exact source/baseline, included and excluded paths, allowed operations/data, current tool/command, expected output, evidence location and remaining gaps. Main maps returned findings to requirements, validates scope and evidence, and decides accepted defect, question, false positive or pending verification. Fixing findings requires the effective implementation authority. Recheck affected findings after the candidate changes.

## Sketch and review gates

Use Mermaid for supported small flow/architecture diagrams, a low-fidelity wireframe for layout questions, or an available image/interactive tool when the result needs it. Link the artifact to the relevant Goal condition and Plan decision; do not duplicate the same diagram into every record. Label assumptions and unresolved interactions. A rough sketch is not pixel-level, accessibility, business or runtime acceptance. Do not invent product copy or data in specification-driven work.

Review the exact revision/diff or immutable artifact against governing requirements. Derive tests from observable behavior, boundaries, failure paths and affected interfaces rather than repeating implementation logic. Define what to test, why, independent expected result, fixture/environment, verified runner and evidence before execution. Keep proposed, executed, passed, failed, skipped, blocked and unverified states distinct. Zero findings or a passing build does not prove full correctness.

## Goal lifecycle and trial

Create an executable Goal only when explicitly requested and supported. A Markdown planning request alone does not create one. Do not infer a token budget. Reuse an unfinished Goal. When the tool cannot edit its objective, amend the selected existing goal record and reference the same identity; do not mark unfinished work complete to recreate it. Pause/completion/blocking follow the actual tool and user instructions.

Update only material decisions, scope, dependencies or acceptance. Inspect receipts/destinations before retrying unknown side effects. Failed approaches require new evidence or a revised hypothesis; preserve independent completed work. An unavailable environment blocks dependent acceptance, not every step. Handoffs retain unresolved owner, next action and evidence.

Evaluate template changes using explicit requests, realistic implicit requests and adjacent negative cases. Separate manual design review from actual model/client invocation. Use observed workflow evidence before claiming improved clarity, speed, quality or cost; no fixed savings, agent count or universal workflow sequence follows from having templates.
