# Select testing interfaces and optional MCP adapters

Read only when existing tools cannot provide the needed evidence or interface selection is requested. Choose by capability, supported version, session/data isolation, permissions and total accepted-task cost. A configured adapter is not proof of client discovery, authentication or a successful call.

| Need | Starting point | MCP adds value when |
|---|---|---|
| Deterministic checks, CI, artifacts and hashes | Existing project CLI and focused Skill | Client needs structured guarded access unavailable through existing tools |
| Browser flow or debugging | Available compatible browser/Playwright/DevTools interface | Live state, traces or native client access materially improve evidence |
| Unity/Unreal editor state | Existing engine commands/test framework and approved editor interaction | Tool schema exposes actual scene/asset/runtime operations needed by the task |
| AI evaluation | Existing versioned fixtures/eval runner and model API | Approved structured tool/service integration is a concrete requirement |

## Candidate research, checked 2026-10-07

- [CoplayDev Unity MCP](https://github.com/CoplayDev/unity-mcp): primary project README lists editor operations and test/profile/build capabilities, MIT, approximately 14.7k GitHub stars at inspection. This is stronger visibility than a small adapter, not a safety or quality guarantee. Verify the exact release, Unity package/runtime prerequisites and discovered test tools before selecting it.
- [ChiR24 Unreal MCP](https://github.com/ChiR24/Unreal_mcp): primary README describes a C++ editor bridge with TypeScript server, MIT, approximately 903 stars at inspection. Inspect compatible engine/plugin/server versions, operation permissions, distribution and failure recovery. It is a candidate for editor interaction, not a replacement for Unreal's own automation framework.
- [Unity community discussion](https://www.reddit.com/r/Unity3D/comments/1vm26dn/unity_advertises_ai_everywhere_so_i_decided_to/): reports differ about adapter testing support. Treat them as version-specific anecdotes that motivate checking live capabilities, not proof of current feature absence.

Recheck current maintainer activity, release history, reproducible issues, CI and substantive user examples. Stars, posts and promotional feature counts measure interest, not adopted workflows or correctness. Prefer primary documentation for technical claims, using community reports to identify questions worth reproducing. Record the observation date and distinguish README claims from locally verified behavior.

Before installation, resolve the actual project version, target device/client, exact missing capability, source/license, requirements and modification scope. Engine package installation changes the project and may require editor restart; client MCP configuration changes another owner. Keep secrets and approved roots local, prefer narrow/loopback access, verify discovery and one authorized bounded call, and clean up owned sessions. No engine MCP is a default dependency of this Skill.
