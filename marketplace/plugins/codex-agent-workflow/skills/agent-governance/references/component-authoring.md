# Component authoring and maintenance

Read when adding or changing an owned Skill, executable helper, Plugin, MCP adapter or governance layer. Ordinary implementation does not require this workflow.

## Choose the maintained unit

| Need | Owner and format |
|---|---|
| Stable cross-project preference or authorization boundary | Concise global guidance |
| Verified architecture, local convention or required check | Nearest project `AGENTS.md` |
| Repeatable agent decisions, task intake and acceptance | Focused `SKILL.md` |
| Conditional schema, procedure, examples or troubleshooting | Linked `references/` with an explicit loading condition |
| Template or input copied into an output | `assets/`, read only when needed |
| Repeated deterministic processing or reliable external-tool operation | Executable helper, not prose pretending to perform the operation |
| Independently useful processing for both people and agents | Versioned Python core and CLI in the public toolkit's Python tools area |
| Related installable workflows sharing dependencies or update needs | Plugin, generated from canonical Skills/resources |
| Native structured discovery, guarded client access, resources or notifications | Thin MCP adapter around the same core when the client needs that capability |
| Selection and distribution of Plugins | Marketplace catalog, not an additional executable core |

Prefer an existing compatible command, API or supported Plugin reference. A one-off command or ordinary semantic judgment does not automatically need a Python package. Keep a Skill-specific helper local until independent use or repeated callers justify a shared API. Do not move working code merely to match this table.

## Keep one source and usable boundaries

- Public portable source belongs in `codex-toolkit`; private `codex-setup` owns personal configuration and machine installation choices. Inspect the actual migration state before changing an owner. Do not require a private checkout or client-cache absolute path at runtime.
- Keep independently runnable cores free of Codex configuration, accounts and MCP imports. CLI and MCP call the same versioned API; preserve existing package identities and compatible callers. Give the adapter its own authentication, allowed roots, limits and structured errors.
- Use supported references first. Self-contained distribution may generate a mirror with source version/revision, file hashes and redistribution authority. Regenerate it from the owner; never edit a generated Skill copy independently or enable duplicate direct/Plugin sources.
- Keep executable dependencies in the owning package/setup requirements. Declare supported Python/OS/architecture and verify actual support. Do not bundle credentials, local state, downloaded runtimes or optional dependencies into every Plugin.
- Standalone Python tools may include `pyproject.toml`/requirements, README, CLI help, examples and focused `docs/` or `references/` for API/data formats and troubleshooting. Keep dependency declarations authoritative in their actual owner, distinguish required/optional or platform-specific extras, and link detailed information instead of copying it into every Skill. Do not create empty directories or require a Skill for ordinary CLI use.
- Secrets stay outside source and artifacts. Preserve third-party licenses and attribution. Reading a private dependency does not authorize redistribution.

## Language and context budget

Global/general guidance uses concise Taiwan Traditional Chinese. Project root/nested instructions, roles, Skill instructions/references and internal usage guides use concise English. User-facing reports and personal README use Taiwan Traditional Chinese unless the user/repository specifies otherwise. Preserve identifiers, parser vocabulary, quotations, legal text and intentionally localized templates/output.

The following are local drafting guides, not product limits, acceptance quotas or reasons to remove a necessary rule. Count English prose by words, Chinese prose approximately by Chinese characters, and separately inspect actual UTF-8 bytes/tokens. A shorter file does not itself prove better reliability, usage or speed.

| Loaded material | Practical drafting guide |
|---|---|
| Skill description | Usually 20-50 English words, front-load purpose and trigger; the standard permits at most 1024 characters |
| New focused `SKILL.md` body | Usually 200-800 English words; a tiny workflow can be shorter, complex workflows keep necessary boundaries and route conditional detail |
| Conditional reference | One subject, often 300-1500 English words; add navigation/search hints when it grows, split by real use case rather than a quota |
| Root/nested project instructions or role delta | Usually 100-600 English words, recording durable facts/constraints absent from an inherited layer |
| A new global/general instruction section | Usually 100-400 Chinese characters; merge inherited duplicates instead of repeating the full workflow |

The Agent Skills standard recommends an entrypoint below 500 lines and 5000 tokens. Treat these as upper guidance, not targets or evidence that every line was read. Keep trigger, authorization, essential inputs, stop conditions and acceptance easy to find. Link conditional references directly from the entrypoint; do not default-load all references. Before changing an established large Skill, inspect its callers and unique decisions, not just length.

