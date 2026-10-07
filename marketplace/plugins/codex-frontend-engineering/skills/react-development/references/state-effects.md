# React State, Effects and Subscriptions

- Identify one owner for each mutable value, derive the rest during render. Do not mirror props/store projections into state merely to keep them synchronized.
- Keys/types/tree positions govern preservation/reset. Keep stable entity keys for reorderable items and confirm deliberate reset behavior before changing keys or nesting component definitions.
- Effects synchronize external systems, event handlers express user actions. Track actual reactive dependencies, cleanup subscriptions/listeners/timers and prevent stale async results. Do not hide dependency mistakes by disabling lint or adding refs indiscriminately.
- State is a render snapshot, check stale closures and use updater functions when deriving from queued prior state. Avoid mutating state objects/arrays or treating setState as a synchronous write.
- Prefer existing framework/cache data ownership. For supported external stores, preserve subscribe/snapshot identity and SSR snapshots; useSyncExternalStore may be the appropriate supported API. Do not rebuild the project store just to apply an example.
- Development Strict Mode can expose missing cleanup through extra setup/cleanup. Do not disable it to mask a leak. Measure production-like performance before memoization, preserve callback/reference semantics when changing caches.
- Select focused tests for affected rerenders, prop changes, race ordering, mount/unmount, keys and transitions. Fixtures do not prove full browser/user behavior.

Sources: [Effects](https://react.dev/learn/synchronizing-with-effects), [derived state and event logic](https://react.dev/learn/you-might-not-need-an-effect), [state identity](https://react.dev/learn/preserving-and-resetting-state).
