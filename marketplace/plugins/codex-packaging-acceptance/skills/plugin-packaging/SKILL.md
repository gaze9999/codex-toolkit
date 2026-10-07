---
name: plugin-packaging
description: Design or automate clean Plugin and application packages from selected Skills, MCP servers, registered app mappings and runtime resources. Use for package assembly or build pipelines, not installation, publication or verification-only acceptance.
metadata:
  short-description: Clean Plugin and application package assembly
  version: "0.1.0"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Plugin Packaging

Build the requested distribution from its canonical sources and existing builders. Inspect actual manifests, entry points, runtime pins, licenses and ownership before choosing package boundaries. Packaging authorization does not authorize installation, account registration, source commits or publication.

Read [assembly](references/assembly.md) when designing mappings or implementing the build. Keep one owner per Skill, include references/scripts/assets needed by its workflows, and generate mirrors only in a dedicated output tree. A Plugin groups capabilities by shared use, dependencies and enablement; it does not create a security sandbox.

Distinguish portable Skills/MCP configuration, registered MCP app mappings, optional hooks/assets, source application bundles and native application runtimes. Inspect the current host schema before adding app or hook settings. Never invent registered IDs or public redistribution permission.

Plan without side effects, assemble selected products in a temporary sibling directory, verify exact members and source hashes, then promote the complete output. Preserve existing outputs on failure. Label working-tree previews separately from reviewed committed release inputs.

Return produced paths, included components, source state, actual readback/checksum results and remaining runtime/distribution acceptance. Use the existing packaging-acceptance workflow only when the request also includes installation, relocation or lifecycle acceptance.
