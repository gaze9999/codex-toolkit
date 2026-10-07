# AGENTS.md instruction layering

Use this reference when reorganizing agent instructions for a repository or moving the same governance pattern to another computer or project.

## Resolve the active hierarchy

- Verify the target agent's current official discovery, precedence, filename, size, and configuration behavior before editing. Do not assume every tool implements `AGENTS.md` or nested files identically.
- First identify the execution environment. ChatGPT account and Project instructions, cloud Work settings, and local Codex file configuration are separate control surfaces. Do not infer account adoption, cloud configuration, or memory synchronization from a local file edit.
- For local Codex, resolve the first nonempty global `AGENTS.override.md` or `AGENTS.md`, then each applicable directory from the repository root to the working directory. Each directory selects at most one instruction file, preferring its override, then the base file, then configured fallbacks. Later, nearer guidance refines broader earlier guidance; keep the combined size limit in mind.
- A workspace instruction file above the Git root is not automatically part of that repository's discovered chain. When a project needs that workspace boundary, maintain an explicit conditional reference and preserve standalone-clone behavior.
- Inventory root and nested instruction files, tool-specific configuration, role definitions, task guides, live references, and ignored files. Inspect ignored governance files directly because a normal Git diff may omit them.

## Place rules at the narrowest durable scope

- Keep global instructions limited to stable cross-project preferences, authorization boundaries, safety, evidence honesty, and execution principles.
- Keep purpose, authorization and evidence-selection principles global; put task-specific feasibility, prohibitions, source pointers, checks and delivery criteria in the active task or the nearest relevant guide. Treat these as decision dimensions, not a required form or universal reading/testing checklist.
- Follow the maintained language split: concise Taiwan Traditional Chinese for global/general agent guidance; concise English for subagent instructions, project root/nested AGENTS.md, project agent guides, and Skill instructions, references and usage guides unless explicitly overridden. Classify templates by their intended scope rather than directory name. Preserve parser terms, quotations and localized artifacts; instruction language does not set the language of user-facing output.
- Keep stable document-writing preferences in global/user guidance; subagent roles follow applicable guidance instead of maintaining full copies. Independently installable authoring Skills retain the relevant output rule within their own scope.
- Keep Desktop Git commit, PR and PR-watch prompts limited to shared output/evidence principles. Project title syntax, folder-to-scope mapping, tickets, branch conventions and acceptance belong in project instructions. Put required shared Git behavior in global AGENTS.md too, so an agent using CLI or MCP can follow it without relying on Desktop-only settings; verify the active client loads those instructions.
- Keep the repository root tool- and model-neutral. It should contain only rules that apply across the repository, such as cross-module architecture, public boundaries, shared safety, generic ownership, and common verification.
- Put framework, runtime, package-manager, directory layout, build/serve commands, local conventions, public interfaces, and focused checks in the nearest nested instruction file whose subtree they govern.
- Keep tool-specific role names, model/reasoning defaults, invocation parameters, and orchestration mechanics in that tool's configuration or conditional guide. Do not require every `AGENTS.md` consumer to read Codex-only behavior.
- Put transaction-, feature-, or workflow-specific procedures in a task guide or Skill with an explicit loading trigger. Keep current progress, temporary exceptions, blockers, and stop conditions in the current task.

## Restructure safely

1. Classify every existing rule by scope and identify exact duplicates, broader summaries, and unique contracts.
2. Create the narrower destination before removing a unique rule from the broader file.
3. Preserve cross-boundary contracts in the closest common ancestor. A nested file may refine local implementation but must not silently weaken repository-wide authorization, safety, or public-interface rules.
4. Replace tool-specific syntax in root guidance with portable intent only when the behavior remains enforceable; keep exact tool settings in maintained configuration.
5. Update live references and role files that point to moved sections. Avoid parallel copies that can drift.
6. Keep the final hierarchy concise enough that an agent working in one subtree receives only relevant local context.

## Verify the migration

- From the repository root and each affected subtree, enumerate the effective instruction chain in load order and check for contradictions or gaps.
- Search for moved headings, role names, model names, invocation parameters, runtime versions, and stale links. Confirm each surviving occurrence belongs at that layer.
- Validate syntax and metadata, compare synchronized copies byte-for-byte when requested, and inspect Git status. Report ignored or untracked governance files explicitly.
- For settings requiring an account, web, or app UI, provide the exact destination, proposed content or value, and remaining manual action separately. Do not invent configuration keys, copy generated memory files as mandatory guidance, or report an unapplied setting as complete.
- Do not claim that shorter instructions reduce tokens, cost, latency, or errors without measurement. Confirm file content immediately; treat runtime reload by an already-open client as unverified unless observed.

## Portable outcome

A reusable governance setup should leave project facts in the project and only the restructuring method in the portable Skill. On another computer, rediscover the repository and tool configuration, then apply this method instead of copying framework versions, paths, role names, models, or commands from the previous project.

## Project-local visibility and Git storage

Apply when creating or maintaining project-local agent files. Resolve the actual remote repository visibility and current tracked state; directory names, package `private` fields and cached assumptions are not visibility evidence. Do not query unrelated repositories.

- Public: keep newly created local `AGENTS.md`/override files, roles and project agent guides out of version control by default. Use the repository-local exclude file resolved by `git rev-parse --git-path info/exclude`; preserve its existing entries. Add only actual owned paths, including applicable nested instructions. A shared `.gitignore` policy requires that project's explicit choice, not a default edit of public source.
- Private: reviewed portable project guidance may be versioned by default. Secrets, credentials, personal absolute paths, machine state and unapproved company/customer content remain excluded. Permission to create guidance does not authorize staging, commits or remote publication.
- Unknown visibility or no remote: retain the files locally and exclude them within the initialized repository until visibility is confirmed. For a directory without Git, report the local-only state and ensure the policy is applied before its first publication.
- Existing tracked files: ignore does not stop tracking. Preserve approved shared instructions; identify tracked local/private content requiring a user decision. Do not automatically use `git rm --cached`, delete files, rewrite history or change visibility. Sensitive content already published needs separately authorized remediation.
- Explicitly requested public neutral templates, reusable Skill/Plugin assets or shared contributor guidance may remain tracked. This is a deliberate distribution exception, not permission to publish personal project instructions. Do not blanket-ignore `.codex/`, `skills/`, plugin payloads or all documentation.

Verify exact exclusions with `git check-ignore -v` for untracked local paths and separately inspect `git ls-files`/status for tracked paths. For an illustrative newly created root instruction plus dedicated role/guide folders, patterns can include `/AGENTS.md`, `/.codex/agents/` and `/.codex/agent-guidance/`; replace them with the actual owned paths and add nested instruction paths only when present. Do not copy an example as a full repository policy. Validate ignored instructions by direct readback and distinguish local availability from synchronized/loaded client state.
