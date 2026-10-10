---
name: ui-ux-design
description: Design or review UI/UX and check rendered interfaces against the original request before delivery. Use for layout defects, misleading displayed data, missing requirements and interaction changes, including UI work without user-provided screenshots.
metadata:
  version: "0.6.0"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# UI / UX Design

Start with the user's task, existing interface, project constraints and the requested deliverable. Analysis or a design reference does not authorize implementation, account changes or publication. Preserve the selected stack, design system and useful existing interactions.

## Check the requested result before delivery

For a detailed review, reported layout/data discrepancy, or user-visible implementation, read [UI acceptance and detail review](references/detail-review.md). Reconcile the original request and still-valid follow-ups, compare each affected requirement with the served interface and its data, then fix and retest discrepancies within the existing authorization. Perform this acceptance pass without waiting for the user to supply screenshots or request a separate review.

Use the available browser capability to operate and visually inspect the affected states, capture and inspect your own screenshots when useful, and supplement them with DOM, console, request and data evidence. A successful build, screenshot creation or plausible mockup does not establish requirement compliance. If the target cannot run or be reached, complete independent checks and identify the unverified requirements and missing runtime evidence.

Jev is optional for semantic ordering of retrieved material or a finite comparison of approved summaries when rules cannot decide it. It does not validate pixels, data bindings or interactions. Keep governing requirements in Main's context and follow the available jev-evaluation Skill's data boundary when evaluation is useful; its absence does not block UI acceptance.

## Work from a representative flow

- Choose a small relevant flow or section first, identify the entry, meaningful outcome, information hierarchy, empty state, failure and recovery. Expand when observed problems justify it, not to redesign every page by default.
- Distinguish observed target behavior, research findings, real product examples and personal reports. Record source date and applicable population/context; popularity and a successful prototype do not prove usability or business improvement.
- Select research, editable prototype, implementation and browser/a11y capabilities from what is actually available. Reuse an authenticated integration and its required Skills; install a tool only for a demonstrated gap within authorization. Keep exact tool recipes in the maintained setup rather than fixing providers here.
- Match component packages to the project's framework/version, license, theme, keyboard/focus and localization requirements. Library adoption and dependency upgrades need scope that includes those changes.

## Verify what users experience

Choose the available browser interface for the real flow. A bounded reproduction can use CLI + a browser Skill when shell access and artifacts are available; use an existing MCP when its client integration or page introspection better fits the task. CLI can retain sessions, so state alone does not require MCP. Follow the selected tool's instructions for unique task sessions, fresh snapshot targets and cleanup, then verify relevant console/request results as well as the rendered UI.

Inspect task completion, labels, validation and recovery, ordering, update/refresh behavior, independent disclosure state, responsive layout and keyboard/focus. Distinguish a visually stretched collapsed card from an actual state change, and keep summary information visible when it is needed before expanding details.

For automatically updated tables or details, use the streaming cases in [detail review](references/detail-review.md#streaming-tables-and-details) to verify record identity, interaction state and the project's selected update policy.

Use the project's existing table/filter/pagination and preference mechanisms when appropriate. Defaults follow the target project's current decisions; preserve valid user overrides. Tags retain readable text and sufficient contrast, and tooltips explain the actual metric or action rather than repeating a label or an unrelated limitation.

Proofread prose by language with available checks and semantic review, preserve original quotations/code and Japanese punctuation. An automatic accessibility scan covers only detectable issues; verify the affected keyboard/focus and task behavior in the served page.

Report the changed flow, evidence, actual validation and unresolved boundaries. Static checks, design rendering and fixture/browser results each prove their exercised scope; do not claim a live account or production flow was verified without observing it.
