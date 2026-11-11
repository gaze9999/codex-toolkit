# Plugins

Plugins are assembled from `skills/` workflows, `plugins/catalog.json` source mappings and `plugins/<id>/plugin.json` metadata. `marketplace/plugins/` holds the generated self-contained packages; install them through the [marketplace](marketplace.md). Every canonical Skill has exactly one bundle owner. Each installer registers the MCP connectors those Skills call with their own setup tool.

## Routing by task domain

Read the project's `AGENTS.md` first; when it names plugins, use those. Otherwise pick the row whose domain matches the task, load one Skill at a time and its references only when that flow needs them. Enable the whole plugin: it carries the Skills and the connectors they call. Connectors still need device runtimes, data roots and login on the target client.

| Task domain | Plugin | Skills | Optional runtimes |
|---|---|---|---|
| Agent instructions, prompts, Markdown goals/plans, review and test briefs | `codex-agent-workflow` | `agent-governance`, `coding-prompt`, `task-routing`, `task-guide` | none |
| Local agent activity counts, artifact inventory and cleanup, RTK | `codex-agent-operations` | `local-activity-query`, `agent-artifact-audit` | `rtk`; `agent-artifact-audit` native MCP |
| Semantic ranking and bounded typed evaluation | `codex-evaluation` | `jev-evaluation`, `decisions-evaluation` | `jev`; standalone `codex-decisions` |
| Local document extraction, specification and doc maintenance, PDF/DOCX/Markdown deliverables, README and license, token counts | `codex-documents-specifications` | `context-brief`, `doc-updater`, `local-document-processing`, `token-count`, `readme-maintainer`, `license-maintainer`, `document-production` | `local-documents`; token counting needs Python 3.10+ with `tiktoken` |
| Proofreading zh-TW, English and Japanese prose | `codex-multilingual-proofreading` | `multilingual-proofreading` | `textlint`, `cspell` |
| Test selection, environment comparison, recorded validation evidence | `codex-environment-evidence` | `validation-evidence-review`, `test-strategy` | `workspace-inspection` |
| Plugin and application packaging, release acceptance | `codex-packaging-acceptance` | `packaging-acceptance` | none |
| Research synthesis with web search, page extraction, papers, communities and library docs | `codex-research` | `research-learning-synthesis` | `tavily`, `exa`, `firecrawl`, `arxiv`, `reddit`, `context7` |
| System boundaries, data ownership, interfaces and architecture trade-offs | `codex-system-design` | `system-design-analysis` | none |
| Angular, React and Vue interfaces with UI/UX, i18n, accessibility and browser checks | `codex-frontend-engineering` | `angular-development`, `angular-member-order`, `react-development`, `vue-development`, `ui-ux-design`, `internationalization-engineering`, `accessibility-engineering`, `playwright-cli` | `playwright`, `serena`, `edge-devtools`, `chrome-devtools`, `spartan` |
| Data visualization, 2D motion and Three.js inside a web project | `codex-visual-development` | `data-visualization`, `visual-development` | `echarts`, `excalidraw`; standalone `codex-visual-runtime` |
| Editorial illustration, Stable Diffusion and ComfyUI workflows | `codex-creative-imaging` | `editorial-illustration`, `comfyui-workflow` | none |
| Unity projects and game economy balance | `codex-game-development` | `unity-development`, `game-balance-simulation` | none |
| LLM, agent, tool-calling, RAG and embedding applications | `codex-ai-engineering` | `ai-application-engineering` | `openai-docs` |
| AdGuard, uBlock, DNS and hosts filter rules | `codex-network-filters` | `network-filter-rules` | none |

`runtime_profiles` name optional tools the installer's setup manifest provides; runtimes, MCP registration and accounts are configured per task. Document and workspace MCPs use the versioned core in `python-tools/`. Plugin websites point to the [GitHub source](https://github.com/gaze9999/codex-toolkit).

## Skill boundaries

