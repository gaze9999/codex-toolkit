# Angular Component Behavior

- Read actual component/template/form callers. Preserve required/optional inputs, output payloads, selector/host bindings, content projection and public component APIs.
- Detect Reactive Forms, template-driven forms or version-supported Signal Forms. Preserve value normalization, validation, pending/disabled/touched/dirty states, async-validator cancellation and submission/reset behavior. Do not migrate forms merely because a newer API exists.
- Signals represent reactive values, RxJS models streams and timing. Inspect subscription/initial-value/error/completion semantics before converting. Reuse `toSignal` results rather than creating repeated subscriptions, and respect injection-context/destruction ownership.
- Keep derived values computed/pure. An effect is not a replacement for explicit ownership or event commands. Verify real installed API semantics before introducing resource/effect/interop helpers.
- Preserve template tracking identity, focus, field state and accessible errors when changing loops/conditions. Do not use index identity for reorderable entities without checking state consequences.
- Respect OnPush/zoneless/SSR/hydration only when configured. Server rendering must not access browser globals or leak request state. Measure the affected render path before caching/memoization or change-detection redesign.
- Use focused checks for the changed contract, with expected success/invalid/async/race/teardown states where meaningful. Real navigation, overlays/focus and host integration require the corresponding runner/browser evidence.

Authoritative starting points, select the matching documentation version: [RxJS interop](https://angular.dev/ecosystem/rxjs-interop), [Angular forms](https://angular.dev/guide/forms), [dependency injection](https://angular.dev/guide/di).
