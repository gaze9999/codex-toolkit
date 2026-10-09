# Portable package acceptance

## Inputs and identity

- Resolve current source visibility and intended audience separately. Private development followed by a public version is public-target delivery; inspect the selected public source/history/artifact boundary when that stage is in scope. Choose checks from the actual payload, data and authorized outcome, rather than imposing one public/private layout or a full history audit on every package.
- Resolve canonical sources and generated outputs. Record the commit plus a digest of relevant uncommitted inputs when allowed; formal release artifacts use a clean committed snapshot. Never equate HEAD with dirty source bytes.
- Check manifest schema, stable package identity, independent component versions, dependency locks, hashes and reference closure. Include required scripts/references/assets, exclude caches, credentials and unrelated installed state. Plugin Skills have one source owner; identify directly installed copies before enabling the corresponding Plugin.
- Distinguish an internal build catalog from host marketplace metadata. New portable Plugins use root plugin.json and optional mcp.json. Resolve current host/schema support before using a compatibility overlay or platform-specific hook.

## Sensitive distribution inputs

For changed distribution inputs, inspect actual mapped files and, when available within authorized checks, ZIP/wheel/Plugin contents: secrets, credential files, local config, logs, fixtures and examples. Report inspected scope and scanner limits; a pattern scan does not prove absence of all sensitive data. Do not build artifacts merely for this check when packaging is excluded.

Suspected exposure blocks affected publication. Follow the [GitHub procedure](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository). Credential rotation, history cleanup and replacement of distributed artifacts are distinct stages; changing the current payload does not erase old distributed copies. Cleanup and repository-setting changes require separate authorization.

For public data generated from private sources, derive selected fields from the actual consumer/schema and inspect the resulting payload and build prerequisites. Private authoring notes and credentials stay outside that public boundary; browser-delivered data remains readable. When candidate application writes existing state, choose digest/revision guards and atomic replacement appropriate to concurrency, and verify relevant persisted-data compatibility before publication. These methods apply to the affected data/update path, not every release.

## Minimal checks

When local packaging is excluded, inspect manifests, referenced inputs, syntax and dependency boundaries without building an EXE, wheel, ZIP or staged package tree. Memory-only payload inspection can verify source mappings; it does not prove that an archive installs or a launcher works.

Use small fixtures for changed deterministic guards. Do not start the real application, install dependencies, query paid APIs or expand access merely to make a source check pass.

## Native runtime acceptance

For authorized native platform checks, use isolated synthetic inputs and a bounded deadline. Verify Chinese/space paths, relocation, missing dependencies, exit codes and the intended CLI/Web/GUI entry. Use actual window/browser interaction for GUI acceptance; HTTP success alone proves only the requested response.

Record PID, parent creation time, owning client and owned resources before lifecycle checks. Normal shutdown comes first. Confirm owned children, ports and temporary directories are released after success, failure and cancellation. Preserve user services and client-managed MCPs. A timeout remains a failure or unresolved result; larger local timeouts do not establish the production deadline.

## Release readback

Check the exact source revision, native runner, artifact set and archive/asset hashes. Confirm remote assets separately after an authorized publication. A local file, successful CI upload or prepared release is not remote publication proof. Keep read-token credentials in the runner secret store; source access permission does not establish redistribution permission.

## Authorized GitHub publication

Check the actual project version scheme, Tag convention, intended commit, branch protections, required CI and release workflow. Never create a Tag/Release from a preparation-only or CP request. Version magnitude does not determine publication permission or cadence. Preserve independent component versions and package-native syntax; changed published contents require a new version rather than a silent replacement.

For a requested release, verify relevant README installation/compatibility claims, confirmed licensing and required shipped notices, metadata/version alignment, user-facing notes and applicable native/artifact gates. Generated notes need review for omissions. Community-health files are optional recommendations unless required by the project. Build provenance, signatures or attestations are selected for the actual supply-chain risk and supported workflow, not added automatically.

Inspect draft, prerelease, latest and immutable settings before publication. With immutable releases, attach all assets to a draft before publishing; a workflow that uploads assets after `release.published` is incompatible with that sequence and needs an explicitly scoped workflow decision before enabling immutability. Do not change repository settings just to complete an audit.

Read back the remote Tag's commit, Release state, required workflow results, asset names/version/size and downloaded SHA-256 against the reviewed manifest. Distinguish source archives from runnable assets and GitHub Release from package-registry or Plugin-marketplace delivery. Upload success alone is not completed acceptance. Report missing assets or native checks with their impact and next step.

Sources checked 2026-10-07: [GitHub releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases), [managing releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository), [immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases), [SemVer](https://semver.org/), [Python metadata](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)


CPR completes only stages allowed by the project: it need not create a GitHub Release on every run. Check project-specific pre-1.0 restrictions and minor milestone policy; patches may require a new downloadable distribution when permitted. Prefer exact full-version tags, retain fixed commit identity and verify tag-triggered workflows before pushing. Explicit tag correction is separate authorization; verify replacement and deletion rather than silently moving a published tag.
