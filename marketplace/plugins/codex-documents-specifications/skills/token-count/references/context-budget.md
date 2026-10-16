# Context budget mode

Use for an environment/instruction budget. Python 3.11+ and tiktoken are required. The helper dispatches `context` to the same versioned Python Tools core distributed in the Plugin.

```text
python <skill-directory>/scripts/count_tokens.py context --project <directory>
python <skill-directory>/scripts/count_tokens.py context --project <directory> --instruction <referenced-AGENTS.md> --active-skill <SKILL.md> --tool-schema <selected-tools.json> --output <new-report.json>
```

- `--codex-home` selects the local configuration and defaults to CODEX_HOME or the user's .codex directory. Read only the selected local configuration, instruction files, Skill metadata and supplied content. Session logs, network traffic and account usage are separate inputs/workflows.
- Global discovery selects the first nonempty AGENTS.override.md or AGENTS.md. Project discovery walks Git root to working directory, choosing one instruction file per directory with override/fallback precedence and the configured combined byte budget. Supply explicitly referenced parent/private instructions with repeatable `--instruction`; file paths are deduplicated.
- Skill discovery renders name, description and path from local/system/project Skills and each Plugin's latest cached version. Respect explicit disabled Skills/Plugins. `--skill-root` adds a selected Skill directory tree. Full Skill bodies enter through repeatable `--active-skill`; role bodies through `--active-role`. Configured role descriptions and the local memory_summary.md are separate rows.
- `--tool-schema` supplies selected tool-definition text/JSON and replaces per-tool estimates. Select the current exposed tool surface; an entire deferred registry is its own expanded scenario. `--builtin-tools` defaults to a 10-tool scenario at 500 tokens per tool; `--mcp-tools` adds a selected scenario at 550–1400 tokens each. Enabled local MCP server declarations add 200–500 tokens each without connecting to servers.
- `--content` adds selected task text, history exports or reference documents. Input files remain local. Exports use a new `--output` path; --json or a .json suffix selects JSON.

The packaged `context_estimates.json` records source dates, URLs and numeric assumptions. Its system baseline is the 8000-token built-in-system example from the community guide updated 2026-10-15. The tool/server ranges come from the linked community references checked 2026-10-16. `--profile` selects an explicitly supplied alternative. Profiles are data; require nonnegative ordered numeric ranges.

Report category counts and the estimated total with the selected encoding and source links/dates. Retain detailed source paths and calculation methods in JSON. General reading/editing does not schedule or automatically repeat this report.
