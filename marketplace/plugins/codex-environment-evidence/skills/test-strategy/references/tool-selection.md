# Select testing interfaces and optional MCP adapters

Read for optional-tool selection, a missing check capability or requested interface selection. Choose by capability, supported version, session/data isolation, permissions and total accepted-task cost. A configured adapter is not proof of client discovery, authentication or a successful call.

| Need | Starting point | MCP adds value when |
|---|---|---|
| Deterministic checks, CI, artifacts and hashes | Existing project CLI and focused Skill | Client needs structured guarded access unavailable through existing tools |
| Browser flow or debugging | Available compatible browser/Playwright/DevTools interface | Live state, traces or native client access materially improve evidence |
| Unity/Unreal editor state | Existing engine commands/test framework and approved editor interaction | Tool schema exposes actual scene/asset/runtime operations needed by the task |
| AI evaluation | Existing versioned fixtures/eval runner and model API | Approved structured tool/service integration is a concrete requirement |

## Optional inspection tools and required checks

ESLint, Stylelint and Serena are optional aids unless the governing project, CI or explicit acceptance criteria require their checks. An installed package, editor save action or available script alone does not establish a required gate.

| Evidence needed | Select when useful | Available alternative and evidence boundary |
|---|---|---|
| JS/TS or Angular structure and syntax | Project-matched compiler, AST and Angular parser | Parsing establishes syntax; use the project compiler for types/templates |
| TS/JS/HTML convention rules | ESLint with the owning project's configuration and resolved plugins | Compiler/AST/manual review can continue, with the unrun lint rules identified |
| CSS/SCSS/Sass convention rules | Stylelint with the owning project's reviewed configuration | Existing Sass compiler, selected formatter and consumer review provide different evidence |
| Semantic symbols and cross-file references | Serena with the intended checkout and relevant language servers active | Local compiler APIs, editor navigation and bounded search can resolve the selected question |

If an optional tool is missing, unconfigured or fails to start, record that tool's result and unexecuted coverage, then continue independent checks that can answer their own questions. A required check stays blocked until its prerequisite is resolved; alternate evidence does not mark it passed. Select installation or repair separately within its authorized scope. Preserve original exit codes and distinguish tooling failure from a confirmed source defect.

Keep confirmed conditions, selectors and required gates. Selecting another compatible tool does not itself authorize more roles, data, state combinations, repetitions or external actions. Formatting, linting, compilation and runtime interaction remain separate results.

## Candidate research, checked 2026-10-07

- [CoplayDev Unity MCP](https://github.com/CoplayDev/unity-mcp): primary project README lists editor operations and test/profile/build capabilities, MIT, approximately 14.7k GitHub stars at inspection. Verify the exact release, Unity package/runtime prerequisites and discovered test tools before selecting it.
- [ChiR24 Unreal MCP](https://github.com/ChiR24/Unreal_mcp): primary README describes a C++ editor bridge with TypeScript server, MIT, approximately 903 stars at inspection. Inspect compatible engine/plugin/server versions, operation permissions, distribution and failure recovery. It is a candidate for editor interaction, not a replacement for Unreal's own automation framework.
- [Unity community discussion](https://www.reddit.com/r/Unity3D/comments/1vm26dn/unity_advertises_ai_everywhere_so_i_decided_to/): reports differ about adapter testing support. Treat them as version-specific anecdotes that motivate checking live capabilities, not proof of current feature absence.

Recheck current maintainer activity, release history, reproducible issues, CI and substantive user examples. Stars, posts and promotional feature counts measure interest, not adopted workflows or correctness. Prefer primary documentation for technical claims, using community reports to identify questions worth reproducing. Record the observation date and distinguish README claims from locally verified behavior.

Before installation, resolve the actual project version, target device/client, exact missing capability, source/license, requirements and modification scope. Engine package installation changes the project and may require editor restart; client MCP configuration changes another owner. Keep secrets and approved roots local, prefer narrow/loopback access, verify discovery and one authorized bounded call, and clean up owned sessions. No engine MCP is a default dependency of this Skill.
