# Game testing

Read when changed game rules, engine lifecycle, save data, hardware behavior or multiplayer need evidence. Determine whether the project is a browser simulation, Unity, Unreal or another engine from actual source. Do not infer an engine from a repository name or install one for this reference.

## Rule core and simulation

Prefer the production rule core over a second simulator. Verify any surrogate against shared fixtures before comparing strategies. Record seed/RNG ownership, numeric types/rounding, event ordering, timestep, horizon and content/save versions. A fixed seed supports reproduction but does not sample every outcome or guarantee cross-platform determinism.

Check conservation and bounds only when the design requires them; intended resource creation/destruction must remain valid. Examples include legal assignments, finite values, stable identities, once-only unlocks and no duplicated refunds. Test partitioned versus continuous time advancement only when the rules promise equivalence, including cap boundaries, pauses, interrupted builds, reset and offline limits. Preserve legitimate frame-based behavior.

Save tests cover old-version migration, unknown/corrupted saves, backup retention, partial writes, competing tabs/processes, import validation and round-trip semantics. Use copies and isolated storage, never player progress. Browser automation is appropriate for browser games without an engine adapter.

For economy/balance experiments, use an available game-balance-simulation Skill. Preserve unreached milestones/censored runs, held-out seeds and distinct player strategies. Resource balance, automated play completion and optimizer scores do not prove engagement or fun; include authorized human playtest criteria when required.

## Engine-specific evidence

| Environment | Select from actual changed behavior | Keep separate |
|---|---|---|
| Unity | Installed Test Framework's Edit Mode for deterministic/editor behavior; Play Mode for lifecycle, scene/physics and interactions; serialization/GUID compatibility | Player build, target GPU/device, render pipeline, IL2CPP/native plugins and sustained profiling |
| Unreal | Installed Automation Framework for supported unit/feature/smoke/content cases, functional maps for world behavior, screenshot baselines when required | Editor-only validation versus cooked packaged build and target rendering/hardware |
| Multiplayer/session orchestration | Authoritative owner, reconnect, timeout, ordering, replication, client/server disagreement and isolated identities; Gauntlet when the Unreal project already supports it | Real deployment/network conditions, platform authentication and production concurrency |

Binary scenes/assets, shared editor instances, build outputs and save stores are mutable resources. One owner controls a coupled asset/state flow. Parallel engine or GPU experiments require independent instances/data and measured resource isolation; different source files do not suffice. Establish baseline frame/CPU/GPU time and memory under comparable scenes/settings, not FPS alone.

Sources: [Unity test modes, package 1.4 example](https://docs.unity3d.com/Packages/com.unity.test-framework@1.4/manual/edit-mode-vs-play-mode-tests.html), [Unreal Automation Framework](https://dev.epicgames.com/documentation/en-us/unreal-engine/automation-test-framework-in-unreal-engine), [Gauntlet](https://dev.epicgames.com/documentation/unreal-engine/gauntlet-automation-framework-overview-in-unreal-engine?lang=en-US). Resolve the project's installed documentation version; these links are not required package versions.
