---
name: environment-consistency-check
description: Compare local Skills, runtime mirrors, or environment trees without synchronizing them. Use for versioned file drift, missing or extra files, and hash-based consistency checks.
metadata:
  short-description: "Compare Skills and environment mirrors without writes"
  version: "0.4.12"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Environment Consistency Check

Resolve two existing absolute, non-nested directory roots and the requested include/exclude scope. Choose an available read-only local comparison capability supporting relative paths, sizes and SHA-256, checking its actual options and permitted roots. Prefer a compatible CLI/native file comparison for a bounded audit; keep a scoped MCP when repeated structured queries or the client's access model justify it. Equivalent local file inspection is sufficient when it preserves the same scope and reports unreadable or changing files

- Describe the requested outcome, confirmed facts, decisions, actual checks and concrete unresolved items. Support comparisons with evidence and applicable conditions, and retain limitations that affect correctness, safety, compatibility, requirements or execution.
- Compare by relative path, size and SHA-256. Report missing, extra and changed files separately; do not reduce all differences to one pass/fail label
- Default exclusions intentionally omit VCS internals, caches, `.env`, credentials and key material. Expand scope only when the user names the required files and their contents may be read safely
- A difference does not authorize synchronization. Inspect ownership, source direction, version and backup expectations before proposing or performing a write
- Repository source and installed mirrors have different roles. State which side was treated as source, and do not assume the newer timestamp is authoritative
- State comparison scope and exclusions. A file limit, unreadable path, missing dependency, or changing tree leaves the affected comparison incomplete; do not report full equality or bypass read-root boundaries to finish it
