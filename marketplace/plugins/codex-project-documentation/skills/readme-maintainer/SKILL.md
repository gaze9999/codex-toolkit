---
name: readme-maintainer
description: Create or substantially restructure a repository README from verified project evidence. Use for README-focused work, not routine documentation sync, license decisions or downloadable reports.
metadata:
  version: "0.4.14"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# README Maintainer

Produce a README that is accurate, scannable, usable by a new developer, and suitable for public presentation when the repository permits it.

## Activation and boundary

- Use when the user explicitly asks to create, rewrite, restructure, audit, or substantially improve a README. An audit is read-only unless edits are also authorized; return concrete findings or no findings rather than silently rewriting it.
- For documentation synchronization after an implementation change, use the applicable documentation-update workflow instead unless the README itself needs substantial redesign.
- Do not modify application code, deployment, manifests, or project behavior merely to make the README easier to write.

## Establish evidence

- Start with the current README and the evidence needed for the requested sections. Inspect relevant manifests, runtime/version files, scripts, entry points, configuration examples and build/deploy files; read lockfiles, tests, demos and related docs only when they resolve a material claim. A README task does not require reading the whole repository.
- Derive features, architecture, requirements, commands, environment variables, package manager, build outputs, and deployment behavior from the repository. Do not infer capabilities from the repository name or stale prose.
- Resolve the intended audience and language. Use the language selected by the user or applicable project guidance; otherwise preserve the repository's established documentation language.
- Treat unverified commands, screenshots, badges, coverage, compatibility, roadmap items, and deployment status as unresolved rather than claims.

## Write only useful sections

- Open with the purpose, problem solved, and core capability in a short factual introduction.
- Add only sections supported by the project, such as Features, Tech Stack, Requirements, Installation, Configuration, Usage, Development, Testing, Build, Deployment, Architecture, Screenshots/Demo, Roadmap, Contributing, or License.
- Keep the README license section factual and link to the canonical repository file. If the task requires selecting, creating, or changing legal text, use `license-maintainer` and require explicit licensing decisions.
- Make setup and common usage directly actionable. Use exact repository commands and safe placeholders for configuration.
- Keep code examples short and representative. Distinguish local development, production build, and deployment.
- Use a compact diagram only when it materially clarifies a non-trivial architecture, data flow, agent flow, RAG pipeline, or model workflow.
- Use informative badges only when their target and status are real. Prefer repository-relative links for internal documents and assets.
- Put detailed specifications, research, or long operational procedures in dedicated docs and link to them instead of duplicating them.
- Never include secrets, credentials, private endpoints, personal absolute paths, production data, unredacted logs, or unsafe `.env` values.

For section order, first-use teaching, compact examples, optional screenshots/diagrams and explanation-first wording, read [README presentation](references/presentation.md) when that part of the README is being revised. Keep a short actionable reader path and link advanced tool/API details; images are useful only when they teach something current and verified.

- Write to explain purpose, operation and results. Remove generic disclaimers and defensive comparisons that do not change usage. Preserve concrete dependencies, compatibility, write/overwrite behavior, data/account boundaries, unverified claims and legal notices beside the relevant operation.
- Choose length and layout by the audience and supported interfaces, not a universal word quota. Do not add a screenshot, badge, tutorial section or full tool catalog merely to fill a template.

## Verify and deliver

- Check authored prose with available textlint or an equivalent language checker, then review meaning and Taiwan terminology manually. Preserve source quotes, legal text, code, identifiers and English/Japanese conventions. Report unavailable, failed or unchecked coverage. Sensitive content may skip tool processing and temporary files; review it manually and report the exception.
- Check headings, links, referenced paths, examples, configuration keys, and commands against repository state. Run safe existing commands only when needed and authorized.
- Confirm that the README does not promise unimplemented behavior or tests that were not run. Clearly label optional, planned, or unverified material.
- Return the changed README, or findings for a read-only audit, and a concise note of evidence used, actual checks, and any command, demo, deployment, badge, screenshot, or compatibility claim that remains unverified.
