---
name: task-routing
description: Choose between continuing a Codex task, creating a separate task, forking a conversation, and using subagents, then prepare a compact handoff when needed. Use for explicit routing questions, conditional routing instructions in a user turn, or an authorized continuing coordinator, not ordinary implementation or AGENTS.md maintenance.
metadata:
  short-description: Task routing and context handoff
  version: "0.4.14"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Task Routing

Choose whether to continue here, create/fork a task, delegate a bounded subtask or schedule later work. The request and available tools determine authorization. Do not create or message another task unless explicitly authorized.

Read [workflow](references/workflow.md) when selecting or executing a routing operation. It retains task/owner/worktree, continuity, cost and authorization decisions. Keep Main responsible for scope/integration, use the minimum useful owners and preserve active sessions.

Return the requested artifact or confirmed operation with actual evidence and concrete gaps. Do not confuse prepared content with execution, parsing with runtime adoption or an intended check with a completed result.
