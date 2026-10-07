# Project agent starter

Use these files only when creating or revising governance for a specific project. Start with the project's actual source, configuration, existing instructions and user-provided material. Treat these files as examples, not active instructions or a required layout.

1. Select relevant concerns from [project-types.md](project-types.md). A repository may fit several types.
2. Fill [root/AGENTS.md](root/AGENTS.md) with verified repository-wide facts. Remove every `<placeholder>` and any rule that does not change a decision.
3. Add [nested/AGENTS.md](nested/AGENTS.md) only in directories with distinct runtime, ownership, public interfaces or checks. Rename `nested` to the real directory when copying.
4. Add [root/.codex/agent-guidance/tasks.md](root/.codex/agent-guidance/tasks.md) only if the project needs task routing or handoff rules beyond the global setup. The root file loads it only for relevant work.
5. Prefer available built-in subagents. Copy only useful files from `root/.codex/agents/`, then specialize their names and boundaries. The portable TOML files omit model pins so each slice can choose a supported model and use a maintained subagent fallback; effort is optional. A target project may pin a model for a stable narrow role when current evidence justifies it. Verify the effective configuration; a role pin overrides a spawn choice and a model-only pin retains previously resolved effort in current Codex.
6. Check the target coding agent's current instruction discovery and role configuration before installing. Other agents may ignore Codex TOML or nested `AGENTS.md`.

Write project root/nested instructions, project agent guides and subagent role instructions in concise English. Keep global/general agent guidance in concise Taiwan Traditional Chinese. Instruction language does not change the user-facing output language; preserve quotations, parser terms and localized artifact examples.

For a backend, legacy Host and migrated custom-element architecture, consult the [sanitized project example](examples/host-and-custom-elements/AGENTS.md). Its conditional [records guide](examples/host-and-custom-elements/.codex/agent-guidance/records.md) illustrates progress triggers, stable IDs and commit evidence. Adapt verified facts and recording policy before use; neither example is active global guidance.

Keep the always-loaded root and nested files short. Put task-specific procedures in conditional guides or skills, and current goals, decisions, progress and permissions in the current task. Do not copy private paths, organization names, secrets, endpoints, unverified versions or commands into public files. A template does not grant permission to spawn subagents, create tasks, change dependencies or publish work.

For an independently reviewable game-economy experiment, [game_balance_reviewer.toml](root/.codex/agents/game_balance_reviewer.toml) provides an optional read-only role. Keep core implementation and experiment generation with their owner; do not install this role globally or require a reviewer chain for routine game changes.

Before delivery, validate active instruction order from the repository root and affected subdirectories, parse selected TOML, inspect Git status and ignored files, and confirm that an agent run loads the intended files. Existing sessions may need to restart before new guidance is active.
