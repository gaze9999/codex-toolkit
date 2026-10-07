---
name: local-activity-query
description: Read bounded tool counts, Jev usage and source health from an explicitly selected local activity monitor. Use for a named time window or diagnostic summary, not conversation extraction, account totals, monitoring activation or process cleanup.
metadata:
  version: "0.1.0"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Local Activity Query

Use an already-running, authorized loopback monitor and its current schema. The bundled [summary helper](scripts/activity_summary.py) takes an explicit loopback URL and window, reads only the supported snapshot endpoint and returns allowlisted counters/statuses. It does not start collectors, change settings, read files or query paid services.

Distinguish source availability, refresh health and partial backfill from completed observation. Preserve null/unknown and observed zero. Thread cumulative usage, logical calls and retry attempts differ; local observations do not establish account totals or cost.

Never return conversation titles/content, raw SQL, request/response payloads, credentials, arbitrary file paths or raw errors through this summary flow. Keep existing detail views under their original application's authorization. Add MCP only if repeated structured queries justify it, using the same bounded summary function and read-only boundary.
