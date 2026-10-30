---
name: ui-ux-design
description: Design or review UI/UX and check rendered interfaces against the original request before delivery. Use for layout defects, misleading displayed data, missing requirements and interaction changes, including UI work without user-provided screenshots.
metadata:
  version: "0.7.4"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# UI / UX Design

Start with the user's task, existing interface, project constraints and the requested deliverable. Analysis or a design reference does not authorize implementation, account changes or publication. Preserve the selected stack, design system and useful existing interactions.

## Select sources and component patterns

For specification-driven work, preserve specified copy, validation and failure/recovery behavior. Do not invent messages, business defaults or error handling to fill gaps. Preserve existing compatible safeguards and identify missing decisions; an explicit owner-authorized design exception must remain scoped. Use existing shared capabilities first when they satisfy the specification; adapt only the documented gap instead of changing the requirement to fit a component.

For company/client work, require a specification location or explicit scoped decision for each new/changed prompt's wording and display trigger, including inline errors, alerts/toasts, loading, empty, success and recovery states. Inventory changed static and dynamic messages before delivery and inspect initial, edited, action-attempted and corrected states. A validation rule or backend field does not authorize explanatory copy. Preserve existing compatible data-protection blocks and their visible causes; unspecified copy never authorizes silent failure, truncation or bypassing invalid/overlength checks. Record unresolved wording without inventing replacements. Owner-authorized personal-project design remains outside this restriction.

For design-system selection, accessibility targets or conflicting guidance, read [design sources](references/design-sources.md). Classify the relevant passage and its platform/version before adopting it; preserve confirmed product decisions and resolve affected conflicts explicitly.

For a new design, prototype or unresolved visual/interaction decision, read [design foundations and reference selection](references/design-foundations.md). When the project has no selected system or platform requirement, start with Apple HIG and then Google Material. Existing requirements, platform semantics, accessibility targets and the selected design system govern adoption. Load only relevant passages and official templates; do not replace a theme or copy native units from reference order alone.

For ambiguous component names, interaction design or component specifications/handoff, read [component patterns](references/component-patterns.md). Select semantics, modality, focus/dismissal and positioning separately, then adapt the relevant specification fields to the actual API and task. Existing project docs, galleries and prototypes remain the working entry points.

## Check the requested result before delivery

For a detailed review, reported layout/data discrepancy, or user-visible implementation, read [UI acceptance and detail review](references/detail-review.md). Reconcile the original request and still-valid follow-ups, compare each affected requirement with the served interface and its data, then fix and retest discrepancies within the existing authorization. Perform this acceptance pass without waiting for the user to supply screenshots or request a separate review.

Use the available browser capability to operate and visually inspect the affected states, capture and inspect your own screenshots when useful, and supplement them with DOM, console, request and data evidence. A successful build, screenshot creation or plausible mockup does not establish requirement compliance. If the target cannot run or be reached, complete independent checks and identify the unverified requirements and missing runtime evidence.

Jev is optional for semantic ordering of retrieved material or a finite comparison of approved summaries when rules cannot decide it. It does not validate pixels, data bindings or interactions. Keep governing requirements in Main's context and follow the available jev-evaluation Skill's data boundary when evaluation is useful; its absence does not block UI acceptance.

## Work from a representative flow

- Choose a small relevant flow or section first, identify the entry, meaningful outcome, information hierarchy and specified/existing empty, failure and recovery behavior; record unspecified behavior instead of inventing it. Expand when observed problems justify it, not to redesign every page by default.
- Distinguish observed target behavior, research findings, real product examples and personal reports. Record source date and applicable population/context; popularity and a successful prototype do not prove usability or business improvement.
- Select research, editable prototype, implementation and browser/a11y capabilities from what is actually available. Reuse an authenticated integration and its required Skills; install a tool only for a demonstrated gap within authorization. Keep exact tool recipes in the maintained setup rather than fixing providers here.
- Match component packages to the project's framework/version, license, theme, keyboard/focus and localization requirements. Library adoption and dependency upgrades need scope that includes those changes.

For changed messages, locale switching or localized formatting, use the available internationalization-engineering Skill. For changed semantics, keyboard/focus, errors or assistive-technology behavior, use accessibility-engineering. Load only the affected references and preserve the existing component, data and copy contracts. Retain necessary checks when a companion Skill is unavailable.

## Verify what users experience

Choose the available browser interface for the real flow. A bounded reproduction can use CLI + a browser Skill when shell access and artifacts are available; use an existing MCP when its client integration or page introspection better fits the task. CLI can retain sessions, so state alone does not require MCP. Follow the selected tool's instructions for unique task sessions, fresh snapshot targets and cleanup, then verify relevant console/request results as well as the rendered UI.

Inspect task completion, labels, validation and recovery, ordering, update/refresh behavior, independent disclosure state, responsive layout and keyboard/focus. Distinguish a visually stretched collapsed card from an actual state change, and keep summary information visible when it is needed before expanding details.

For automatically updated tables or details, use the streaming cases in [detail review](references/detail-review.md#streaming-tables-and-details) to verify record identity, interaction state and the project's selected update policy.

Use the project's existing table/filter/pagination and preference mechanisms when appropriate. Defaults follow the target project's current decisions; preserve valid user overrides. Tags retain readable text and sufficient contrast, and tooltips explain the actual metric or action rather than repeating a label or an unrelated limitation.

Proofread prose by language with available checks and semantic review, preserve original quotations/code and Japanese punctuation. An automatic accessibility scan covers only detectable issues; verify the affected keyboard/focus and task behavior in the served page.

Keep the UI review scoped to requirements and the rendered flow.

Report the changed flow, evidence, actual validation and unresolved boundaries. Static checks, design rendering and fixture/browser results each prove their exercised scope; do not claim a live account or production flow was verified without observing it.
