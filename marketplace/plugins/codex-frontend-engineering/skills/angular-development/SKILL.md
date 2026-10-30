---
name: angular-development
description: Implement, diagnose, refactor or review Angular components, forms, templates, feature models/helpers and application integration using the detected Angular/TypeScript/RxJS versions. Use architecture guidance only when ownership, DI, routing or cross-runtime boundaries are affected.
metadata:
  version: "0.5.0"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Angular Development

Inspect the affected feature, actual Angular/TypeScript/RxJS versions, compiler/build targets and applicable instructions. Use the project's existing patterns, do not assume standalone components, Signals, zoneless rendering or a recent API.

- Preserve selector/input/output/host/template contracts, form value/validation/disabled/touched semantics and injector lifetime. Local screen state stays local, shared state uses its existing owner.
- Derive values rather than synchronize competing flags. Respect subscription cancellation, signal dependencies and async teardown. Do not migrate APIs, state libraries or framework versions as incidental cleanup.
- For uncertain APIs, use available authoritative version-specific documentation. Keep public questions separate from private project content, no fixed MCP/provider requirement.
- For maintenance analysis, trace actual imports, templates, selector consumers and the complete changed call chain. Lexical identifier counts do not establish unused imports. Keep boundary validation and shared component ownership. Choose Playwright for interaction, DevTools for console/network/performance evidence and supported symbol navigation only when references are unclear.

## Load only the affected mode

- DI/state/routing/render ownership or Host/custom elements: [architecture](references/architecture.md)
- New/replaced generic UI, dialogs or a shared-library reuse review: [UI reuse](references/ui-reuse.md)
- Forms, templates, async rendering or hydration: [component behavior](references/component-behavior.md)
- Generation or review of class visibility, layout, member groups, compact syntax or numeric display: [Angular style example](references/angular-style.md)
- Feature maintenance items, read/write ownership, actual option sources, pass-through calls, duplicate projections or Model/type definitions: [code maintainability](references/code-maintainability.md)
- Bounded maintenance audits with independent scope/depth, candidate evidence, performance/security routing: [maintenance review](references/maintainability-review.md), using the optional read-only [Python runner](scripts/check_maintainability.py) and its [AST adapter](scripts/maintainability_ast.cjs)
- Explicit member reordering or Signal I/O migration: use the available angular-member-order Skill, otherwise preserve declaration order and initializer dependencies

The style references are bundled with this Skill and the frontend-engineering Plugin. Load only the affected mode after checking project compatibility. Member ordering alone does not authorize logic or Model changes.

At each work round, recover relevant current progress, effective decisions and coding conventions. Apply formatting and member ordering to the actual generated/changed code, preserving initializer/decorator timing and unrelated work; reading a rule is not compliance. Reuse checked pointers and refresh only affected evidence. Apply the selected baseline to components, models, Error classes and helpers. Keep existing frontend-only ownership; do not expand into backend/framework/workspace work.

For new/replaced generic UI, compare existing project capabilities before building another implementation; verify actual imports/templates and the adopted behavior or concrete mismatch before claiming reuse. Keep the selected source pointer with existing work records, not a fixed checkout path or a parallel backlog.

Before delivery, compare the actual changed declarations and behavior with that checklist. When explicit `public` is required, include constructors and constructor parameter properties such as `readonly code`, not only `class.members`; keep private/protected/#private and ordinary parameters unchanged. Use the style reference's optional AST check for the reviewed file set when a compatible TypeScript is already installed. Do not substitute text counts for reference or read/write analysis, and do not report pending maintenance items as fixed.

For authorized edits, choose actual project type/template/targeted tests and relevant browser interactions. For analysis, deliver decisions/evidence without editing. Use traces only for measured performance questions, symbol lookup only when relationships/language support need it. Report exercised route/state/results and specific gaps, close only owned browser sessions.

For changed messages, locale switching or localized formatting, use the available internationalization-engineering Skill. For changed semantics, keyboard/focus, errors or assistive-technology behavior, use accessibility-engineering. Load only the affected references and preserve the existing component, data and copy contracts.

For company/client form or message changes, apply the source and trigger checks in [component behavior](references/component-behavior.md); a validator or familiar UX pattern does not authorize new copy.

For user-visible layout, copy, displayed-data or interaction changes, use the available ui-ux-design Skill for requirement comparison and rendered-flow acceptance before delivery, without waiting for user screenshots. If unavailable, compare the original request with the affected rendered states directly and identify unverified behavior.
