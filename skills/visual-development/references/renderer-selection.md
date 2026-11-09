# Web renderer selection

Read only when a project must choose or replace a 2D/3D web renderer, or when an existing renderer is unfamiliar. A project that already uses a renderer keeps it unless its actual requirements fail. The project's lockfile, browser targets and license policy decide versions; the snapshot below only orients the choice.

## Decision order

1. Exact values, sorting or reading order: keep tables/charts and the data-visualization Skill. A renderer is decoration or exploration on top, never the only data path.
2. A few animated shapes, icons or transitions: CSS, SVG or Canvas 2D. Add a library only when object count, hit testing or effects exceed them in a representative benchmark.
3. Many 2D sprites, particles, tiles or filters: PixiJS. Editable diagrams/whiteboards with selection and transforms: Konva or Fabric.js.
4. A 2D game needing scenes, input, physics, audio and asset loading together: Phaser.
5. Spatial 3D, product views, scientific scenes or custom shaders inside an app: Three.js.
6. A full 3D application or game needing integrated physics, GUI, XR, inspector or editor workflows: Babylon.js or PlayCanvas.
7. Sketches, teaching or generative art: p5.js, after checking that its LGPL terms suit distribution.

Prefer a renderer library (Three.js, PixiJS, Konva, Fabric.js) when the host framework owns state and layout. Prefer an engine (Phaser, Babylon.js, PlayCanvas) only when the engine's scene/game loop is the product core. Do not combine two renderer owners on one canvas.

## Comparison

Snapshot from npm on 2026-11-09. Recheck before adoption.

| Library | Version, license | Scope | Backends | Teardown entry point | Fit and cost |
| --- | --- | --- | --- | --- | --- |
| Three.js (`three`) | 0.187.0, MIT | 3D renderer and scene graph | `WebGLRenderer`; `WebGPURenderer` from `three/webgpu` with automatic WebGL 2 fallback | `renderer.dispose()` plus owned geometry/material/texture `dispose()` | Largest 3D ecosystem and loaders. Physics, UI and editor are separate choices. Resource disposal is manual. |
| PixiJS (`pixi.js`) | 8.22.0, MIT | 2D renderer | WebGL and WebGPU via `preference` | `app.destroy({removeView: true}, {children: true, texture: true, textureSource: true})` | Fast sprites, text, filters and batching. No physics or game structure. `app.init()` is async. |
| Babylon.js (`@babylonjs/core`) | 9.35.0, Apache-2.0 | 3D engine | WebGL and `WebGPUEngine` | `scene.dispose()`, `engine.dispose()` | Integrated physics, GUI, XR, inspector and asset pipeline. Larger payload; prefer modular imports. |
| PlayCanvas (`playcanvas`) | 2.23.3, MIT | 3D engine | WebGL and WebGPU | `app.destroy()` | Engine with entity-component model and an optional hosted editor. Keep editor/cloud use a separate account decision. |
| Phaser (`phaser`) | 4.2.1, MIT | 2D game framework | WebGL and Canvas | `game.destroy(true)` | Scenes, input, Arcade/Matter physics, audio, tweens and loader in one package. Owns the game loop and canvas. |
| Konva (`konva`) | 10.9.1, MIT | 2D Canvas scene graph | Canvas 2D | `stage.destroy()` | Shapes, layers, drag, hit testing and transformers for editors and diagrams. Not built for very large sprite counts. |
| Fabric.js (`fabric`) | 7.4.0, MIT | 2D object canvas | Canvas 2D | `canvas.dispose()` (asynchronous) | Object selection, editing, text and SVG/JSON import/export for design tools. |
| p5.js (`p5`) | 2.3.4, LGPL-2.1 | Creative coding | Canvas 2D and WebGL | instance-mode `remove()` | Fast sketching and teaching. Global mode conflicts with app frameworks; use instance mode. |

Framework bindings: React Three Fiber (`@react-three/fiber` 9.8.2, MIT) and `@pixi/react` (8.0.5, MIT) let React own the scene declaratively. Use one only when the React project adopts it as the scene owner; otherwise use the native library inside an effect.

## Integration rules

- Async initialization: PixiJS `app.init()`, Three.js `await renderer.init()` with `WebGPURenderer`, and Babylon WebGPU initialization can resolve after the component is destroyed. Record a disposed flag and tear down the late instance; React Strict Mode repeats setup/cleanup.
- WebGPU: treat it as progressive. Keep the WebGL fallback in acceptance and test on the project's target browsers. Three.js `WebGPURenderer` uses node materials/TSL; GLSL `ShaderMaterial` code needs porting, so do not switch renderers only for novelty.
- The [owned scene helper](../assets/three-scene.mjs) wraps `WebGLRenderer` only. For `WebGPURenderer` or other libraries, use the library's own lifecycle with the same ownership, DPR, resize, reduced-motion, hidden-tab and failure checks described in [project integration](integration.md).
- Upstream agent material: PixiJS publishes [Skills in its repository](https://github.com/pixijs/pixijs/tree/v8.22.0/skills), and Three.js publishes [llms.txt](https://github.com/mrdoob/three.js/blob/dev/docs/llms.txt). Read them for the matching version as sources; they do not replace this project's lifecycle, licensing or acceptance rules, and are not installed by this Skill.
- Bundle and license: measure the production bundle after tree shaking, and keep license notices for vendored builds, models, textures and fonts.

Sources: [Three.js WebGPURenderer](https://threejs.org/manual/#en/webgpurenderer), [PixiJS application lifecycle](https://github.com/pixijs/pixijs/blob/v8.22.0/skills/pixijs-application/SKILL.md), [PixiJS renderers](https://github.com/pixijs/pixijs/blob/v8.22.0/skills/pixijs-core-concepts/references/renderers.md), npm registry metadata for each package.
