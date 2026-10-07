# Documentation impact and target selection

Read this reference only when evidence strength, documentation impact or target selection is unclear. [SKILL.md](../SKILL.md) owns activation, source authority, authorization, local updates and history rules. For an explicitly authorized Notion update, use the [reader and writer contract](notion-sync-reader-writer-contract.md).

## Evidence strength

| Evidence | Confidence | Rule |
|---|---|---|
| Diff hunks + changed files | Highest | Supports implementation-change claims; runtime, deployment and acceptance claims still need their own evidence. |
| PR / commit + changed-file list | High | Use commit text carefully; inspect relevant files when available. |
| Release or migration note tied to code changes | Medium | Mark unsupported details as unresolved. |
| User-provided implementation summary only | Lower | Label updates as summary-based and avoid claiming direct verification. |

## Impact classification

Use `yes`, `maybe`, or `no` for documentation impact.

### `yes`

Use `yes` when the change affects documented contracts or user-observable behavior:

- public API, endpoint, SDK, CLI, event, schema, or integration contract
- environment variable, config key, setup command, build command, deploy step, or migration path
- user-facing UI behavior, validation, permissions, copy, state, error, or workflow
- breaking change, compatibility change, limitation, deprecation, or operational risk

### `maybe`

Use `maybe` when the file path or diff suggests a possible doc impact but the behavior is not clear:

- internal module restructuring that may affect architecture docs
- UI refactor touching labels or state names
- dependency upgrade with possible setup or compatibility impact
- generated type changes without visible source context

### `no`

Use `no` when the change is unlikely to require docs:

- tests only
- formatting only
- lint-only changes
- internal variable rename with no public contract impact
- generated artifacts with no semantic change
- local tooling changes not exposed to users or maintainers

## Documentation target selection

Choose the smallest documentation surface that keeps knowledge aligned.

| Change type | Likely target |
|---|---|
| user-facing feature | README, docs, memo, Notion page only if requested |
| public API change | API reference, Codex context brief, changelog |
| config / env change | setup docs, deployment docs, README |
| breaking change | changelog, migration guide, release note |
| internal architecture change | architecture doc, Codex context brief, memo |
| bug fix with user-visible effect | changelog or memo when relevant |

Create a new documentation surface only when the user requests one or no existing target can represent the necessary update. Prefer patching the smallest existing section.
