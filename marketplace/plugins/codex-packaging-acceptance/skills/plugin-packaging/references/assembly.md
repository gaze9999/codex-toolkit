# Clean package assembly

## Select sources and products

- Inspect canonical source ownership, the target host's current portable/compatibility schema and existing release builders. Do not move sources just to match an illustrative tree.
- A portable Plugin uses root `plugin.json`, `skills/` and optional `mcp.json`. OpenAI registered app mappings use `extensions.com.openai.apps`; application binaries are separate products. Hooks and visual assets remain inside the package root with valid relative paths.
- Map source trees for Skills and resources, and individual source files for root component entry points. Reject traversal, symlinks/junctions, case-insensitive collisions and missing component references. Declaring a dependency does not install it.
- Bundle only explicit sources. Exclude VCS data, virtual environments, dependency caches, private generated assets, logs, local tests and temporary output. Reject selected credentials/private keys and `.env` material. Keep authorized examples and third-party notices. Filename checks do not establish a complete secret audit.
- Keep existing MCP adapters and shared cores in their own versioned runtime. Do not fork implementation into every Plugin. An external runtime requirement remains visible in provenance and installation acceptance.

## Execute and verify

- Prefer the repository's existing builder. In a verified codex-toolkit checkout, `tooling/package.py plan` inspects the default source products, `build --version <tag> --output <new-directory>` creates labeled development artifacts, and `verify --output <directory>` checks the recorded assets. Use repeatable `--product` selection for wheels or native runtimes. `--release` requires clean committed inputs and does not publish.
- The maintained catalog's optional `components` maps exact `{source, target}` files, while `resources` maps trees below a target folder. Validate packaged MCP transport and app/hook JSON entry points. Full host schema/runtime tests remain separate.
- Use fixed ZIP metadata and sorted entries. Record each original source/hash, artifact hash, base revision, working-tree/committed state, version and prerequisites. Do not call a changed working tree the contents of its base commit.
- Verify archive CRC, unique complete members and byte-for-byte expected contents before promotion. Verify output ownership and refuse replacement of existing/unmanaged output. Recheck relevant sources before accepting the build.
- Run native builds on their supported runner with the pinned standalone runtime and authorized UI assets. Reuse existing smoke checks for relocated startup/exit. Separate syntax, package readback, runtime startup, real authenticated calls and client reload in the report.
- Public submission, GitHub Release, client installation and activation require their own authorization. A read token proves source access, not redistribution rights.

## Cross-client compatibility changes

Before repairing a Plugin, identify the exact client/version, loaded manifest and runtime path, configuration source, and synchronization mechanism. A CLI installation or settings file does not establish Desktop adoption. Keep account-synchronized copies separate from local CLI caches; update canonical sources and regenerate owned outputs, not client-managed copies.

For settings or launcher changes, apply the owning package's version policy and verify generated manifests plus source provenance. Treat stale same-version synchronization as a hypothesis until receipts or loaded bytes support it. Test the actual selected interpreter and package prerequisites; shell PATH and GUI PATH may differ. An optional executable or root setting needs explicit empty-value behavior, never an implicit expansion of filesystem access. Preserve required settings and use only supported runtime registration/dispatch paths without automatic installation or repeated handoff loops.

Keep manifest validation, package generation, process startup, tool invocation, account synchronization and native client reload as separate evidence. Record native platform coverage independently. Prepare candidate output in a verified new directory and promote only after validation; a failed temporary-directory operation must not redirect writes into an existing candidate.
