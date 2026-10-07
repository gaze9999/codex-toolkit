---
name: react-development
description: Implement, diagnose, refactor or review React components, hooks, state and routing using the detected React runtime. Load server/SSR guidance only for a framework or hydration boundary, not for generic JavaScript or non-React UI.
metadata:
  version: "0.4.15"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# React Development

Inspect actual React/compiler/build versions, entry points, router/store, tests, styling and deployment. Do not assume Next.js, React Server Components, React Compiler, Vite, TypeScript or a new Hook API.

- Preserve props/events/context/ref and route/store/component identity contracts. Keep render pure, Hooks unconditional and at supported call sites. Use the existing state owner and typed public APIs.
- Derive render values directly instead of synchronizing redundant state. User actions stay event commands, external synchronization may use owned effects with cleanup. Do not introduce a new state/data-fetching library incidentally.
- Reuse design tokens, loading/error/empty/form/keyboard/focus patterns. Rendering the same component type/key/position preserves state, changes can reset user progress.
- Obtain authoritative version-specific APIs through available documentation capabilities, no fixed provider or external private-code submission.
- Before extracting or deleting shared code, trace actual imports/re-exports, lazy consumers and the complete component/hook/store call chain. Preserve subscription, identity and validation boundaries. Use Playwright for interactions, DevTools for console/network/performance evidence and supported symbol navigation only for unresolved references.

Read [state, effects and subscriptions](references/state-effects.md) when those contracts change. Read [server and hydration](references/server-hydration.md) only for SSR/framework/server-client work. UI flow/a11y design and prose proofreading use relevant available capabilities, not mandatory tools.

Choose actual type/build/focused component tests for the changed contract. Verify async races, cleanup, identity and interactions where affected. Existing browser tests or available DOM/console/network capabilities cover live behavior. Trace/profile the same production-like route/state before optimization claims, record expected/actual evidence and close only owned sessions.

For user-visible layout, copy, displayed-data or interaction changes, use the available ui-ux-design Skill for requirement comparison and rendered-flow acceptance before delivery, without waiting for user screenshots. If unavailable, compare the original request with the affected rendered states directly and identify unverified behavior.
