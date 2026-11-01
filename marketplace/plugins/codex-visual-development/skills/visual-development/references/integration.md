# Project-native rendering

Read only for the selected framework/engine integration. Framework and engine versions come from the project, not this reference. Import the owned scene helper from an adopted project-local module; it accepts the project's `THREE` namespace and does not download an engine.

## Angular

Create browser-only renderers after the view is available using APIs supported by the actual Angular version. Keep SSR/prerender paths free of document/WebGL access. In zone-based applications, run the animation loop outside Angular and reenter only for meaningful application state. On component destruction call the scene handle's dispose exactly once. Do not move business data into the render loop or adopt Signals solely for this integration.

Pass a canvas with explicit CSS width/height. Provide a semantic table/text equivalent and a user-visible fallback for unsupported WebGL. The helper's `createScene(THREE, canvas, {onFrame, onError, maxDpr})` returns `{status, render, dispose, track, scene, camera, renderer}` on success. `track(resource)` registers exclusively owned disposable resources. `onFrame(seconds, context)` updates visual state; render is explicit for nonanimated data changes. On failure the result is `{status: 'unavailable', error}`; the caller owns product wording and fallback.

## Vue / Nuxt and React

Vue mounts in onMounted and disposes in onBeforeUnmount. Nuxt initializes in a client-only boundary compatible with its version. React mounts in an effect and returns dispose; repeated Strict Mode setup/cleanup must work. React Three Fiber can own a React scene instead of this helper when justified; do not combine two renderer owners for one canvas.

## Ownership and future adapters

Keep data transforms pure where useful; framework owners manage state and canvas lifetime. Register geometry, material, texture, controls and render targets only if the scene owns them. Shared resources retain their original owner. Loaded assets need explicit license, version, cancellation and disposal handling. No automatic traversal can reliably infer shared ownership.

For data-heavy 2D views, benchmark supported Canvas/SVG/chart options with representative data. For weather, map real data separately from decorative motion and honor reduced-motion preferences. For games, use the existing game engine unless a web-engine choice is part of the actual project decision. Add Blender, Remotion, physics or other adapters when concrete operations need them; do not generate empty engines.

Sources: [Three.js cleanup](https://threejs.org/manual/pages/cleanup.html), [responsive rendering](https://threejs.org/manual/pages/responsive.html). Verify actual device rendering and teardown; Python preview tests do not validate GPU behavior.

## Synthetic example

The bundled [example](../assets/example.html) uses synthetic temperature values for a table, SVG motion and Three.js bars; it fetches no weather data. It expects the adopted scene helper beside it and the selected Three.js build's `three.module.js` and `three.core.js` under `vendor/`. Obtain those from the project's approved package installation, retain its license, and do not publish copied vendor files without the applicable notices. The source browser-smoke runner prepares these files in a new temporary output directory and accepts explicit Python, Playwright, Three.js and browser paths. This fixture is acceptance material, not a mandatory product UI or framework starter.
