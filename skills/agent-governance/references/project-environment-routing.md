# Project environment and lifecycle routing

Read when setting up a project, revising roles, selecting owners for a materially different runtime, or coordinating development/test/release boundaries. These are conditional defaults to adapt from verified source, not a project roster or permission to delegate.

## Common owner model

Main retains requirements, authoritative sources, cross-module/state/interface decisions, necessary direct implementation, integration and final acceptance. No-subagent execution is normal. Prefer available Explorer/Worker/Reviewer capabilities; add custom roles only for durable differences in permissions, mutable resources or expected evidence. User/environment restrictions take precedence.

Explorer maps one unresolved area read-only; Worker owns one coherent behavior and its focused checks; Reviewer independently assesses a concrete risk read-only. Optional test_worker owns authorized fixtures/execution without silently changing acceptance or application APIs; evaluation_reviewer interprets recorded stochastic/model/performance evidence; release_reviewer examines immutable artifacts and required gates without publishing. Use their starter templates only when those responsibilities cannot be expressed adequately through available roles.

| Confirmed environment | Useful ownership boundary | Conditional evidence and constraints |
|---|---|---|
| Python CLI, desktop or portable package | Command/config/core and platform adapter as a coherent slice; packaging review when target-platform risk warrants it | Actual Python/OS/architecture, exit codes, paths, native WebView/build and cleanup; source checks do not prove native distribution |
| Browser app, shared UI or extension | Feature state and consumers together; narrow browser exploration/reproduction where needed | Served artifact, accessibility, async/disposal, storage, actual permissions, extension lifecycle and supported browser engine |
| Browser game or simulation | Rule/clock/RNG/save owner; UI consumer interfaces agreed first | Seeds, numerical representation, offline equivalence where specified, migration, multi-tab ownership, balance and real playtest |
| Unity or Unreal | Coupled gameplay/assets/serialization with one owner; target-build/device checks as a distinct accepted scope | Engine/package version, binary assets and editor instance, lifecycle/physics, player/cooked builds, rendering and multiplayer |
| LLM/RAG/agents or stochastic media | Application/tool/access boundaries separated from an explicitly owned evaluation slice | Model/checkpoint/provider, dataset authority, held-out cases, GPU contention, costs and actual output state |
| Backend/monorepo | Confirmed module owners and public formats; shared-interface decisions precede parallel edits | Runtime, authentication, migration, persistence and actual consuming modules |
| Documentation/configuration | Source/terminology/link scope with the narrowest readback or parser | Provenance, publication/synchronization authority and actual client loading |

Select an available test-strategy Skill only when testing decisions or missing lifecycle evidence need work; recorded-result interpretation stays with validation-evidence-review when available. Use packaging-acceptance for actual artifact acceptance, and domain Skills for implementation. Missing optional Skills do not block known project checks.

## Dispatch and resources

Define the owned files/modules, expected behavior and independent oracle, authorized data/environment, must-preserve constraints, acceptance, revision/diff state and stop condition. Give only context needed by the slice, preserving previous effective decisions and current user steering. A child cannot expand scope, install dependencies, run production writes or release from a role description.

Parallelism requires stable interfaces and independent mutable resources: browser profiles/ports, temporary outputs, fixtures/stores, editor instances, binary assets, GPU/VRAM and build caches may couple otherwise separate files. Sequence conflicting or measurement-sensitive work. Do not run multiple benchmark owners concurrently and later infer unloaded performance from resource counters.

Main chooses supported model/effort from uncertainty, consequences and verification, separately from role names and Main settings. Portable templates omit pins. Personal defaults remain in private configuration; confirm effective role/default precedence, live capabilities and actual loading rather than assuming a parsed TOML means a spawned role is active.

Review returned work against actual source/artifact state, checks and remaining acceptance; retain unknowns. Development readiness, focused test PASS, native packaging, installed client discovery and published release are separate states. Recommendations and role availability do not authorize new chats, messages, installations or publication.

Sources checked 2026-10-07: [official custom subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) describes narrow custom roles and schema; [community setup example](https://www.reddit.com/r/codex/comments/1ujjcxh/how_i_set_up_codex_subagents_without_overusing/) illustrates selective roles, not a benchmark or required configuration. Runtime-specific decisions above are maintenance choices to verify against each project.
