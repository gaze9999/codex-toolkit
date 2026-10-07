---
name: agent-governance
description: Create, audit, or simplify project AGENTS.md layers and Codex subagent roles. Use for agent-governance work, including a new project setup, not ordinary implementation or general code review.
metadata:
  short-description: Agent governance, role boundaries, and instruction minimization
  version: "0.4.17"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Agent Governance

Keep the smallest instruction set that preserves authorization, contracts, project knowledge, and completion criteria. Prefer removing, merging, or relocating rules over adding them.

## Scope and evidence

- Treat an audit or recommendation as read-only. Edit only when requested, normally within `AGENTS.md`, role configuration, and directly related governance documents; do not expand into application code or external actions.
- When edits are requested, complete and verify them. Deliver only a prompt, plan, review, report, or handoff when the user explicitly requests that artifact.
- Read applicable instruction layers, role files, live references, Git status, and relevant diffs before editing. Preserve concurrent work and inspect ignored governance files directly.
- Shape task intake around the intended outcome, authorization, feasibility, dependencies and acceptance. These dimensions are illustrative; add or replace them for the actual situation. Select relevant sources, evidence, checks and reporting without a fixed questionnaire, exhaustive reading or a mandatory preflight ritual.
- Consult current official OpenAI documentation when changing discovery, configuration, model, reasoning, or subagent behavior. Label human reports as anecdotal and project observations as local evidence.

## Start a new project setup

- Read user-provided files or uploads and inspect the target repository before choosing an instruction structure. Do not require this repository or a fixed source path to be available.
- For an authorized new setup, read [project-starter/README.md](assets/project-starter/README.md) and select only relevant templates for the confirmed project type and tool support. Fill verified facts, remove placeholders, and keep the always-loaded root and nested files brief.
- Start with built-in agents; add custom roles only for a durable difference in ownership, permissions, tools, or expected output. Keep Model and reasoning choices unset until the target environment supports and needs a specific override.
- Put task routing detail in a conditional guide when needed. Do not turn templates into standing instructions for every turn or treat a template as authorization to create tasks or delegate.

## Put each rule at the narrowest durable layer

| Layer | Keep here |
|---|---|
| Global or user | Stable cross-project preferences, safety boundaries, execution and evidence principles |
| Repository root | Cross-module architecture and contracts, shared safety, generic ownership, common verification |
| Nested repository | Directory-specific runtime, commands, conventions, public interfaces, and focused checks |
| Role | Only behavior or restrictions that differ for that role |
| Task guide or Skill reference | Procedures needed only for a specific task type |
| Current task | Goal, authorization, progress, exceptions, concurrency, blockers, stop condition |

- Judge where guidance will execute, not where it is authored. Do not copy project rules into portable guidance merely because the file is being edited outside that project.
- Use concise Taiwan Traditional Chinese when creating or revising global/general agent guidance. Use concise English for subagent instructions, project root/nested AGENTS.md, project agent guides, and Skill instructions, internal references and usage guides, unless explicitly overridden. Classify templates by their intended instruction scope even inside a Skill; preserve identifiers, source quotations, parser vocabulary and intentionally localized output examples. User-facing replies and documents follow the user/project language, independently of instruction language.
- Treat paths, installed tools, versions, model availability, and environment reachability as facts to resolve at runtime unless they are verified project contracts.
- Linked references should have clear loading triggers. Do not require unconditional reading of entire documentation folders.
- Keep capability-selection criteria and data-transfer boundaries in the applicable global/project layer. General roles and workflow Skills select from actually available tools by the needed outcome and live schema, not a fixed provider or a copied tool catalog. Preserve exact commands and restrictions in tool-specific Skills/setup, and use an available development-tool-setup Skill only for needed installation or diagnosis. Role configuration inherits the parent capabilities unless a verified narrower scope is required, and source updates do not authorize runtime installation or live configuration changes.

## Simplify without losing decisions