Choose the entry by actual purpose; references load only when that flow needs them. Installed count, discovered Skills and Skills used in one task are separate checks. When trimming or updating, compare matching tasks and versions with [instruction utility evaluation](../skills/agent-governance/references/component-authoring.md#evaluate-instruction-utility); packaging checks verify hashes, the target client verifies loading and behavior.

| Need | Entry and condition |
|---|---|
| Find existing extracts, verify source hashes | `$local-document-processing` [read-only source matching](../skills/local-document-processing/references/source-matching.md) |
| Convert documents or edit a selected Markdown file | `$local-document-processing`, with source, output and write authorization checked separately |
| Count tokens, compare encodings, export statistics | `$token-count` on the selected text and encoding, default `o200k_base`; API credentials, account usage and context that was not supplied are out of scope ([context estimates](../skills/token-count/references/context-budget.md)) |
| Update identified docs from implementation changes | `$doc-updater`, with change evidence and concrete targets |
| Compare sources with installed Skills or runtimes | `$validation-evidence-review` [environment comparison](../skills/validation-evidence-review/references/environment-comparison.md), no synchronization |
| Review existing test, build or UI evidence | `$validation-evidence-review`, keeping source versions and coverage, no reruns |
| Select or run the checks this change needs | `$test-strategy` within the authorized scope; performance and stream cases in [measurement guidance](../skills/test-strategy/references/performance-and-streams.md) |
| UI sources, templates and detail acceptance | `$ui-ux-design` [design foundations](../skills/ui-ux-design/references/design-foundations.md), [detail review](../skills/ui-ux-design/references/detail-review.md); Angular style in [angular-style](../skills/angular-development/references/angular-style.md) and [code maintainability](../skills/angular-development/references/code-maintainability.md) |
| Multilingual program behavior / assistive technology behavior | `$internationalization-engineering` / `$accessibility-engineering`; prose quality stays with proofreading, automatic scans do not prove full acceptance |

Platform or SDK Skills follow the project's actual stack and selected tools. Generic needs such as agents, React, environment variables or charts never decide a provider, framework, hosted service or account by themselves; third-party plugins keep their vendor update sources.

## Catalog fields

| Field | Meaning |
|---|---|
| `id` | Bundle source ID; the manifest name is `codex-<id>` |
| `status` | `ready` assembles; `blocked` needs `blocked_reason` and explicit selection reports it |
| `skills` | Canonical Skills in this bundle; may be empty for MCP/app-only bundles |
| `resources` | `{source, target}` directory mappings into the package |
| `components` | `{source, target}` single-file mappings |
| `runtime_profiles` | Optional tool names the installer's setup manifest provides |

Human-facing `description` and `extensions.com.openai.interface.displayName` are zh-TW: a four-character title and one sentence on what the bundle does. This index stays concise English. Optional components include a portable `mcp.json`, registered app mappings, hooks and assets; entry points come from `extensions.com.openai`.

The checker rejects path escapes, links, case collisions, credentials or private keys, and unlisted relative references. VCS, venv, cache, test output and temporary files stay out of packages.

## Checks and build

The maintainer's generator validates mappings and references, then writes `marketplace/plugins/` with a `source-manifest.json` per bundle. Development snapshots mark `source_state: working-tree`; published content comes from clean, committed, tracked sources.

A changed payload needs a new `plugin.json` version: native marketplace updates compare versions only, so the generator stops when a bundle's files differ from the generated copy while its version is unchanged.

## Updating installed plugins

Check the marketplace `source_type`, installed IDs and enabled state first; Git and local sources use different update entries.

A GitHub marketplace serves published content: update the marketplace, then each selected plugin. Keep disabled state and custom settings through the native management interface.

```text
codex plugin list --marketplace codex-toolkit --json
codex plugin marketplace upgrade codex-toolkit --json
codex plugin add codex-agent-workflow@codex-toolkit --json
```

A registered local marketplace takes a working-tree snapshot through the maintainer's setup tool. First installs use the [marketplace commands](marketplace.md). Keep backups and other plugin settings before updating, verify content and enabled state afterwards, then reload the client and confirm Skill discovery.

Retired bundles (`jev-evaluation`, `decisions-evaluation`, `local-activity`, `project-documentation`, and the former standalone `skill-*` packages) are removed through each client's native plugin management.

The activity summary reads only a running HTTP loopback monitor; periods are `1h`, `24h`, `7d`, `all`, unknown values are null, responses are metadata only with size and connection limits ([activity Skill](../skills/local-activity-query/SKILL.md)).
