# Project type prompts

Choose only applicable rows. These are questions to resolve from the target repository, not facts to copy into `AGENTS.md`. Place confirmed rules in the narrowest relevant directory.

| Type | Check before writing guidance |
|---|---|
| User-facing application | UI and state ownership, navigation, accessibility, assets, manual and automated checks |
| Game or simulation | Shared rule core, clock/RNG ownership, numerical representation, event ordering, offline settlement, save compatibility and reproducible balance experiments |
| API or service | Public endpoints, authentication, persistence, external services, migrations and integration checks |
| CLI or desktop tool | Command and file compatibility, configuration precedence, cross-platform behavior and packaging |
| Library or SDK | Public symbols, supported runtimes, version compatibility, package outputs and usage examples |
| Monorepo or multi-module system | Module owners, dependency direction, shared interfaces, outputs and focused checks per module |
| Data pipeline or automation | Source schema, idempotency, schedules, recovery, privacy and output validation |
| Infrastructure or deployment | Environment boundaries, secrets, approval, rollout, rollback and safe verification |
| Documentation or content | Authoritative sources, output formats, links, publication and synchronization permissions |

Language is separate from project type. Read actual manifests, compilers and CI before recording a language, version, package manager or command. Put language-specific guidance beside the code it governs instead of adding every language to the root file.
