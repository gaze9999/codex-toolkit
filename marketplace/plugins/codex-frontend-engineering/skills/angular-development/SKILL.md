---
name: angular-development
description: Implement, diagnose, refactor or review Angular components, forms, templates and application integration using the detected Angular/TypeScript/RxJS versions. Use architecture guidance only when ownership, DI, routing or cross-runtime boundaries are affected.
metadata:
  version: "0.4.14"
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
- Forms, templates, async rendering or hydration: [component behavior](references/component-behavior.md)
- Explicit member reordering or Signal I/O migration: use the available angular-member-order Skill, otherwise preserve declaration order and initializer dependencies

For authorized edits, choose actual project type/template/targeted tests and relevant browser interactions. For analysis, deliver decisions/evidence without editing. Use traces only for measured performance questions, symbol lookup only when relationships/language support need it. Report exercised route/state/results and specific gaps, close only owned browser sessions.
