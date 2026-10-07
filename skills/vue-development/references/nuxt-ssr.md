# Nuxt and Vue SSR

- Verify Nuxt/Vue versions, router, Nitro/server routes, auto-imports, data fetching, runtime config and deployment mode. A Vue/Vite application is not automatically a Nuxt application.
- Server state must be scoped to a request, not mutable shared module singletons across users. Keep secrets/server dependencies outside public runtime config/client bundles.
- Guard window/document/storage and browser side effects. Hydration needs compatible initial server/client output, check time/random/locale inputs and generated keys rather than suppressing mismatches.
- Preserve useAsyncData/useFetch keys, payload/cache/dependency behavior and errors only according to the installed Nuxt version. Do not double-fetch from component effects when the framework owns initial data.
- Separate universal/client/static rendering and server-only API availability. A static deployment must present unavailable server features honestly and retain correct asset/router base paths.
- Verify the affected SSR response, hydration/console, navigation and target build mode. A successful client build does not prove server deployment, request isolation or static-server feature support.

Sources: [Vue SSR](https://vuejs.org/guide/scaling-up/ssr), [Nuxt documentation](https://nuxt.com/docs).
