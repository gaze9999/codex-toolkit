# Local runtime operations

Use `codex-visual-runtime` for read-only project inspection, explicit artifact hashes and process-owned static preview jobs. Source: `python-tools/packages/visual-runtime`; Plugin distribution: `resources/visual-runtime`. The package README owns install details. The core has no third-party dependencies; MCP requires the optional pinned SDK.

CLI: `visual-runtime --root PROJECT inspect`, `artifacts --files FILE...`, or `preview --entry index.html --files index.html app.js`. The preview CLI remains in the foreground; Ctrl+C releases its listener. Never report the server ready after that process has stopped.

MCP: start `visual-runtime-mcp` without a project argument. Operations: visual_inspect(root), visual_artifacts(root, paths), visual_preview_start(root, entry, files), visual_preview_status(job_id), visual_preview_stop(job_id). Supply a nonblank authorized root for each file operation, preferably an absolute project path. Paths and traversal guards resolve within that call's root. Jobs retain their original snapshots; interleaved roots share the process-wide eight-job limit. Status and stop use the owning process's job_id.

For 0.2.0, remove the former startup `--root PROJECT` arguments and add root to the three file-operation calls. CLI root selection remains unchanged.

Preview serves an immutable snapshot of at most 128 explicitly selected browser assets, 32 MiB each and 64 MiB total, under an unguessable loopback URL with a Host guard. No directory listing, hidden files, linked paths or arbitrary commands. Up to eight jobs per process; unknown jobs cannot stop foreign processes. Source changes require a new snapshot. HTML scripts may still access the network: review selected assets before opening them.

Angular/Nuxt/React dev servers keep their native scripts, HMR and owner lifecycle. This tool does not execute project commands, build bundles, render video or replace a browser. Use the project's approved runner when those capabilities are required. Record exact artifact hashes and browser evidence in existing project tracking.
