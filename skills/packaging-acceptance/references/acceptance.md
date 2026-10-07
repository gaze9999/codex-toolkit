# Portable package acceptance

## Inputs and identity

- Resolve canonical sources and generated outputs. Record the commit plus a digest of relevant uncommitted inputs when allowed; formal release artifacts use a clean committed snapshot. Never equate HEAD with dirty source bytes.
- Check manifest schema, stable package identity, independent component versions, dependency locks, hashes and reference closure. Include required scripts/references/assets, exclude caches, credentials and unrelated installed state. Plugin Skills have one source owner; identify directly installed copies before enabling the corresponding Plugin.
- Distinguish an internal build catalog from host marketplace metadata. New portable Plugins use root plugin.json and optional mcp.json. Resolve current host/schema support before using a compatibility overlay or platform-specific hook.

## Minimal checks

When local packaging is excluded, inspect manifests, referenced inputs, syntax and dependency boundaries without building an EXE, wheel, ZIP or staged package tree. Memory-only payload inspection can verify source mappings; it does not prove that an archive installs or a launcher works.

Use small fixtures for changed deterministic guards. Do not start the real application, install dependencies, query paid APIs or expand access merely to make a source check pass.

## Native runtime acceptance

For authorized native platform checks, use isolated synthetic inputs and a bounded deadline. Verify Chinese/space paths, relocation, missing dependencies, exit codes and the intended CLI/Web/GUI entry. Use actual window/browser interaction for GUI acceptance; HTTP success alone proves only the requested response.

Record PID, parent creation time, owning client and owned resources before lifecycle checks. Normal shutdown comes first. Confirm owned children, ports and temporary directories are released after success, failure and cancellation. Preserve user services and client-managed MCPs. A timeout remains a failure or unresolved result; larger local timeouts do not establish the production deadline.

## Release readback

Check the exact source revision, native runner, artifact set and archive/asset hashes. Confirm remote assets separately after an authorized publication. A local file, successful CI upload or prepared release is not remote publication proof. Keep read-token credentials in the runner secret store; source access permission does not establish redistribution permission.
