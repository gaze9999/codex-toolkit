# Local runtime operations

Use `codex-visual-runtime` for read-only project inspection, explicit artifact hashes and process-owned static preview jobs. Source: `python-tools/packages/visual-runtime`; Plugin distribution: `resources/visual-runtime`. The package README owns install details. The core has no third-party dependencies; MCP requires the optional pinned SDK.

CLI: `visual-runtime --root PROJECT inspect`, `artifacts --files FILE...`, or `preview --entry index.html --files index.html app.js`. The preview CLI remains in the foreground; Ctrl+C releases its listener. Never report the server ready after that process has stopped.

MCP: start `visual-runtime-mcp --root PROJECT`. Operations: visual_inspect, visual_artifacts(paths), visual_preview_start(entry, files), visual_preview_status(job_id), visual_preview_stop(job_id). A configured root scopes the whole process; do not repoint it implicitly for another project.

Preview serves an immutable snapshot of at most 128 explicitly selected browser assets, 32 MiB each and 64 MiB total, under an unguessable loopback URL with a Host guard. No directory listing, hidden files, linked paths or arbitrary commands. Up to eight jobs per process; unknown jobs cannot stop foreign processes. Source changes require a new snapshot. HTML scripts may still access the network: review selected assets before opening them.

Angular/Nuxt/React dev servers keep their native scripts, HMR and owner lifecycle. This tool does not execute project commands, build bundles, render video or replace a browser. Use the project's approved runner when those capabilities are required. Record exact artifact hashes and browser evidence in existing project tracking.