Codex instruction discovery has a configurable combined byte cap, 32 KiB by default. Check the actual applicable chain and configured limit, including inherited instructions. Keep common rules short and conditional details outside that chain; do not raise the cap automatically or claim a character count equals tokens.

## Add or revise safely

1. Identify the requested outcome, actual users/callers, existing capability, source owner, authorization, inputs/outputs and acceptance. Check current files, metadata and concurrent differences; add only a missing capability or demonstrated correction.
2. Select the narrowest maintained unit above. Keep discovery descriptions discriminating; supply an explicit loading condition for a new reference. Instructions should change decisions, not repeat general model knowledge or project rules.
3. For executable work, preserve explicit inputs, bounded output/errors/exit codes, dry-run or preview when useful, overwrite/hash guards and cleanup of owned resources. Windows/macOS paths and platform differences belong in the relevant implementation/setup, not hardcoded personal paths in portable guidance.
4. When the public API, distribution payload or behavior changes, update its actual version and callers according to the package's compatibility/release policy. Skill, Plugin, core and release versions are distinct. Never equate a metadata bump or working-tree snapshot with a release.
5. Start with readback, metadata, references and relevant syntax. Changed behavior needs targeted fixtures/tests or a real bounded operation. Check CLI help/JSON/exit behavior and core-to-adapter compatibility when affected. Cross-platform source checks do not prove native execution.
6. For a changed Skill, examine an explicit request, a realistic implicit request and an adjacent negative case when useful. Record design/manual review separately from actual model execution. Expand checks only for remaining concrete risk or required release gates.
7. Synchronize only affected, already-authorized installed owners and teaching references. Preview/recheck conflicts, preserve backups and compare content/hash after apply. Use native Plugin management; preserve unrelated settings, disabled states and installations.
8. Report changed files and actual source, package/build, installation, authentication, client discovery/reload and successful-use results separately. Include necessary failures, unverified scope and next action. Do not publish, install a new group or contact an external service just because a reference mentions it.

## Evidence behind this design

- [OpenAI Skills](https://learn.chatgpt.com/docs/build-skills): focused descriptions, instruction-first design and conditional resources; the initial discovery list and a selected Skill body have different budgets
- [OpenAI AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md): discovery hierarchy and configurable combined byte limit
- [OpenAI Plugin packaging](https://developers.openai.com/plugins/build/plugins): portable payloads and Git/local marketplace sources
- [Agent Skills specification](https://agentskills.io/specification): metadata limits, scripts/references/assets and progressive disclosure
- [Anthropic engineering case](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills): executable helpers and task-dependent disclosure
- [Community reading observations](https://www.reddit.com/r/codex/comments/1t1rbqt/codex_may_only_read_the_first_220_lines_of_a/): reported partial reads in particular sessions; this is an anecdotal failure mode, not an official 220-line cap or a cross-model benchmark

Sources checked 2026-10-07. Numeric drafting ranges above are local maintenance choices. Recheck current documentation when host discovery, metadata/schema or executable integration changes.

## Version and publication decisions

Follow the component's established version scheme and current official platform rules. SemVer describes public compatibility, not a release schedule: breaking interfaces require major, compatible features minor, compatible fixes patch; define an explicit policy for pre-1.0 stability. Use package-native version syntax, including Python's version rules. Skill, Plugin, core and aggregate release versions are independent. Do not bump every component for unrelated CI or documentation changes.

Keep publication authorization separate from version edits, preparation and installation. If the user defines CP as commit/push, it does not authorize a Tag or Release. Apply CPR only through the actual project's release policy; documentation-only repositories may publish through a branch instead. Community examples inform cadence and communication, not mandatory release branches or automatic publication.

For an authorized release, inspect relevant README/version/license/package metadata, notes, required checks and artifact inputs. Route distribution validation to packaging-acceptance and legal changes to license-maintainer when needed. Optional SECURITY, CONTRIBUTING, CODE_OF_CONDUCT, templates, citation and changelog files depend on audience and maintenance needs; GitHub's community checklist is not a universal Release gate. Preserve verified legal notices and material operating limitations. Recheck platform documentation before changing release automation or settings.


For suspected secret exposure or maintenance of cleanup guidance, read [sensitive-data removal](sensitive-data-removal.md). Keep incident execution separately authorized; normal component maintenance does not authorize history rewrites.
