---
name: unity-development
description: Implement, refactor, diagnose, or review Unity projects while preserving the repository's Unity version, packages, scenes, prefabs, serialized assets, render/input pipelines, and build targets. Use for Unity project work, not general C# outside Unity.
metadata:
  version: "0.4.14"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Unity Development

Follow the project's exact Unity editor and package contracts. Do not assume a current Unity release, render pipeline, input system, backend, or target platform.

## Discover the project

- Read `ProjectSettings/ProjectVersion.txt`, `Packages/manifest.json`, `Packages/packages-lock.json`, relevant ProjectSettings, asmdefs, scenes, prefabs, tests, and build scripts.
- Resolve the active render pipeline, input system, scripting backend, API compatibility level, target platforms, Addressables or asset-bundle usage, and version-control serialization settings.
- Find existing gameplay, editor-tooling, dependency-injection, event, state, save-data, pooling, and async patterns before adding another pattern.
- Inspect Git status and preserve concurrent asset, scene, prefab, and `.meta` changes.

For economy, progression or stochastic-reward work, use an available game-balance-simulation Skill when relevant. Keep the simulation tied to the same C# rules and numeric types; engine lifecycle and serialized-asset verification remain here.

## Implement safely

- Keep runtime and Editor-only code separated. Place editor APIs behind Editor assemblies or compile guards consistent with the project.
- Preserve serialized field names and types unless migration is part of the task. Use the project's established migration approach for renamed or replaced serialized data.
- Preserve asset GUIDs and their `.meta` files. Do not recreate, move, or rename assets casually, and do not hand-edit scene or prefab YAML unless the task and serialization mode make that the safest reviewed change.
- Avoid hidden lifecycle dependencies. Respect Unity execution order, domain reload settings, scene loading, object lifetime, and disabled/destroyed object behavior. When domain reload is disabled, account for retained static state and event subscriptions; verify repeat Play Mode entry when changing their lifecycle.
- Match the existing update model and performance budget. Avoid unnecessary per-frame allocation, repeated lookups, synchronous asset loads, or main-thread blocking in hot paths.
- Keep platform, quality, graphics, input, physics, and player settings scoped to the requested targets. Do not change global ProjectSettings to solve a local issue without evidence.
- Do not add or upgrade packages, regenerate lockfiles, or migrate render/input pipelines without explicit scope.

## Verify

- Prefer focused EditMode tests for deterministic/editor logic and PlayMode tests for scene, lifecycle, coroutine, physics, rendering, and interaction behavior.
- When behavior depends on a scene or prefab, verify the actual serialized asset and references, not only the C# compiler result.
- Run the smallest relevant build or platform check when build settings, stripping, IL2CPP, shaders, Addressables, native plugins, or platform APIs are affected.
- Separate script/test success from unverified editor interaction, asset import, graphics output, device behavior, performance, and platform build results.
- Report the Unity and package versions used, changed assets and GUID-sensitive operations, actual checks, and any editor or target-platform verification not run.

For explicit test strategy, missing coverage or lifecycle acceptance work, use an available test-strategy Skill and its relevant domain reference. Keep actual project checks usable without that optional Skill. Recorded evidence review, target-platform execution and release authorization remain separate.
