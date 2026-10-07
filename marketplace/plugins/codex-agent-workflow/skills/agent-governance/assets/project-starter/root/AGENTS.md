# <Project> Agent Rules

<!-- Replace placeholders with confirmed project facts before use. -->

## Project boundaries

- Type and purpose: <confirmed project type and purpose>
- Ownership: <modules/packages and actual paths>
- Shared interfaces: <API, schema, CLI, file formats or other public boundaries>
- Cross-owner changes follow <actual coordination/authorization rules>

## Task and sources

- Understand the purpose and delivery. Resolve scope, feasibility, necessary sources/evidence, verification and reporting for the situation; examples are not a fixed checklist.
- Track this execution's original request and every later steering item in conversation/task context. Reconcile changed decisions/results and retain valid work and unfinished items through interruptions or compaction. Write progress files only when explicitly requested or required by applicable guidance.
- Check runtime, conventions and verification in the nearest nested `AGENTS.md` for the target path.
- Read `.codex/agent-guidance/tasks.md` only for task routing/delegation when that file exists.
- Select available tools by the required capability, live interface and data boundary. Follow the owning Skill for operations and the current authorization for missing-tool installation.

## Git conventions

- Commit and PR titles default to `[scope] type: [ticket] summary`; omit `[ticket]` when no ticket is confirmed. Use `[scope] type!: [ticket] summary` and a `BREAKING CHANGE:` footer for incompatible changes. An explicit task requirement or verified repository hook/template takes precedence.
- Derive lowercase scope from the affected feature/transaction directory in the actual diff, keeping helper/test subdirectories under that feature scope. For shared work use its owning module; for repository-wide work use the repository folder. Split unrelated purposes rather than inventing a combined scope.
- Resolve the actual target/base branch, ticket and applicable checks from this project and the task. Follow inherited Git authorization and evidence rules for Desktop, CLI and MCP operations.

## Verification and reporting

- Focused checks: <applicable commands and changed behavior/dependencies>. Start with the smallest sufficient scope; when checks fail or evidence is insufficient, expand gradually around the unresolved risk and state the missing evidence and added scope. Retain required gates.
- Report in conversation text: progress against original requirements and effective steering, deviations, every changed file and its scope, actual test/check results and coverage in each delivery or phase report, and remaining acceptance. Distinguish passed, failed, blocked, not run and unverified, explaining checks that did not run or apply. Add useful recommendations only when relevant; do not create a separate report document unless requested. Keep issues traceable to sources, state, impact and next action.
