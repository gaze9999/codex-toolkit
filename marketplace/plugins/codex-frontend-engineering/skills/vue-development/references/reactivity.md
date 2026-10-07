# Vue Reactivity and Component Contracts

- Preserve typed props/emits, v-model arguments/defaults, slot scope, attribute fallthrough and exposed methods. Do not mutate parent-owned props or create a duplicate store owner.
- Vue 3.5+ compiler-reactive defineProps destructuring differs from ordinary reactive() destructuring and earlier Vue compilers. Confirm the installed compiler, keep reactive getters/refs when passing values to watchers/composables.
- Watch a reactive source, not an already-read primitive. Preserve ref identity, computed dependencies, watcher flush timing and teardown. Async-created watchers need explicit ownership/stop.
- Cancel or invalidate stale requests. Version-supported onWatcherCleanup must be registered synchronously before await, callback-provided cleanup may have different semantics. Do not transplant an API into an unsupported runtime.
- Composables should retain clear caller/lifecycle ownership. Shared/persisted state belongs to the existing store, local interaction remains component-owned.
- Verify prop changes, event ordering, stale-result protection, mount/unmount and relevant navigation with focused existing tests. Add tests only when behavior/risk warrants them.

Version-aware sources: [props](https://vuejs.org/guide/components/props), [watchers](https://vuejs.org/guide/essentials/watchers.html), [composables](https://vuejs.org/guide/reusability/composables).
