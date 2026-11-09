---
name: visual-development
description: Integrate data visualization, 2D motion or WebGL/WebGPU scenes (Three.js, PixiJS and similar renderers) into an existing web project, selecting rendering and lifecycle tools from its actual stack. Use for interactive feature development and owned previews, not automatic video production or framework migration.
metadata:
  short-description: Project-native visualization and Three.js development
  version: "0.2.0"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Visual Development

Inspect the project version, data, interaction, accessibility, performance constraints and existing components before choosing a renderer. Main can act as the project agent without spawning another agent. A tool list does not prescribe a product category.

Use existing tables/charts for exact lookup and ordinary analytics, CSS/SVG/Canvas for suitable 2D motion, Three.js for spatial interactions. Read [renderer selection](references/renderer-selection.md) only when choosing or replacing a 2D/3D web renderer or engine such as PixiJS, Phaser, Babylon.js, PlayCanvas, Konva or Fabric.js. Keep Angular, Vue/Nuxt and React lifecycles native; React Three Fiber is a React-specific option. Existing Unity projects retain their engine. Remotion is conditional on an actual video requirement. Do not install every option or introduce a universal scene schema.

Use the available data-visualization Skill for source mapping and figure design when applicable. Read [project integration](references/integration.md) for lifecycle/adapter boundaries and [runtime operations](references/runtime.md) when project inspection or a static preview is needed. Use existing browser tools for interaction, console, network and capture; snapshots and package inspection do not establish rendered acceptance.

For Three.js, adapt the [owned scene helper](assets/three-scene.mjs) only after checking the project's runtime support. The helper owns its renderer/listeners/loop; caller-owned resources must be explicitly registered. Keep framework destruction, DPR, resize, reduced motion, hidden tabs and failed WebGL in the acceptance path. Do not dispose shared textures/materials owned elsewhere.

Keep deterministic data transformation separate from rendering. Verify values, nulls, units and labels, then interaction and rendering at relevant sizes. Product runtime must work without Codex/MCP/semantic API unless a separate feature explicitly requires them.

Delegate only authorized independent work with exact file/resource ownership. An optional bounded provider comparison may clarify eligible rendering choices; it cannot establish stack compatibility, source authority or dispatch permission. Retain actual engine format and add adapters only for demonstrated new-project needs.
