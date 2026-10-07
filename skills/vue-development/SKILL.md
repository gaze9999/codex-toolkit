---
name: vue-development
description: Implement, diagnose, refactor or review Vue components, composables, stores and routes using the detected Vue ecosystem. Load Nuxt/SSR guidance only for server rendering, hydration, deployment or Nuxt integration.
metadata:
  version: "0.4.14"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Vue Development

Inspect manifests/lockfiles, compiler/router/store/build settings and relevant components. Detect Vue version, Options/Composition API, script setup, auto-imports, TypeScript, UI library and CSS conventions, do not assume Nuxt/Vite/Pinia/SSR.

- Preserve props/emits/v-model/slots/exposed members/provide-inject and route/store/API/CSS contracts. Reuse current components/composables/tokens/loading/error/validation patterns.
- Preserve reactive identity and lifecycle ownership, keep local state local. Do not migrate API style/router/state/bundler/UI libraries unless requested.
- Preserve guard/lazy-load/error/empty/form/keyboard/focus behavior and scoped/project styling. Do not use broad global/deep CSS to fix one component.
- For unclear APIs, retrieve authoritative documentation for the verified package/compiler version with available capabilities, submit only public questions externally.
- Before maintenance changes, trace actual imports, auto-import configuration, template consumers, slots and the complete composable/store call chain. Preserve reactive and validation boundaries. Use Playwright for interaction, DevTools for console/network/performance evidence and supported symbol navigation when consumers are unclear.

Read [reactivity and component contracts](references/reactivity.md) for watcher/composable/state changes, or [Nuxt and SSR](references/nuxt-ssr.md) for request isolation, hydration, server/client APIs or deployment. Do not load both for a simple local template edit.

Select actual type/template/focused tests/lint/build for the changed behavior. Use the existing component/browser runner or available browser capability when interaction is not statically provable. Record route/state/actions/console/network and expected/actual results, close only owned sessions. Measure the same route/state before performance conclusions and verify language support before symbol retrieval.
