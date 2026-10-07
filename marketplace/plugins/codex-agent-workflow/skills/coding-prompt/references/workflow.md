# Coding Prompt Workflow

Create a minimal handoff-ready prompt when the requested deliverable is the prompt itself. Do not execute the generated prompt. User instructions override these defaults.

## Activation

- Use only when the user explicitly asks for a coding-agent prompt, delegation prompt, portable handoff, or a model recommendation packaged with that prompt
- For investigation, review, diagnosis, implementation, or fixes, perform the requested work instead of returning a prompt

## Prompt content

- Describe the requested outcome, confirmed facts, decisions, actual checks and concrete unresolved items. Support comparisons with evidence and applicable conditions, and retain limitations that affect correctness, safety, compatibility, requirements or execution.
- Understand the purpose, use case and desired outcome before selecting context. Include only task-relevant scope, feasibility, dependencies, confirmed requirements, source pointers, preservation/prohibition boundaries and observable acceptance. These are decision dimensions, not a fixed form; infer supported details from available evidence and leave material unknowns explicit.
- Preserve the requested read-only or implementation boundary. Carry Git, installation and release authority only when the user granted it; examples and suggestions do not grant additional actions.
- Keep the effective outcome and scope stable. Carry a necessary expansion only when supported by a dependency, acceptance gap or demonstrated risk and covered by existing authority; identify its reason, affected slice and checks. Keep optional recommendations and expansions requiring a decision separate from authorized work.
- Define acceptance with observable behavior or artifacts. Adapt reporting to the task while retaining necessary acceptance information, requirement status and evidence. Keep issues traceable to sources/artifacts and checked state, with impact and next action; carry existing IDs when available. Avoid generic long templates and unrelated test suites.
- Carry a task-specific recommendation requirement only when useful. Recommendations need evidence, applicability and a concrete next step, with required work kept separate from optional improvements; do not grant extra implementation authority.
- Prefer positive gates that state what to implement, preserve, verify, or deliver. Use negative wording only for files, modules, behaviors, external systems, or actions that must not be touched
- Mention a document as required reading only when the task actually depends on it. Do not add broad repository, specification, history, or instruction-reading checklists
- For specification-based prompts, locate an existing Markdown extraction using the task and available source/version metadata or pointers, without requiring fixed filenames, same-stem names or a fixed folder; point first to its relevant sections. Make screenshot or original-source lookup conditional on needed visual evidence, missing/unclear/stale extraction, conflicting evidence, or an explicit original-source check; do not make rereading PDF/XLSX a routine prerequisite. If no usable extraction exists, point to the relevant original sections without requiring unrequested extraction work
- Keep original specifications and confirmed decisions authoritative, retain source/version and page/sheet pointers where available, and distinguish extraction-based evidence from a verified original. State only task-specific fallback conditions; do not copy a generic source-reading checklist into every prompt
- Omit routine repository discovery, Git operations, generic coding/style/safety rules, standard verification checklists, and reminders to follow project instructions. The destination agent and project instruction layers provide them
- Keep task-specific exceptions, exact contract values or messages, required compatibility boundaries, known concurrent-work constraints, and explicit stop conditions when they materially affect execution
- For refactor prompts, carry forward explicit user decisions about equivalent syntax, inferred return types and explicit void/public annotations, responsibility-based variable/member ordering, helper depth/readability, type-file cohesion and state ownership only when they change this task. Do not turn them into blanket extraction, inlining or migration requirements; keep review candidates distinct from authorized implementation
- Preserve the requested authority boundary. Do not turn a review, diagnosis, or plan into implementation, or add external actions the user did not authorize
- Do not invent paths, APIs, versions, commands, mappings, requirements, or completed results. Keep unresolved decisions explicit and block only dependent work
- Consolidate repetition and omit background or rationale that does not change an implementation decision

## Execution context

- Write for the environment where the prompt will run, not where it is created
- For a known project, identify only the target area and task-specific sources needed to act. Do not copy project governance into the prompt
- For an unknown or non-project destination, provide the minimum context needed to stand alone without assuming access to this chat or local files
- Include ownership, batching, delegation, or handoff mechanics only when the task requires them
- For reusable prompt patterns, an unfamiliar handoff shape or requested expected-delivery/report illustrations, read [prompt-patterns.md](../references/prompt-patterns.md). Use only the matching pattern; ordinary prompt generation does not require reading it. Retain current authorization and pending acceptance when carrying work to another owner

## Model recommendation

- Complete the prompt first, then recommend exactly one model and supported reasoning level for the resulting task
- Preserve an explicit user selection. Otherwise base the choice on task uncertainty, interacting logic, risk, context, coordination, and verification burden
- Prefer an efficient supported model for an explicitly bounded task with a known approach. Choose a stronger reasoner when the task still requires deciding the approach, root cause, or architecture; do not use progressively higher reasoning levels to retry the same unresolved problem
- Verify current model availability when a concrete model name is required. If it cannot be verified, give concise selection criteria and mark the concrete choice unresolved
- Keep the recommendation outside the copyable prompt. A recommendation does not switch models or change project routing

## Output

- Use the language requested by the user or target project. Otherwise use concise Traditional Chinese for Chinese context, or concise English for English context
- Return the complete prompt as one uninterrupted Markdown `text` fenced code block so the app can show its code-block copy control on mobile, including for long prompts. Do not split the prompt or wrap it in a writing block, quote, list, or table. Use short sentences or compact bullets, omit empty sections, and add headings only when they improve comprehension
- Put only task instructions inside the block. Keep the model and reasoning recommendation immediately after it
- Outside the prompt, include the model recommendation, necessary availability/unresolved-requirement notes and any explicitly requested expected-delivery explanation or report illustration. Separate illustrations with Markdown headings, use placeholders for unobserved results, and keep them distinct from actual execution evidence
- Never execute the generated prompt as part of this workflow
