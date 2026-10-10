# Compare local environment mirrors

Read for a read-only comparison of selected Skills, runtime mirrors or environment trees. A difference does not authorize synchronization.

Resolve two existing absolute roots, identify the source and mirror roles, and select the requested include/exclude scope. Choose a compatible local CLI/native comparison or scoped MCP using its actual options, permitted roots and limitations. A tool requiring non-nested roots must receive independent roots; another comparison method must explicitly account for overlap without reading its own output.

- Compare relative paths, sizes and SHA-256. Separate missing, extra and changed files, preserving actionable locations and versions when available.
- Exclude VCS internals, caches, `.env`, credentials and key material by default. Expand only for requested files whose contents may be read safely; do not bypass read-root boundaries.
- Repository sources and installed mirrors have different owners. State the selected source direction; a newer timestamp alone does not establish authority.
- Preserve unreadable, inaccessible or changing files and tool/file limits as incomplete comparisons. Equality applies only to the fully checked scope, with its exclusions.
- Report requested outcome, actual checks, confirmed differences and remaining scope. Installation, authentication, client loading and runtime behavior need their own evidence.

Before any separately authorized write, inspect ownership, source version, references, backup expectations and current destination. Return comparison evidence to the maintained synchronization workflow rather than applying writes during review.
