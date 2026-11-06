---
name: agent-artifact-audit
description: Inventory Codex and Claude Code artifacts across selected local workspaces and linked worktrees, review offline reports, apply a human-exported permanent deletion selection, or recover a prior run.
metadata:
  version: "0.1.0"
  author: gaze9999
  repository: https://github.com/gaze9999/codex-toolkit
---

Use scan_artifacts with explicit workspace roots and an output directory. Report the batch, gaps, counts and report paths. Keep detailed inventories local. Read the plugin README for eligibility and recovery, or tools/agent-artifact-audit/README.md in the Toolkit checkout.

For cleanup, require an explicit permanent deletion request and a selection JSON exported by the user from the scan HTML. Never create, expand or edit the selection on their behalf. Call apply_artifacts once. If the response is lost, locate the original run via the local batch receipt and call report_artifacts. Describe partial outcomes and unknowns. Never retry a destructive call to reconstruct its output.