- Describe the requested outcome, confirmed facts, decisions, actual checks and concrete unresolved items. Support comparisons with evidence and applicable conditions, and retain limitations that affect correctness, safety, compatibility, requirements or execution.
- Keep a rule only when it changes a meaningful decision, belongs at that layer, and is not reliably recoverable from source, configuration, or tooling.
- Merge inherited duplicates and repeated workflow prose while preserving exact contractual wording, authorization gates, public-interface boundaries, and project-specific completion criteria.
- Remove old-model scaffolding, fixed output quotas, repeated status rituals, blanket rereads, unconditional checklists, and failure-specific workarounds that no longer change a decision.
- Prefer repository tooling, tests, linters, or CI for mechanically enforceable behavior. Do not add dependencies merely to reorganize instructions.
- Before retiring a guide or role, map all live references and unique rules. Move surviving content first, then verify dead links and callers; historical mentions may remain when they are not live instructions.
- Preserve explicit user choices and safety boundaries. Never claim that a shorter file improves quality, cost, or runtime behavior without measured evidence.

## Preserve maintainability decisions

- Keep explicit equivalent-syntax, return-type, explicit-public and responsibility-based member-order preferences at the user/global layer; do not replace them with a generic Clean Code style. Preserve equivalent behavior, clear reading and applicable tooling support
- When recording extraction or inlining rules, judge the full helper call chain, meaningful abstraction boundaries and navigation cost. Avoid pass-through layers, but do not inline into hard-to-read or overly long callers; do not invent fixed function-length or layer-count limits
- Place type/file cohesion and single-state-owner principles at their durable layer. Keep framework-specific Component/Service placement in applicable project guidance, and record concrete refactor candidates as task work items rather than implementation authorization

## Load detailed guidance only when needed

- When creating, splitting, or relocating global, root, nested, or tool-specific agent instructions, read [instruction-layering.md](references/instruction-layering.md).
- When changing task intake, source selection, Git authorization or completion reporting, read [task-execution-and-reporting.md](references/task-execution-and-reporting.md). Keep examples conditional rather than always loaded.
- When changing delegation, worker ownership, subagent context, or model/reasoning routing, read [delegation-routing.md](references/delegation-routing.md).
- When changing ongoing user guidance, task-state checkpoints, interruption recovery, role context, compaction, task switching, handoffs, memory or Context Brief policy, read [context-continuity.md](references/context-continuity.md).

For maintenance spanning canonical guidance, installed Skills/Plugins and teaching, read [maintenance acceptance](references/maintenance-acceptance.md). Use it for affected-source synchronization and representative checks, not a per-turn ritual.

For adding or revising owned Skills, references, Python helpers, Plugins, MCP adapters or their distribution, read [component authoring](references/component-authoring.md). Use it to select the maintained unit, language, conditional context and necessary checks, without adding a fixed per-task checklist or a new delegation policy.

## Verify and deliver

- Review the final instruction hierarchy for contradictions, unreachable references, duplicated authority, ambiguous ownership, and rules placed above their valid scope. For routing changes, check direct work, bounded delegation, independent tasks, main-model changes and interrupted handoffs; each must retain authorization, unfinished work and acceptance responsibility.
- Start with the smallest sufficient readback, syntax, metadata, reference and mirror checks for changed governance files and affected callers. If evidence is insufficient or a check fails, expand gradually to address the remaining concrete risk, stating the missing evidence and added scope. Retain applicable required gates. Use application builds or E2E only when governance changes affect application behavior; avoid unrelated suites and new test infrastructure for text-only changes.
- If synchronized copies were requested, compare paths and content after the copy. Syntax checks do not prove that a client reloaded the new guidance.
- Report in conversation text against the original request and all effective steering received during this execution. State progress and deviations, list every changed file and its scope, include actual test/check results and coverage in each delivery or phase report, distinguish passed, failed, blocked, not run and unverified, explain why a check did not run or apply, and retain remaining acceptance. Add recommendations only when useful. Do not create a separate report document unless requested. Verify requested mirrors; source validation alone does not prove client reload.
- Include actionable recommendations when they help a decision or follow-up, with evidence, applicability and a next step. Separate required work from optional improvements; suggestions neither expand authority nor replace authorized work.
