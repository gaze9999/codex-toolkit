# Host and custom-element project rules

<!-- Example only. Replace placeholders with verified project facts before use. -->

## Repository boundaries

- Modules: backend in <backend-directory>, legacy web Host in <host-directory>, migrated custom elements in <elements-directory>. Confirm actual frameworks, runtimes, package managers and configured targets before adopting this example.
- The Host owns session, navigation, permissions, loading and deployment assembly. Custom elements own migrated transaction UI. Keep coupled behavior and checks with one owner inside the authorized module.
- Frontend scope does not authorize backend changes. Unresolved specifications block only dependent behavior; local UI, state, validation and fixtures do not prove formal API, persistence, permission or workflow support.
- API payloads, selectors, element properties/events, routes, bundles, output paths and shared assets are public boundaries. Cross-owner changes require confirmed specifications, authorization and checks for affected owners.
- Preserve unrelated behavior, user work and concurrent changes. Follow the nearest nested instructions for module runtimes, conventions and commands.

## Conditional sources and coordination

- Resolve the current feature guide and matching Markdown extracts from task context and source provenance. Read relevant sections first; inspect originals or screenshots for visual evidence, gaps, ambiguity, stale coverage, conflicts or an explicit original-source request. Originals and confirmed decisions retain authority.
- Use a configured project routing guide only when task branching or delegation is relevant. Main retains decisions, necessary direct implementation, integration and final acceptance; delegate only authorized, independently verifiable slices.
- For progress, history or document maintenance, read the [records guide](.codex/agent-guidance/records.md). Resolve actual destinations from the project or task; this example creates none automatically.
- Inspect ignored governance files directly and verify their availability in another checkout or worktree. Local exclusion rules are not automatically portable.

## Git conventions

- Titles default to [scope] type: [ticket] summary, omitting unconfirmed tickets. Derive lowercase scope from the affected feature or owning module, using the repository folder for repository-wide work.
- Incompatible changes use type! and a BREAKING CHANGE footer. An explicit task requirement or verified hook/template takes precedence.
- Resolve the actual target/base branch and required gates. Text generation does not authorize commit, push or release; follow effective user authorization.

## Verification and reporting

- Start with the smallest sufficient existing checks for changed behavior and module/interface dependencies. When failure or insufficient evidence leaves a concrete risk, expand gradually, stating the missing evidence and added scope. Retain required gates.
- Each delivery or phase report includes actual test/check results and coverage, distinguishing passed, failed, blocked, not run and unverified. Explain checks that did not run or apply; continue independent checks when dependencies or environment access block others.
- Isolated or browser checks cover only exercised behavior. Keep Host, authentication, API, persistence, permission, workflow and end-to-end evidence separate, with reproducible commands or artifacts when needed.
- Report progress, every changed file and its scope, traceable issues and remaining acceptance directly in conversation. Recommendations do not expand authority; create a separate report only when requested.
- Before sharing guidance, remove organization/project identifiers, private paths, endpoints, credentials, customer data and transaction-specific decisions.
