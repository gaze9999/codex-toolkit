---
name: maintainability-review
description: Review source maintainability using local code-health candidates for orphan files, unused exports or members, duplicate code, branch counts and long functions. Use for scoped cleanup reviews of comments, call chains and forwarding. Return evidence and a proposed diff without editing the project.
metadata:
  short-description: Review unused code, duplicate regions, and complex functions
  version: "0.1.0"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Maintainability Review

1. Resolve the requested root, relevant entry points, tracked decisions, and project rules. Run the project's marker/retention lookup first. Pass its approved patterns, root-relative files and verified line ranges into the scan. Keep private marker policy and reasons in their owning environment.
2. Call the local `code_health` tool with the selected root and checks. If it is unavailable, run the compatible local `code-health scan --root <root>` CLI with the same scope. Supply known entry paths and preserve unresolved configuration, dynamic loading, template or reflection boundaries. See the [CLI and MCP inputs](https://github.com/gaze9999/codex-toolkit/blob/main/tools/code-health/README.md).
3. Inspect the actual declarations, callers, templates, and relevant runtime hooks with [review checks](references/checks.md). Use the project's existing compatible ESLint CLI and configured rule options for complexity and length when available. Use code-health branch and line counts as syntax-level evidence otherwise.
4. Return the [review table](references/report.md) and proposed diffs for changes supported by the evidence. Prepare applicable patches in scratch following the project's approval rules. Leave source edits, deletions and moves for a separately authorized implementation.

An omitted entry point, partial scan, private member, matching body, or high branch count can change the review scope. Trace the actual use and impact before proposing any change.
