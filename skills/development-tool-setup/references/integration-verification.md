# Integration Verification



Apply only the checks for the selected capability and provider. The named examples below preserve implementation-specific boundaries, they are not a fixed provider list for general agent workflows.

## Execution route and permission diagnosis

Read this section when the selected tool is denied, appears unavailable or behaves differently between clients. Record the actual local/cloud execution location, shell/browser/App/MCP route, relevant policy and the observed error or result before choosing a repair. A connection, credential or network failure in one route does not establish failure in another.

- Separate command sandbox reachability from approval policy. For command networking, check both the network grant and applicable proxy enforcement. Enabling a proxy does not enable command network access, and a network grant alone does not establish an enforced domain policy.
- Command network controls do not by themselves disable hosted search, Apps, MCP connections or browser activity. Those routes have their own client, account, capability and managed restrictions. A successful alternative read proves that route only and does not authorize bypassing the failed route's policy.
- Test only the selected authorized capability. Preserve effective permissions, authentication and providers while diagnosing, and distinguish a local command result from a remote service or another client's result. Change policy or account settings only within a separate, explicit scope.

Source checked 2026-10-21: [OpenAI approvals and network isolation](https://learn.chatgpt.com/docs/agent-approvals-security). Resolve current client/build and execution policy before applying configuration examples.

## Selected integration checks

### Project memory compatibility

When ChatGPT Work is missing inside a Project, identify the product/interface, account plan, whether the Project is shared, its effective memory mode and any pending setting transition. The [Projects documentation](https://help.openai.com/en/articles/10169521-projects-in-chatgpt), checked 2026-10-21, says Work is unavailable with project-only memory; shared projects use that mode and cannot switch to default memory. This is a product compatibility condition, not evidence of a broken local MCP or missing package. Do not generalize it to local Codex repositories or unrelated tool failures.

Preserve the approved memory/data boundary. Do not switch memory mode, move private context outside the Project or reinstall tools just to expose Work. Confirm the visible entry and effective setting in the selected account when access is available; otherwise report the unverified account condition and retain an explicit handoff in its approved location. A source check establishes the documented condition only, not account rollout, successful execution or usage savings.

### Provider checks

- Distinguish registration, package availability and actual use. `manual_verification_required` requires the remaining browser/app/authentication checks; an existing file or parsed config does not establish client reload.
- Context7: for MCP, verify client tool discovery and one public library resolution/document query after reload. For an existing CLI, verify `ctx7 --help`, resolve the public library ID, then query the intended documentation version. A package or HTTP endpoint check alone leaves the selected query path unverified; ordinary docs lookup does not authorize setup, OAuth or Skill installation.
- Firecrawl: distinguish App/connector and standalone MCP configuration, discovery, authentication and successful use. Verify the selected route with a bounded public read when that capability needs acceptance; an account/credit response proves account access, not search, scrape or crawl behavior. Check current plan/limits for a budget-sensitive job, preserve other providers and report each route's unverified scope. Do not upload a private local file to verify hosted parsing.
- Playwright: verify the selected CLI/browser version and authorized local/dev page. Use a unique task session for every CLI call in the same working directory, read a snapshot before interaction, then verify DOM/UI, console and relevant request results. Use the available playwright-cli Skill for exact CLI operations, and the selected server's schema for MCP. Close only this task's session; keep private URLs, browser data and company content within the approved environment.
- Chrome DevTools: verify the selected Chrome session and authorized trace/network/console behavior, retain the preset's isolated profile and disabled usage statistics/CrUX lookup unless changed explicitly. A trace demonstrates the measured route and state, not all UI behavior.
- Serena: verify the intended active project and actual language-server support before symbol/reference lookup or edits. On Windows, verify the installed dashboard interface: hiding or closing an app window can retain its tray viewer. Use a supported single tray manager or browser interface when authorized, preserve per-task server isolation and reload only the owning client after its work is saved. Do not index adjacent repositories automatically, enable hooks, or create a competing memory workflow as part of installation.
- Lifecycle diagnosis: distinguish task completion, browser close, MCP connection/server shutdown, native viewers and intentional monitors. Verify PID/parent creation times, owning client and relevant ports before calling duplicates stale. Count launcher/venv redirects separately. Release temporary clients and owned sessions in success, failure and cancellation cleanup; preserve active concurrent work and use native shutdown before any narrowly scoped forced termination.
- Proofreading: verify one expected error and one valid sample for the selected language, preserve Japanese punctuation and literal source material, and confirm whether fix results are returned or written. Keep language configurations separate and report unsupported grammar capabilities.
- RTK: retain the original output when the filter loses necessary evidence. Judge benefit using completion and total task usage, not output compression alone; enable hooks or telemetry only within their separately authorized scope.
- RTK MCP filters existing text or explicitly allowed logs through `rtk pipe`; retain the originating exit code separately from filter success. It does not execute project shell commands. cmux adapter exposes only typed inspection and workspace/pane creation or focus, and retains cmux's socket access policy.
- Hosted MCPs: save only environment-variable names for credentials, complete OAuth in the client's supported flow, then verify tool discovery and a safe read. Registration and credential presence alone leave authentication and quota unverified. `manual_setup_required` or blocked plans require the stated app/account/source setup; do not bypass them with an all-tools install.
- Desktop/context/workbench tools: verify app launch, provider authentication and the selected context/session/worktree workflow on the target platform. App discovery or a package-manager result alone leaves those behaviors unverified.

Report the selected tool, actual checks, configuration/backups changed and remaining boundaries. Updating this Skill or setup source does not authorize unrelated runtime installation, remote publication or provider changes.
