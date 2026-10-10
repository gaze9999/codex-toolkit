---
name: agent-governance
description: Create, audit, or simplify project AGENTS.md layers, Codex subagent roles and durable goal recovery across conversations. Use for instruction-governance work, not ordinary implementation or general code review.
metadata:
  short-description: Agent governance, role boundaries, and instruction minimization
  version: "0.5.7"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Agent Governance

Create or simplify instruction layers and durable role boundaries. Keep rules that change decisions, at their narrowest valid scope; remove inherited duplicates and route conditional procedures outside always-loaded instructions.

## Scope

- An audit or recommendation is read-only. An edit request authorizes the identified instructions, role configuration and related guidance; it does not authorize application refactoring, installation or external actions. Complete requested edits and their relevant checks; an explicit prompt/plan/review/handoff request receives that artifact.
- Resolve applicable instruction sources, actual project/tool configuration, relevant Git status/diff and ignored guidance. Preserve concurrent work. Choose sources and acceptance from the intended outcome and effective authorization, without a fixed questionnaire or exhaustive rereading.
- Verify current official OpenAI behavior when changing instruction discovery, configuration, model/reasoning or subagents. Distinguish project evidence and human reports from product specifications.
- Stable cross-project preferences belong in Global, project facts and authorized record pointers at root/nested scope, role differences in roles, and conditional procedures in references. Execution state stays in the task; durable goals, decisions and acceptance use the selected authorized project record. Judge execution scope rather than the directory where guidance is authored.
- Global/general instructions use concise Taiwan Traditional Chinese; project, role and Skill instructions/references use concise English unless explicitly overridden. Classify templates by intended use and preserve parser terms, quotations and localized outputs. User-facing language follows the user/project.
- Preserve confirmed decisions, exact contractual wording, authorization, public interfaces and acceptance. Prefer existing enforcement tools over repeated prose. Replace discoverable paths, versions, role lists and routine sequences with source-selection conditions; keep exact values only when they govern safety, compatibility or an explicit decision. Examples do not become mandatory defaults, and brevity needs no fixed length/output quota.

## Select relevant detail

| Changed concern | Read |
|---|---|
| New project instructions, roles or code-maintenance preferences | [Project setup](references/project-setup.md); select starter assets only when useful |
| Global/root/nested scope, discovery or exact Git exclusions | [Instruction layering](references/instruction-layering.md) |
| Project lifecycle, environment or shared resource ownership | [Project environment routing](references/project-environment-routing.md) |
| Task intake, evidence, Git authority or reporting | [Task execution and reporting](references/task-execution-and-reporting.md) |
| Cross-client response formats, finished writing or interactive presentation | [Response presentation](references/response-presentation.md) |
| Delegation, worker context or supported model/reasoning choices | [Delegation routing](references/delegation-routing.md) |
| Ongoing steering, new-conversation goal recovery, interrupted work, compaction or handoffs | [Context continuity](references/context-continuity.md) |
| Public/private sources or planned public delivery | [Public and private delivery](references/public-private-delivery.md) |
| Sensitive-data exposure or history cleanup | [Sensitive-data removal](references/sensitive-data-removal.md) |
| Canonical guidance, installed owners and teaching synchronization | [Maintenance acceptance](references/maintenance-acceptance.md) |
| Persistent project tracking, cross-device settings or recurring document maintenance | [Shared workflow](references/shared-workflow.md) |
| Owned instructions, Skills, helpers, Plugins, MCP, tool selection or teaching workflow changes | [Component authoring](references/component-authoring.md), including relevant collected research |
| Skill/Plugin boundaries, context budgets or measured comparison | [Operating efficiency](references/operating-efficiency.md) |

## Verify and deliver

Before retiring guidance, map live callers and unique rules, move surviving decisions, then check references. Review the resulting hierarchy for contradictions, duplicated authority, unreachable references and ambiguous owners.

Start with affected content review, metadata, syntax, references and requested mirrors. Expand only for a concrete gap or required gate; text-only guidance does not require application builds/E2E. Routing changes retain direct-work, delegation and handoff authorization, unfinished work and Main's acceptance responsibility.

Report the result against the effective request, changed files, actual check scope and unfinished acceptance. Keep direct checks, historical evidence and others' reports distinct. Requested mirrors need content comparison; installed bytes do not prove existing-client reload. Give useful recommendations separately from required work, and create a separate report only when requested. Shorter guidance alone does not establish better quality, cost or runtime behavior.
