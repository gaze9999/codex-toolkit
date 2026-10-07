# Maintained Setup

For removing one MCP, read `docs/setup/cli.md` from the verified setup. Use `launch-cli.cmd uninstall` on Windows, `sh launch-cli.sh uninstall` on macOS/Linux or the installed wheel's `codex-mcp-uninstall`. Preview one registration first. Package removal is explicit and rejects shared/unmanaged runtimes, preserve dictionaries, user data, credentials and client-managed plugins. Do not force-stop concurrent sessions or infer OAuth revocation from unregistering.



Locate a trusted `codex-setup` checkout or an explicitly installed `codex-tool-setup` wheel; verify its instructions, metadata, scripts and requirements. Read `docs/tools/development.md` for development tools, `docs/tools/catalog.md` for the selected MCP/connector and `docs/setup/packages.md` for wheel installation. The checkout or installed wheel owns `mcp/tools/development-tools.requirements.json`, dependency recipes, versions and installers; retain one source instead of copying them into this Skill or framework guidance.

Run from the verified setup root, substituting the selected tool name:

```text
python mcp/scripts/check_development_tools.py --tool <selected-tool>
python mcp/scripts/install_development_tool.py --tool <selected-tool>
```

Replace the placeholder with a tool name from the verified catalog, and select `--interface mcp` only when that tool supports the requested mode. The checker reads prerequisites, the installer previews one tool and its missing prerequisites. It accepts exactly one `--tool`. Use `--apply` after reviewing the source, version/channel, scope and purpose, use `--yes` only when that exact installation is already authorized. Preserve existing compatible runtimes and MCP providers, and retain the installer's conflict checks and backups.

An installed setup wheel provides `codex-mcp-setup`, `codex-tool-setup` and `codex-tool-check` with the same workflow. The portable installer ZIP includes CMD/shell entries and a wheel directory; select one tool and verify its version and checksum against `mcp-release-manifest.json`. A separate directory can use `--wheel-dir <absolute-path>`. Respect each Python server's declared minimum version and its isolated environment; third-party wheels do not supply account credentials, notebooks or native applications.

For a user-operated installation prefer the setup's `launch-cli.cmd mcp` on Windows or `sh launch-cli.sh mcp` on macOS/Linux. The CMD entry invokes the existing Windows PowerShell entry with session-only RemoteSigned; retain Group Policy precedence and persistent policy values. Both platform entries use the shared Python installer. It selects one category/tool, previews prerequisites and scope, then guides registration, supported OAuth login and verification. `--guided` uses the same Python workflow; `--list` lists names. Keep the structured preview for agent automation. Manual app/account/permission prerequisites remain visible rather than being bypassed by the wizard.

When choosing a computer-purpose subset or updating installed tools, read `docs/tools/workflows.md` from the verified setup. Profiles filter the menu; they do not install a group. The update entry checks one installed tool's reviewed channel and preserves configuration and language rules. Review runtime requirements, shared-package impact and previous versions before applying; use noninteractive updates only within existing authorization. Keep project-matched libraries, hosted provider updates, native apps and client-managed plugins separate from setup-managed packages.

For UI/UX setup, read `docs/tools/workflows.md` for the selected research, design or accessibility capability. Distinguish a research source or component library from an MCP. Verify design-file access and a live plugin connection where needed; a free extension does not establish access to a paid MCP server.

For game-economy tooling, read `docs/tools/workflows.md` from the verified setup. `--profile game` selects a relevant menu, not a package bundle to install together. Calculation and property-testing libraries belong in the selected game/simulation environment and its dependency lock; reviewed single-package requirements are starting points for new environments, not permission to replace project versions. Check official wheels against OS, CPU, Python and ABI. Keep browser products, native calculation apps and actual MCPs distinct, and verify model visibility before sending a private economy to a hosted design product.

Resolve CLI/app versus MCP explicitly. Context7 offers CLI documentation queries and hosted MCP; preserve an existing compatible entry, and inspect the official CLI setup writes and authentication before using setup. Selected hosted services already use MCP; Playwright supports both official MCP and CLI, RTK/cmux use this setup's narrow adapters, and RepoPrompt uses its native Mac MCP. Confirm platform support before bootstrapping. A manual connector, account setup, API source or Skill is not an automatically installable MCP; report the catalog's exact remaining setup instead of inventing a server or endpoint. Prefer an existing compatible authenticated plugin/connector before registering a duplicate. For Angular use the target project's matching CLI and its actual MCP support, not a global latest version.

For search/collection, choose the coverage, freshness and original-content access needed for the task, and avoid adding an overlapping provider when the existing one is sufficient. Feed aggregation needs explicit sources. For life services verify the selected account and permissions. For charts/documents reuse available tools first, local rendering may still fetch resources, and hosted rendering sends supplied data to that service. For notebooks/databases, select a development environment and scope before enabling code execution or writes. Domain sources keep their dates, versions and provenance, financial forecasts need temporal backtests and uncertainty, medical sources need applicable evidence, and a document search server does not supply market quotes. Payment API Skills are setup candidates, real payments, deletes and account changes need authorization for that action.

For proofreading setup, read `docs/tools/proofreading.md` from the verified setup. Select the intended language profile independently, preserve project dictionaries and modified local rules, and separate spelling from grammar and semantic review. A CLI checker is not automatically an MCP. A grammar service needs its actual runtime or account/data boundary, not a guessed MCP endpoint.

The Python entrypoints need Python 3.11+. If it is missing, the setup's `launch-cli.cmd tool <name>` on Windows or `sh launch-cli.sh tool <name>` on macOS/Linux previews the bootstrap; their Apply option asks before installing Python and then the selected tool. Prefer an approved existing interpreter. Check the actual script help and platform support before applying, and keep browser installation explicitly selected.

If neither the checkout nor installed setup wheel is available, continue diagnosis with installed tools and the selected tool's current official documentation. Identify the approved setup location or use an individually reviewed official installation; do not assume a personal path, clone an unrelated repository, or expand into all-tool installation.

## Local management interface

Use the maintained terminal CLI: `launch-cli.cmd`, `launch-cli.ps1` or `sh launch-cli.sh`, or the installed wheel's `codex-setup`. Read `docs/setup/cli.md` for the selected agent, Skill, Plugin or tool operation. Categories and profiles filter choices; they do not authorize a group installation. Python bootstrap follows the selected CLI entry's preview and existing authorization.

For owned Plugin updates, read `docs/plugins.md` and preview `launch-cli.cmd plugins --sync-installed` (or the corresponding shell entry). This uses canonical payloads, preserves registered Plugin identities and delegates installation to the supported native Codex CLI. Use the reviewed `--apply` scope only when authorized. Preserve client-managed caches, other marketplaces, accounts and runtimes. ChatGPT Web profiles remain copyable sources applied in their account/Project UI.

For a failed validator, identify its actual interpreter, version, required modules and exit code. Reuse a compatible installed tool environment; declared requirements or the App's bundled Python do not prove that environment has loaded its dependencies. Report a missing validator separately from a checked source defect. Do not install or change dependencies merely to clear a prose-check gap without authorization.
